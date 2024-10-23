import json
from typing import AsyncIterator

import chainlit as cl
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, BaseMessageChunk, ToolCall
from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from .reference_functions import add_references_to_messsage


def apply_tool_constraints(
    tool_calls: list[ToolCall],
    max_parallel_tool_calls: int = 3,
) -> list[ToolCall]:
    # discard all other tool calls and only keep the retrieve_table_of_contents
    tool_names = [tool["name"] for tool in tool_calls]
    if "retrieve_table_of_contents" in tool_names:
        tool_calls = [
            tool for tool in tool_calls if tool["name"] == "retrieve_table_of_contents"
        ]

    # only retrive a single section at a time
    tool_names = [tool["name"] for tool in tool_calls]
    if "retrieve_section" in tool_names:
        tool_calls = [
            tool for tool in tool_calls if tool["name"] == "retrieve_section"
        ][:1]

    # enforce a maximum amount of parallel tool calls
    tool_calls = tool_calls[:max_parallel_tool_calls]

    return tool_calls


def format_content(content: str) -> str:
    # Fixing LaTeX formatting
    # The model sometimes returns invalid LaTeX formatting
    # i.e. \( FORMEL \) instead of $FORMEL$
    # and \[ FORMEL \] instead of $$FORMEL$$
    content = content.replace(r"\(", "$")
    content = content.replace(r"\)", "$")
    content = content.replace(r"\[", "$$")
    content = content.replace(r"\]", "$$")
    return content


async def handle_anthropic_stream(
    stream: AsyncIterator[BaseMessageChunk],
) -> tuple[cl.Message, list[ToolCall]]:
    response_created = False
    tool_calls = []
    msg = None

    async for chunk in stream:
        if len(chunk.content) > 0:
            content = chunk.content[0]

            if content["type"] == "text":
                text_content = content.get("text", "")

                if not response_created:
                    msg = cl.Message(content="")
                    await msg.send()
                    response_created = True

                msg.content += text_content
                msg.content = format_content(msg.content)
                await msg.update()

            elif content["type"] == "tool_use":
                if "name" in content:
                    tool_calls.append(
                        {
                            "id": content["id"],
                            "name": content["name"],
                            "args": "",
                        }
                    )
                else:
                    tool_calls[-1]["args"] += content["partial_json"]

    for tool_call in tool_calls:
        tool_call["args"] = json.loads(tool_call["args"])

    return msg, tool_calls


async def handle_openai_stream(
    stream: AsyncIterator[BaseMessageChunk],
) -> tuple[cl.Message, list[ToolCall]]:
    response_created = False
    tool_calls = {}
    msg = None

    async for chunk in stream:
        text_content = chunk.content
        tool_content = chunk.additional_kwargs.get("tool_calls", None)

        if text_content:
            if not response_created:
                msg = cl.Message(content="")
                await msg.send()
                response_created = True

            msg.content += text_content
            msg.content = format_content(msg.content)
            await msg.update()

        if tool_content:
            for tool_call in tool_content:
                tool_index = tool_call["index"]
                tool_id = tool_call["id"]
                function_name = tool_call["function"]["name"]
                function_args = tool_call["function"]["arguments"]

                if tool_index not in tool_calls:
                    tool_calls[tool_index] = {}
                if tool_id is not None:
                    tool_calls[tool_index]["id"] = tool_id
                if function_name is not None:
                    tool_calls[tool_index]["name"] = function_name

                if function_args is not None:
                    if "args" not in tool_calls[tool_index]:
                        tool_calls[tool_index]["args"] = function_args
                    else:
                        tool_calls[tool_index]["args"] += function_args

    tool_calls = list(tool_calls.values())
    for tool_call in tool_calls:
        tool_call["args"] = json.loads(tool_call["args"])

    return msg, tool_calls


async def handle_ollama_stream(
    stream: AsyncIterator[BaseMessageChunk],
) -> tuple[cl.Message, list[ToolCall]]:
    response_created = False
    tool_calls = {}
    msg = None

    async for chunk in stream:
        text_content = chunk.content
        try:
            tool_content = chunk.tool_calls
        except AttributeError:
            tool_content = None
        if text_content:
            if not response_created:
                msg = cl.Message(content="")
                await msg.send()
                response_created = True

            msg.content += text_content
            msg.content = format_content(msg.content)
            await msg.update()

        if tool_content:
            for tool_call in tool_content:
                print(tool_call)
                tool_id = tool_call["id"]
                function_name = tool_call["name"]
                function_args = tool_call["args"]

                if tool_id not in tool_calls:
                    tool_calls[tool_id] = {}
                if tool_id is not None:
                    tool_calls[tool_id]["id"] = tool_id
                if function_name is not None:
                    tool_calls[tool_id]["name"] = function_name

                if function_args is not None:
                    if "args" not in tool_calls[tool_id]:
                        tool_calls[tool_id]["args"] = function_args
                    else:
                        tool_calls[tool_id]["args"] += function_args

    tool_calls = list(tool_calls.values())

    return msg, tool_calls


async def handle_stream(
    stream: AsyncIterator[BaseMessageChunk],
    model: BaseChatModel,
) -> tuple[cl.Message, list[ToolCall]]:
    if type(model) == ChatOpenAI:
        return await handle_openai_stream(stream)
    if type(model) == AzureChatOpenAI:
        return await handle_openai_stream(stream)
    elif type(model) == ChatAnthropic:
        return await handle_anthropic_stream(stream)
    elif type(model) == ChatOllama:
        return await handle_ollama_stream(stream)
    else:
        raise ValueError(f"Model type {type(model)} not supported.")


async def handle_stream_output(
    model_message: cl.Message | None,
    tool_calls: list[ToolCall],
) -> list[ToolCall]:
    chat_history: list[BaseMessage] = cl.user_session.get("chat_history", [])

    tool_calls = apply_tool_constraints(
        tool_calls,
        max_parallel_tool_calls=3,
    )

    if model_message:
        await add_references_to_messsage(model_message)
        chat_history.append(AIMessage(model_message.content, tool_calls=tool_calls))
    else:
        chat_history.append(AIMessage("", tool_calls=tool_calls))

    return tool_calls
