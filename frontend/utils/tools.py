import os
import random
import time
import urllib.parse
from typing import Optional

import aiohttp
import chainlit as cl
from aiohttp.client_exceptions import ClientConnectorError
from constants.urls import (
    CHAPTER_DB_URL,
    FORMULA_DB_URL,
    TOC_DB_URL,
    VECTOR_DB_URL,
    WOLFRAM_URL,
)
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage

from .functions import add_system_message
from .reference_functions import to_reference, update_references


class QueryVectorDB(BaseModel):
    query: str = Field(
        ...,
        description=(
            "Eine natürlichsprachliche Abfrage, die an die Datenbank gesendet wird. "
            "Zum Beispiel: 'Wofür wird er Paritäts Operator benutzt?' oder 'Was ist das Ohm'sche Gesetz?'\n"
            "Dieser Parameter darf NIEMALS leer sein."
        ),
    )


class RetrieveTableOfContents(BaseModel):
    script_id: str = Field(
        ...,
        description="Die ID des Skripts, dessen Inhaltsverzeichnis abgefragt werden soll. Z.B. 'EX1', 'EX2' usw.",
    )


class RetrieveScriptSection(BaseModel):
    script_id: str = Field(
        ...,
        description="Die ID des Skripts, dessen Inhaltsverzeichnis abgefragt werden soll. Z.B. 'EX1', 'EX2' usw...",
    )
    chapter_id: str = Field(
        ...,
        description="Eine Kapitel-ID aus dem Inhaltsverzeichnis oder der Semantischen Suche, z.B. '1' oder '4' usw...",
    )
    section_id: str = Field(
        ...,
        description="Eine Sektions-ID aus dem Inhaltsverzeichnis oder der Semantischen Suche, z.B. '1' oder '2' usw...",
    )


class RetrieveFormula(BaseModel):
    script_id: str = Field(
        ...,
        description="Die ID des Skripts, dessen Inhaltsverzeichnis abgefragt werden soll. Z.B. 'EX1', 'EX2' usw...",
    )
    formula_id: str = Field(
        ...,
        description="Die formel ID, z.B. '3.13' oder '15.3' usw...",
    )


class QueryWolframAlpha(BaseModel):
    query: str = Field(
        ...,
        description="The query to send to the Wolfram Alpha API. For example: 'speed of light', 'integrate (x + 14)^3' or '3145/(3123 + 4123)'.",
    )


class QuestionSetup(BaseModel):
    topic: Optional[str] = Field(
        None,
        description="Das Thema, zu dem eine Frage gestellt werden soll. Z.B. 'Elektromagnetismus', 'Quantenmechanik' usw...; Wenn nicht angegeben, wird ein zufälliges Thema ausgewählt.",
    )


