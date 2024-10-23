import asyncio
import re

import chainlit as cl

from .stream_handler import handle_stream, handle_stream_output
from .tools import question_setup, retrieve_table_of_contents_no_step


async def retrieve_available_sections(permitted_document_ids):
    responses = await asyncio.gather(
        *[
            retrieve_table_of_contents_no_step(doc_id)
            for doc_id in permitted_document_ids
        ]
    )

    available_sections = [res.split("\n") for res in responses]
    available_sections = [
        [f"{section} | {doc_id}" for section in sections]
        for doc_id, sections in zip(permitted_document_ids, available_sections)
    ]
    available_sections = [item for sublist in available_sections for item in sublist]
    available_sections = [
        section for section in available_sections if re.match(r"^\d+\.\d+", section)
    ]
    available_sections = [
        section
        for section in available_sections
        if not any(
            word in section.lower()
            for word in ["ausblick", "zusammenfassung", "anhang"]
        )
    ]

    return available_sections


async def ask_user_for_section(available_sections):
    msg = cl.AskUserMessage(
        content="Gibt es eine spezielle Sektion, die du lernen möchtest?\nGib einfach die Kapitelnummer an, z.B. **1.2** für Kapitel 1, Sektion 2.\nWenn nicht tipp einfach **n**.",
    )
    res = await msg.send()

    if res and res.get("output"):
        section_id = res.get("output")

        # check if the section_id has the correct format
        if re.match(r"^\d+\.\d+", section_id):
            # check if the section_id is in the available_sections
            for section in available_sections:
                if section.startswith(section_id):
                    choosen_section = section
                    break
            else:
                msg.content = "Die Sektion habe ich nicht gefunden. Ich wähle eine zufällige Sektion für dich aus."
                await msg.update()
        else:
            msg.content = "Die Sektion hat nicht das richtige Format. Ich wähle eine zufällige Sektion für dich aus."
            await msg.update()

    return choosen_section


async def setup_exam_trainer():
    msg = cl.AskActionMessage(
        content="Welche Skripte soll ich für die Prüfung benutzen?",
        actions=[
            cl.Action(
                name="Die Erste Feynman Vorlesung",
                value="FEYNMANI",
                label="Die Erste Feynman Vorlesung",
            ),
            cl.Action(
                name="Die Zweite Feynman Vorlesung",
                value="FEYNMANII",
                label="Die Zweite Feynman Vorlesung",
            ),
            cl.Action(
                name="Die Dritte Feynman Vorlesung",
                value="FEYNMANIII",
                label="Die Dritte Feynman Vorlesung",
            ),
        ],
    )

    res = await msg.send()

    if res and res.get("value") == "FEYNMANI":
        msg.content = "Alles klar, ich werde die erste Feynman Vorlesung benutzen."
        permitted_document_ids = ["FEYNMANI"]
    elif res and res.get("value") == "FEYNMANII":
        msg.content = "Alles klar, ich werde die zweite Feynman Vorlesung benutzen."
        permitted_document_ids = ["FEYNMANII"]
    elif res and res.get("value") == "FEYNMANIII":
        msg.content = "Alles klar, ich werde die dritte Feynman Vorlesung benutzen."
        permitted_document_ids = ["FEYNMANIII"]
    else:
        return
    await msg.update()

    cl.user_session.set("permitted_document_ids", permitted_document_ids)

    available_sections = await retrieve_available_sections(permitted_document_ids)
    cl.user_session.set("available_sections", available_sections)
    model = cl.user_session.get("model")
    model_with_tools = model.bind_tools(
        [
            question_setup,
        ]
    )

    cl.user_session.set("model_with_tools", model_with_tools)

    await question_setup.arun({})

    chat_history = cl.user_session.get("chat_history")
    model = cl.user_session.get("model")
    stream = model.astream(chat_history)
    model_message, tool_calls = await handle_stream(stream, model)
    tool_calls = await handle_stream_output(model_message, tool_calls)
