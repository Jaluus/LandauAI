import os

import chainlit as cl
import requests
from chainlit.input_widget import Switch
from constants.documents import DOCS
from constants.settings import DEFAULT_SETTINGS
from constants.starters import COPILOT_STARTERS, DEFAULT_STARTERS
from constants.urls import LOGIN_URL, VALIDATION_URL
from utils.copilot import add_context_to_copilot
from utils.exam_trainer import setup_exam_trainer
from utils.functions import load_env_vars, load_model
from utils.profiles import default_profile, exam_trainer_profile
from utils.tools import (
    query_vector_db,
    query_wolfram_alpha,
    retrieve_formula,
    retrieve_section,
    retrieve_table_of_contents,
)

load_env_vars()

if os.getenv("PERSISTENCE", None) is not None and os.getenv("PERSISTENCE") == "true":
    import datalayer.datalayer


@cl.set_chat_profiles
async def chat_profile():

    return [
        cl.ChatProfile(
            name="Vorlesungsbegleiter",
            markdown_description="Hilfreicher Modus um Vorlesungen zu begleiten, Fragen zu beantworten und mehr.",
            starters=[
                cl.Starter(
                    label=starter["label"],
                    message=starter["message"](),
                    icon=starter["icon"],
                )
                for starter in DEFAULT_STARTERS.copy()[:4]
            ],
        ),
        cl.ChatProfile(
            name="Wissenstrainer (Beta Feature)",
            markdown_description="Spezieller Modus um Wissen über das Skript abzufragen. Stellt in der Regel sehr schwierige Fragen.",
            starters=None,
        ),
    ]


@cl.password_auth_callback
def password_auth_callback(username: str, password: str) -> cl.User | None:
    # Fetch the user matching username from your database
    # and compare the hashed password with the value stored in the database
    if (username, password) == ("demo", "hypermodern"):
        return cl.User(
            identifier="Demo User",
            display_name="Demo User",
            metadata={
                "role": "Demo",
                "provider": "credentials",
            },
        )
    else:
        return None


# @cl.header_auth_callback
# def header_auth_callback(headers: dict) -> cl.User | None:
#     # https://phyphox.org/ex1/script/externalauth.php?href=https://landau.uslu.tech/login
#     ref_url: str = headers.get("referer", "")

#     # make sure the referrer is the login page
#     if not ref_url.startswith(LOGIN_URL):
#         return None

#     URL_args = ref_url.split("?")

#     # make sure the URL has query parameters
#     if len(URL_args) != 2:
#         return None

#     query_args = dict(q.split("=") for q in URL_args[1].split("&"))

#     # make auth_token is present in the query parameters
#     if "auth_token" not in query_args:
#         return None

#     # validate the auth_token against the validation endpoint
#     # also retrieve the user id and role from the response
#     response = requests.get(f"{VALIDATION_URL}{query_args['auth_token']}")
#     if response.status_code != 200:
#         return None

#     response_json = response.json()

#     # make sure the response is valid
#     if response_json["valid"]:
#         try:
#             user_id = response_json["userid"]
#             role = response_json["userroles"]
#             return cl.User(
#                 identifier=user_id,
#                 display_name="Student",
#                 metadata={
#                     "role": role,
#                     "provider": "header",
#                 },
#             )
#         except KeyError:
#             return None

#     return None


@cl.set_starters
async def set_starters(user: cl.User) -> list[cl.Starter]:
    try:
        chat_profile = cl.user_session.get("chat_profile")
    except Exception:
        chat_profile = None

    try:
        if user.identifier.endswith("_copilot"):
            starters = COPILOT_STARTERS.copy()
        else:
            starters = DEFAULT_STARTERS.copy()
    except AttributeError:
        starters = DEFAULT_STARTERS.copy()

    if chat_profile != "Wissenstrainer (Beta Feature)":
        return [
            cl.Starter(
                label=starter["label"],
                message=starter["message"](),
                icon=starter["icon"],
            )
            for starter in starters[:4]
        ]


@cl.on_settings_update
async def change_lectures(selected_documents: dict) -> None:
    permitted_document_ids = [
        lecture_id
        for lecture_id, is_permitted in selected_documents.items()
        if is_permitted
    ]
    if len(permitted_document_ids) == 0:
        permitted_document_ids = None

    cl.user_session.set("permitted_document_ids", permitted_document_ids)


@cl.on_chat_start
async def on_chat_start() -> None:
    selected_documents = await cl.ChatSettings(
        [
            Switch(
                id=doc_id,
                label=doc["name"],
                initial=doc["default"],
                description=doc["description"],
            )
            for doc_id, doc in DOCS.items()
        ]
    ).send()

    permitted_document_ids = [
        lecture_id
        for lecture_id, is_permitted in selected_documents.items()
        if is_permitted
    ]

    if len(permitted_document_ids) == 0:
        permitted_document_ids = None

    model = load_model()
    model_with_tools = model.bind_tools(
        [
            retrieve_formula,
            retrieve_section,
            retrieve_table_of_contents,
            query_vector_db,
            # query_wolfram_alpha,
        ]
    )

    cl.user_session.set("model", model)
    cl.user_session.set("model_with_tools", model_with_tools)
    cl.user_session.set("permitted_document_ids", permitted_document_ids)
    cl.user_session.set("settings", DEFAULT_SETTINGS)
    cl.user_session.set("chat_history", [])
    cl.user_session.set("references", [])
    cl.user_session.set("copilot_context", None)
    cl.user_session.set("num_user_messages", 0)

    chat_profile = cl.user_session.get("chat_profile")
    if chat_profile == "Wissenstrainer (Beta Feature)":
        await setup_exam_trainer()


# Decorator to process each message sent by the user
@cl.on_message
async def main(message: cl.Message) -> None:
    chat_profile = cl.user_session.get("chat_profile")

    if chat_profile == "Wissenstrainer (Beta Feature)":
        await exam_trainer_profile(message)

    else:
        if cl.context.session.client_type == "copilot":
            await add_context_to_copilot()

        await default_profile(message)