@tool(args_schema=QueryVectorDB)
async def query_vector_db(query: str) -> str:
    """
    Frage eine Semantische Vektor-Datenbank mit natürlicher Sprache ab, die relevante Ausschnitte aus allen Vorlesungsskripten basierend auf der Abfrage zurückgibt.
    Mögliche Anwendungen sind die Suche nach Formeln, Definitionen, Gesetzen und anderen Konzepten basierend auf deren Namen.
    Funktioniert gut für das Suchen von Konzepten die für das Lösen von Aufgaben benötigt werden.
    Wenn snippets aus diesem Tool verwendet werden müssen sie Zitiert werden.
    Falls nichts relevantes gefunden wird, präziere die Frage.
    Es ist besser Fragen aufzuteilen, z.b. "Drei Fälle des gedämpften Oszillators: Überdämpfung, kritische Dämpfung, Unterdämpfung" -> "Überdämpfung des gedämpften Oszillators", "Kritische Dämpfung des gedämpften Oszillators", "Unterdämpfung des gedämpften Oszillators"
    """

    def format_query_step(
        query: str,
        context_list: list[dict],
    ) -> tuple[str, str]:
        input_string = f"## Input Frage\nEs wurden **{len(context_list)}** Snippets mit folgender Frage gefunden: \n\n- **{query}**"

        output_string = "## Gefundene Snippets\n\n"
        for i, context in enumerate(context_list):
            chapter_name = context["chapter_name"]
            section_name = context["section_name"]

            # remove the section number from the subsection title
            section_name = section_name.replace(
                f"{chapter_name.split(' ')[0]}.", ""
            ).strip()

            output_string += f"### Snippet {i+1}\n"
            output_string += f"**Zitation**: [{context['document_id']} {context['chapter_id']}.{context['section_id']}]\n"
            output_string += f"**Dokument**: {context['document_name']}\n"
            output_string += f"**Kapitel**: {chapter_name}\n"
            output_string += f"**Sektion**: {section_name}\n"
            output_string += f"**Übereinstimmung**: {context['score']:.1%}\n"
            output_string += f"**Anzahl Token**: {context['num_tokens']}\n"
            # output_string += f"**Snippet Inhalt**: {content}\n\n"

        return input_string, output_string

    ret_settings = cl.user_session.get("settings")["retrieval_settings"]
    permitted_document_ids = cl.user_session.get("permitted_document_ids", None)

    request_json_body = {
        "query": query,
        "collection_name": ret_settings["collection_name"],
        "top_k": ret_settings["top_k"] or 200,
        "top_n": ret_settings["top_n"] or 5,
        "use_rerank": ret_settings["use_rerank"] or False,
        "extend_results": ret_settings["extend_results"] or False,
        "rerank_score_threshold": ret_settings["rerank_score_threshold"] or 0.1,
    }

    # only add permitted_document_ids if it is not None
    if permitted_document_ids:
        request_json_body["permitted_document_ids"] = permitted_document_ids

    async with cl.Step(
        name="Vektorsuche",
        language=None,
        show_input=True,
        type="tool",
    ) as step:

        step.input = f"Die Vektorsuche wird mit der Frage '**{query}**' durchgeführt."

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    VECTOR_DB_URL, json=request_json_body
                ) as response:

                    response_json = await response.json()
                    document_list: list[dict] = response_json["documents"]

                    # each document is a dictionary with the following keys
                    # "id", The id of the document in the database, Typically "script_id.chapter_id.section_id.paragraph_id"
                    # "document_id", The id of the document in the database
                    # "chapter_id", The id of the chapter in the document
                    # "section_id", The id of the section in the document
                    # "paragraph_id", The id of the paragraph in the document
                    # "document_name", The name of the document
                    # "chapter_name", The name of the chapter
                    # "section_name", The name of the section
                    # "content", The content of the (extended) paragraph
                    # "score", The score of the paragraph between 0 and 1
                    # "num_tokens", The number of tokens of the content

                    reference_list = [
                        to_reference(doc, "snippet") for doc in document_list
                    ]
                    update_references(reference_list)

                    input_str, output_str = format_query_step(
                        query,
                        document_list,
                    )
                    step.input = input_str
                    step.output = output_str

                    return (
                        "## Tool Response\n\n"
                        + "\n\n".join([ref.print_reference() for ref in reference_list])
                        + "\n## Ende der Antwort\n"
                        + "Wenn informationen hieraus benutzt werden, müssen die Quellen korrekt zitiert werden."
                    )

        except ClientConnectorError as e:
            step.output = f"Server Aktuell nicht erreichbar."
            return "Der Server ist aktuell nicht erreichbar. Versuchen Sie es später erneut."


@tool(args_schema=RetrieveTableOfContents)
async def retrieve_table_of_contents(script_id: str) -> str:
    """
    Erfrage das Inhaltsverzeichnis eines spezifischen Vorlesungsskripts.
    Gibt das Inhaltsverzeichnis mit Sektions-IDs zurück.
    """

    ret_settings = cl.user_session.get("settings")["retrieval_settings"]

    request_json_body = {
        "document_id": script_id,
        "collection_name": ret_settings["collection_name"],
    }

    with cl.Step(
        name="Inhaltsverzeichnis",
        language=None,
        show_input=True,
        type="tool",
    ) as step:

        step.input = f"Das Inhaltsverzeichnis für **{script_id}** wird abgefragt."

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(TOC_DB_URL, json=request_json_body) as response:
                    if response.status != 200:
                        step.output = "Die Anfrage ist fehlgeschlagen."
                        return "Es konnte kein Inhaltsverzeichnis gefunden werden."

                    response_json: dict = await response.json()

                    toc: list | None = response_json.get("toc", None)
                    if toc is None:
                        step.output = "Die Anfrage ist fehlgeschlagen."
                        return "Es konnte kein Inhaltsverzeichnis gefunden werden."

                    toc = "\n".join(toc)
                    step.output = toc
                    return toc

        except ClientConnectorError as e:
            step.output = f"Server Aktuell nicht erreichbar."
            return "Der Server ist aktuell nicht erreichbar. Versuchen Sie es später erneut."


