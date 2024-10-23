import base64
import copy
import os
import uuid

import chainlit as cl
import cv2
import numpy as np
from constants.documents import DOCS
from constants.prompts import (
    POST_PROMPT,
    SYSTEM_PROMPT_EXAM_TRAINER_TEMPLATE,
    SYSTEM_PROMPT_TEMPLATE,
)
from constants.settings import DEFAULT_SETTINGS
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
)


def load_model() -> BaseChatModel:

    provider = os.getenv("LANDAU_MODEL_PROVIDER", "openai").lower()
    model_name = os.getenv("LANDAU_MODEL_NAME", "gpt-4o-mini")

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model=model_name,
            **DEFAULT_SETTINGS["model_settings"],
        )
    elif provider == "azure":
        from langchain_openai import AzureChatOpenAI

        model = AzureChatOpenAI(
            api_key=os.getenv("AZURE_OPENAI_CHAT_API_KEY"),
            azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
            api_version=os.getenv("AZURE_OPENAI_CHAT_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_CHAT_ENDPOINT"),
            **DEFAULT_SETTINGS["model_settings"],
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        model = ChatAnthropic(
            model=model_name,
            **DEFAULT_SETTINGS["model_settings"],
        )
    else:
        raise ValueError(
            f"Invalid provider. Got: {provider}, expected 'openai', 'azure' or 'anthropic'"
        )

    return model


def load_env_vars() -> None:
    # Load the environment variables from the .env file
    file_dir = os.path.dirname(os.path.realpath(__file__))
    env_path = os.path.join(file_dir, "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as env_file:
            for line in env_file:
                line = line.strip()

                # skip empty lines and comments
                if len(line) == 0 or line.startswith("#"):
                    continue

                # split the line into key and value
                arr = line.split("=")

                # The key is the first element and the value is the rest
                key = arr[0]

                # If the value contains an equal sign, join the rest of the elements
                value = "=".join(arr[1:])
                os.environ[key] = value


def image_to_base64(image_path: str, size: int = 512) -> str:
    image = cv2.imread(image_path)

    new_image = np.zeros((size, size, 3), dtype=np.uint8)

    h, w = image.shape[:2]
    if h > w:
        new_h = size
        new_w = int(w * (size / h))
    else:
        new_w = size
        new_h = int(h * (size / w))

    new_image[:new_h, :new_w] = cv2.resize(
        image,
        (new_w, new_h),
        interpolation=cv2.INTER_LINEAR,
    )

    new_image_path = f"saved_images/{uuid.uuid4()}.jpg"
    cv2.imwrite(new_image_path, new_image)
    with open(new_image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    return base64_image


def format_system_prompt(prompt_type: str = "default") -> str:
    permitted_document_ids = cl.user_session.get("permitted_document_ids", None)

    if permitted_document_ids is not None:
        permitted_documents = {
            document: DOCS[document] for document in permitted_document_ids
        }
    else:
        permitted_documents = DOCS

    if prompt_type == "default":
        permitted_document_string = "\n\n".join(
            [
                f"{document_id}. {document['name']}:\n{document['description']}"
                for document_id, document in permitted_documents.items()
            ]
        )
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            permitted_documents=permitted_document_string,
        )

    elif prompt_type == "exam_trainer":
        system_prompt = SYSTEM_PROMPT_EXAM_TRAINER_TEMPLATE.format(
            context=cl.user_session.get("current_exam_trainer_section_text")
        )
    else:
        raise ValueError(f"Invalid prompt type. Got: {prompt_type}")

    context = cl.user_session.get("copilot_context", None)
    if context is not None:
        system_prompt += (
            "\n\nAlle Fragen des Users beziehen sich auf das folgende Dokument:\n\n"
            f"{context}\n\n"
            "## Handlungsanweisungen\n"
            "Nimm an, das sich alle Fragen des Users auf dieses Dokument beziehen und Antworte entsprechend.\n"
            "Suche unter keinen umständen nach diesem Dokument und antworte nur auf Basis des aktuellen Dokuments."
        )

    return system_prompt


def inject_post_prompt(chat_history: list[BaseMessage]) -> list[BaseMessage]:
    """
    Injects the post prompt to the latest user message in the chat history.
    Returns a copy of the chat history with the post prompt injected.
    """
    chat_history_temp = copy.deepcopy(chat_history)

    if len(chat_history_temp) == 0:
        return chat_history_temp

    # go trough the chat history in reverse order
    # and inject the post prompt to the first user message
    for message in reversed(chat_history_temp):
        if type(message) == HumanMessage:
            if type(message.content) == list:
                for content in message.content:
                    if content["type"] == "text":
                        content["text"] += POST_PROMPT
            elif type(message.content) == str:
                message.content += POST_PROMPT
            break

    return chat_history_temp


def add_user_message(
    user_message: cl.Message,
    chat_history: list[BaseMessage],
    max_images: int = 1,
) -> list[BaseMessage]:

    query_string = user_message.content or ""
    query_images = [
        file
        for file in (user_message.elements or [])
        if "image" in file.mime and file.path is not None
    ]

    message_content = [{"type": "text", "text": query_string}]

    for image in query_images[:max_images]:
        message_content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_to_base64(image.path)}",
                    "detail": "low",
                },
            },
        )

    chat_history.append(HumanMessage(message_content))
    return chat_history


def add_system_message(
    chat_history: list[BaseMessage],
    prompt_type: str = "default",
) -> list[BaseMessage]:
    system_prompt = SystemMessage(format_system_prompt(prompt_type))

    if len(chat_history) == 0:
        chat_history.append(system_prompt)
    else:
        chat_history[0] = system_prompt

    return chat_history


async def maybe_add_message_quota_element(model_message: cl.Message) -> None:
    # Update the final message with an element if the user has reached the message quota
    # Dont do this if the user has unlimited messages
    app_settings = cl.user_session.get("settings")["app_settings"]
    max_messages = app_settings["max_messages"]
    if cl.user_session.get("num_user_messages") >= max_messages and max_messages > 0:
        model_message.elements.append(
            cl.Text(
                name="Message Quota Reached",
                content="You have reached the maximum amount of messages. Please start a new chat to continue.",
            )
        )
        await model_message.update()
