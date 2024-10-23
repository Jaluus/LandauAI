import random

import chainlit as cl
from langchain.pydantic_v1 import ValidationError
from langchain_core.messages import ToolCall, ToolMessage

from .tools import (
    query_vector_db,
    query_wolfram_alpha,
    question_setup,
    retrieve_formula,
    retrieve_section,
    retrieve_table_of_contents,
)


def generate_tool_id() -> str:
    # generate a 24 character long id
    # with Big and small letters and numbers
    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    call_id = "".join(random.choices(letters, k=24))
    return f"call_{call_id}"


async def execute_tool_call(tool: ToolCall) -> None:
    async def handle_query_vector_db(
        args: dict,
        **kwargs,
    ) -> str:
        try:
            tool_response = await query_vector_db.arun(tool_input=args)
        except ValidationError as e:
            tool_response = f"Database query failed. Bad arguments. Error: {str(e)}"
        return tool_response

    async def handle_retrieve_table_of_contents(
        args: dict,
        permitted_document_ids: list[str] | None = None,
        **kwargs,
    ) -> str:
        script_id = args.get("script_id", None)

        if permitted_document_ids and script_id not in permitted_document_ids:
            return f"Table of Contents retrieval failed. Document not permitted. Only the following documents are currently permitted: {permitted_document_ids}"

        try:
            tool_response = await retrieve_table_of_contents.arun(tool_input=args)
        except ValidationError as e:
            tool_response = (
                "Table of Contents retrieval failed. Bad arguments. Error: {str(e)}"
            )

        return tool_response

    async def handle_query_wolfram_alpha(
        args: dict,
        **kwargs,
    ) -> str:
        try:
            tool_response = await query_wolfram_alpha.arun(tool_input=args)
        except ValidationError as e:
            tool_response = (
                f"Wolfram Alpha query failed. Bad arguments. Error: {str(e)}"
            )

        return tool_response

    async def handle_retrieve_section(
        args: dict,
        permitted_document_ids: list[str] | None = None,
        **kwargs,
    ) -> str:
        script_id = args.get("script_id", None)

        if permitted_document_ids and script_id not in permitted_document_ids:
            return f"Section retrieval failed. Document not permitted. Only the following documents are currently permitted: {permitted_document_ids}"

        try:
            tool_response = await retrieve_section.arun(tool_input=args)
        except ValidationError as e:
            tool_response = f"section retrieval failed. Bad arguments. Error: {str(e)}"

        return tool_response

    async def handle_retrieve_formula(
        args: dict,
        permitted_document_ids: list[str] | None = None,
        **kwargs,
    ) -> str:
        script_id = args.get("script_id", None)

        if permitted_document_ids and script_id not in permitted_document_ids:
            return f"Formula retrieval failed. Document not permitted. Only the following documents are currently permitted: {permitted_document_ids}"

        try:
            tool_response = await retrieve_formula.arun(tool_input=args)
        except ValidationError as e:
            tool_response = f"Formula retrieval failed. Bad arguments. Error: {str(e)}"

        return tool_response

    async def handle_question_setup(args: dict) -> None:
        await question_setup.arun(tool_input=args)

    permitted_document_ids = cl.user_session.get("permitted_document_ids", None)
    tool_id = tool["id"]
    tool_name = tool["name"]
    tool_args = tool.get("args", {}) or {}

    if tool_name == "query_vector_db":
        tool_response = await handle_query_vector_db(tool_args)

    elif tool_name == "retrieve_table_of_contents":
        tool_response = await handle_retrieve_table_of_contents(tool_args)

    elif tool_name == "query_wolfram_alpha":
        tool_response = await handle_query_wolfram_alpha(tool_args)

    elif tool_name == "retrieve_section":
        tool_response = await handle_retrieve_section(tool_args, permitted_document_ids)

    elif tool_name == "retrieve_formula":
        tool_response = await handle_retrieve_formula(tool_args, permitted_document_ids)

    elif tool_name == "question_setup":
        await handle_question_setup(tool_args)
        return

    else:
        tool_response = f"Tool call failed. Function '{tool['name']}' not found."

    chat_history: list = cl.user_session.get("chat_history")
    chat_history.append(
        ToolMessage(
            tool_call_id=tool_id,
            name=tool_name,
            content=tool_response,
        )
    )