@tool(args_schema=RetrieveScriptSection)
async def retrieve_section(
    script_id: str,
    chapter_id: str,
    section_id: str,
) -> str:
    """
    Rufe eine spezifische Sektion aus einem Vorlesungsskript basierend auf der Skript-ID und der Sektions-ID aus dem Inhaltsverzeichnis oder der Vektorsuche des Skripts ab.
    Mögliche Anwendungen sind das tiefere Eintauchen in ein spezifisches Konzept wenn der User nach mehr informationen fragt oder wenn ein spezifischer Abschnitt zusammengefasst wird.
    Wenn snippets aus diesem Tool verwendet werden müssen sie zitiert werden.
    """

    retrival_settings = cl.user_session.get("settings")["retrieval_settings"]

    request_json_body = {
        "document_id": script_id,
        "chapter_id": chapter_id,
        "section_id": section_id,
        "collection_name": retrival_settings["collection_name"],
    }

    async with cl.Step(
        name="Sektions Abfrage",
        language=None,
        show_input=False,
        type="tool",
    ) as step:

        step.input = f"Die Sektion {chapter_id}.{section_id} wird abgefragt..."

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    CHAPTER_DB_URL, json=request_json_body
                ) as response:
                    if response.status != 200:
                        out_str = f"Die Sektion {chapter_id}.{section_id} konnte nicht gefunden werden."
                        step.output = out_str
                        return out_str

                    response_json = await response.json()
                    step.output = f"Sektion **{response_json['section_name']}** aus Kapitel **{response_json['chapter_name']}** in **{response_json['document_name']}** wurde abgefragt."

                    reference = to_reference(response_json, "section")
                    update_references(reference)

                    return reference.print_reference()

        except ClientConnectorError as e:
            step.output = f"Server Aktuell nicht erreichbar."
            return "Der Server ist aktuell nicht erreichbar. Versuchen Sie es später erneut."


@tool(args_schema=RetrieveFormula)
async def retrieve_formula(
    script_id: str,
    formula_id: str,
) -> str:
    """
    Rufe eine spezifische Formel aus einem Vorlesungsskript basierend auf der Skript-ID und der Formel-ID ab.
    Mögliche Anwendungen sind wenn der User eine spezifische Formel sucht oder im text eine wichtige Formel referenziert wird.
    """

    retrival_settings = cl.user_session.get("settings")["retrieval_settings"]

    request_json_body = {
        "document_id": script_id,
        "formula_id": formula_id,
        "collection_name": retrival_settings["collection_name"],
    }

    async with cl.Step(
        name="Formel Abfrage",
        language=None,
        show_input=False,
        type="tool",
    ) as step:

        step.input = (
            f"Die Formel **{formula_id}** aus **{script_id}** wird abgefragt..."
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    FORMULA_DB_URL, json=request_json_body
                ) as response:
                    if response.status != 200:
                        out_str = f"Die Anfrage ist fehlgeschlagen. Es wurde keine Formel mit ID '{formula_id}' in Skript '{script_id}' gefunden."
                        step.output = out_str
                        return out_str

                    response_json = await response.json()
                    step.output = f"Es wurde Formel ({response_json['formula_id']}) in Sektion **{response_json['section_name']}** aus Kapitel **{response_json['chapter_name']}** in **{response_json['document_name']}** wurde abgefragt.\n{response_json['content']}"

                    reference = to_reference(response_json, "formula")
                    update_references(reference)

                    return reference.print_reference()

        except ClientConnectorError as e:
            step.output = f"Server Aktuell nicht erreichbar."
            return "Der Server ist aktuell nicht erreichbar. Versuchen Sie es später erneut."


