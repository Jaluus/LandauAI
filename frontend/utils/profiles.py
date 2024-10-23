import asyncio

import chainlit as cl
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from .functions import (
    add_system_message,
    add_user_message,
    inject_post_prompt,
    maybe_add_message_quota_element,
)
from .stream_handler import handle_stream, handle_stream_output
from .tool_calling import execute_tool_call


async def default_profile(user_message: cl.Message) -> None:
    app_settings = cl.user_session.get("settings")["app_settings"]
    max_images = app_settings["max_images"]
    max_tool_recursion = app_settings["max_tool_recursion"]

    chat_history: list[BaseMessage] = cl.user_session.get("chat_history", [])
    model: BaseChatModel = cl.user_session.get("model")
    model_with_tools: BaseChatModel = cl.user_session.get("model_with_tools")

    # we need to add the user message to the chat history before we can limit the context and afterwords add the system message
    # this is done as the limit context function removes all messages which are too old
    # we inject the system message after the limit context function
    # TODO: THIS IS ULTRA HACKY; If I dont call the add_system_message function first thing, it will overwrite the user message
    chat_history = add_system_message(chat_history, "default")
    chat_history = add_user_message(user_message, chat_history, max_images)

    # TODO: Write a proper function to limit the context, I cant just cut off the last n messages, I might cut off a tool call.
    # chat_history = limit_context(chat_history, max_tokens=max_tokens)

    stream = model_with_tools.astream(inject_post_prompt(chat_history))
    model_message, tool_calls = await handle_stream(stream, model)
    tool_calls = await handle_stream_output(model_message, tool_calls)

    current_tool_recursion = 0
    while len(tool_calls) > 0:
        current_tool_recursion += 1

        # execute the tool calls concurrently
        await asyncio.gather(*[execute_tool_call(tool) for tool in tool_calls])

        # remove the tools if the model has recursed too many times
        stream = (
            model_with_tools.astream(inject_post_prompt(chat_history))
            if current_tool_recursion < max_tool_recursion
            else model.astream(inject_post_prompt(chat_history))
        )
        model_message, tool_calls = await handle_stream(stream, model)
        tool_calls = await handle_stream_output(model_message, tool_calls)

    await maybe_add_message_quota_element(model_message)


async def exam_trainer_profile(user_message: cl.Message) -> None:
    app_settings = cl.user_session.get("settings")["app_settings"]
    max_images = app_settings["max_images"]

    chat_history: list[BaseMessage] = cl.user_session.get("chat_history", [])
    model: BaseChatModel = cl.user_session.get("model")
    model_with_tools: BaseChatModel = cl.user_session.get("model_with_tools")

    chat_history = add_user_message(user_message, chat_history, max_images)

    stream = model_with_tools.astream(chat_history)
    model_message, tool_calls = await handle_stream(stream, model)
    tool_calls = await handle_stream_output(model_message, tool_calls)

    if len(tool_calls) > 0:

        # execute the tool calls concurrently
        await asyncio.gather(*[execute_tool_call(tool) for tool in tool_calls])

        stream = model.astream(chat_history)
        model_message, tool_calls = await handle_stream(stream, model)
        tool_calls = await handle_stream_output(model_message, tool_calls)

    await maybe_add_message_quota_element(model_message)