@tool(args_schema=QueryWolframAlpha)
async def query_wolfram_alpha(query: str) -> str:
    """
    The Wolfram Alpha API allows you to query a wide range of topics, including mathematics, physics, chemistry, and more.
    WolframAlpha performs mathematical calculations, date and unit conversions, formula solving, etc.
    Convert inputs to simplified keyword queries whenever possible (e.g. convert 'how many people live in France' to 'France population').
    Send queries in English only; translate non-English queries before sending, then respond in the original language.
    ALWAYS use this exponent notation: `6*10^14`, NEVER `6e14`.
    ALWAYS use proper Markdown formatting for all math, scientific, and chemical formulas, symbols, etc.:  '$$\n[expression]\n$$' for standalone cases and '\\( [expression] \\)' when inline.
    If data for multiple properties is needed, make separate calls for each property.
    """

    def format_query_response(
        response: dict,
    ) -> str:

        output_str = ""
        for key, value in response.items():
            output_str += f"**{key}**\n > {value}\n\n"

        return output_str

    def response_to_json(response_text: str) -> dict:
        res_arr = response_text.split("\n\n")
        ans_dict = {}
        for res in res_arr:
            res = res.split("\n")
            if len(res) > 1:
                key = res[0]
                values = res[1:]
                value_str = " ".join(values).strip()
                if "Wolfram|Alpha" in key:
                    continue
                if "image" in value_str:
                    continue
                if "assumption" in key.lower():
                    new_values = []
                    for value in values:
                        if value.endswith("--"):
                            continue
                        else:
                            new_values.append(value)
                    values = new_values
                    value_str = " ".join(values).strip()

                ans_dict[key] = value_str
        return ans_dict

    try:
        wolfram_app_id = os.getenv("WOLFRAM_APP_ID")
    except KeyError:
        return "Der Wolfram Alpha API Schlüssel ist nicht gesetzt. Bitte kontaktieren Sie den Administrator."
    if wolfram_app_id is None:
        return "Der Wolfram Alpha API Schlüssel ist nicht gesetzt. Bitte kontaktieren Sie den Administrator."

    query_url = WOLFRAM_URL.format(APP_ID=wolfram_app_id)
    query_url += urllib.parse.quote_plus(query)
    async with cl.Step(
        name="Wolfram Alpha",
        language=None,
        show_input=True,
        type="tool",
    ) as step:

        step.input = f"Die Anfrage an Wolfram Alpha wird gestellt:\n{query}"

        try:

            async with aiohttp.ClientSession() as session:
                async with session.get(query_url) as response:
                    if response.status != 200:
                        print(response.status)
                        print(await response.text())
                        step.output = "Die Anfrage ist fehlgeschlagen."
                        return "Die Anfrage ist fehlgeschlagen."

                    res_json = response_to_json(await response.text())

                    output_str = format_query_response(res_json)
                    step.output = output_str
                    return output_str

        except ClientConnectorError as e:
            step.output = f"Server aktuell nicht erreichbar."
            return "Der Server ist aktuell nicht erreichbar. Versuchen Sie es später erneut."


async def retrieve_section_no_step(
    script_id: str,
    chapter_id: str,
    section_id: str,
) -> str:

    retrival_settings = cl.user_session.get("settings")["retrieval_settings"]

    request_json_body = {
        "document_id": script_id,
        "chapter_id": chapter_id,
        "section_id": section_id,
        "collection_name": retrival_settings["collection_name"],
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(CHAPTER_DB_URL, json=request_json_body) as response:
                if response.status != 200:
                    out_str = f"Die Sektion {chapter_id}.{section_id} konnte nicht gefunden werden."
                    return out_str

                response_json = await response.json()
                reference = to_reference(response_json, "section")
                update_references(reference)

                return reference.print_reference()

    except ClientConnectorError as e:
        return (
            "Der Server ist aktuell nicht erreichbar. Versuchen Sie es später erneut."
        )


async def retrieve_table_of_contents_no_step(script_id: str) -> str:
    """
    Erfrage das Inhaltsverzeichnis eines spezifischen Vorlesungsskripts.
    Gibt das Inhaltsverzeichnis mit Sektions-IDs zurück.
    """

    ret_settings = cl.user_session.get("settings")["retrieval_settings"]

    request_json_body = {
        "document_id": script_id,
        "collection_name": ret_settings["collection_name"],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(TOC_DB_URL, json=request_json_body) as response:
            if response.status != 200:
                return "Es konnte kein Inhaltsverzeichnis gefunden werden."

            response_json: dict = await response.json()

            toc: list | None = response_json.get("toc", None)
            if toc is None:
                return "Es konnte kein Inhaltsverzeichnis gefunden werden."

            toc = "\n".join(toc)
            return toc


@tool(args_schema=QuestionSetup)
@cl.step(type="tool", name="Fragenersteller", show_input=False)
async def question_setup(topic: str | None = None) -> None:
    """Stellt dem Nutzer eine Frage aus einem bestimmten Thema oder einem zufälligen Thema."""

    current_step = cl.context.current_step
    current_step.output = "Frage wird erstellt..."

    def extract_section_parameters(section):
        chapter_id = section.split(".")[0]
        section_id = section.split(" ")[0].split(".")[1]
        script_id = section.split(" | ")[1]
        section_name = " ".join(section.split(" | ")[0].split(" ")[1:]).strip()

        return chapter_id, section_id, script_id, section_name

    # reset the chat history inplace
    chat_history: list[BaseMessage] = cl.user_session.get("chat_history", [])
    for _ in range(len(chat_history)):
        chat_history.pop()

    if topic is None:
        available_sections = cl.user_session.get("available_sections")
    else:
        try:
            ret_settings = cl.user_session.get("settings")["retrieval_settings"]
            request_json_body = {
                "query": topic,
                "collection_name": ret_settings["collection_name"],
                "top_k": ret_settings["top_k"] or 200,
                "top_n": 10,
                "use_rerank": ret_settings["use_rerank"] or False,
                "extend_results": False,
                "rerank_score_threshold": 0.5,
                "permitted_document_ids": cl.user_session.get("permitted_document_ids"),
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    VECTOR_DB_URL, json=request_json_body
                ) as response:

                    response_json = await response.json()
                    document_list: list[dict] = response_json["documents"]
                    if len(document_list) == 0:
                        await cl.Message(
                            content=f"Zu dem Thema **{topic}** konnten ich leider keine Sektionen finden. Ich werde eine zufällige Sektion auswählen."
                        ).send()
                        available_sections = cl.user_session.get("available_sections")
                    else:
                        available_sections = [
                            f"{doc['section_name']} | {doc['document_id']}"
                            for doc in document_list
                        ]
                        # deduplicate the list
                        available_sections = list(set(available_sections))

        except Exception as e:
            available_sections = cl.user_session.get("available_sections")

    random.seed(time.time())
    choosen_section = random.choice(available_sections)

    # if len(permitted_document_ids) == 1:
    #     choosen_section = await ask_user_for_section(choosen_section)

    (
        chapter_id,
        section_id,
        script_id,
        section_name,
    ) = extract_section_parameters(choosen_section)

    await cl.Message(
        content=f"Hier ist eine Frage aus **{script_id}** Kapitel **{chapter_id}**, Sektion **{section_id}** (**{section_name}**)."
    ).send()

    section_text = await retrieve_section_no_step(
        script_id=script_id,
        chapter_id=chapter_id,
        section_id=section_id,
    )

    cl.user_session.set(
        "current_exam_trainer_section",
        f"{script_id}.{chapter_id}.{section_id}",
    )
    cl.user_session.set(
        "current_exam_trainer_section_text",
        section_text,
    )

    if topic is None:
        query_text = f"Stell mir eine Frage zur folgenden Sektion:\n\n{section_text}"
        current_step.output = "Eine Frage zu einer zufälligen Sektion wurde erstellt."
    else:
        query_text = f"Stell mir eine Fragezur folgenden Sektion, sie sollte mit {topic} zutun haben:\n\n{section_text}"
        current_step.output = f"Eine Frage zu dem Thema **{topic}** wurde erstellt."

    chat_history: list[BaseMessage] = cl.user_session.get("chat_history", [])
    chat_history = add_system_message(chat_history, "exam_trainer")
    chat_history.append(
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": query_text,
                }
            ]
        )
    )
