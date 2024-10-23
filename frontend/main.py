from datetime import datetime, timedelta

import jwt
import requests
from chainlit.utils import mount_chainlit
from constants.urls import VALIDATION_URL
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8000",
    "https://phyphox.org",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

with open("./.env") as f:
    lines = f.readlines()
    for line in lines:
        if not line.strip():
            continue

        splitted_line = line.strip().split("=")
        key = splitted_line[0]
        # remove the quotes
        value = "=".join(splitted_line[1:])[1:-1]
        if key == "CHAINLIT_AUTH_SECRET":
            CHAINLIT_AUTH_SECRET = value


def create_jwt(identifier: str, metadata: dict) -> str:
    to_encode = {
        "identifier": identifier,
        "metadata": metadata,
        "exp": datetime.now() + timedelta(hours=8),  # 8 hours
    }

    encoded_jwt = jwt.encode(to_encode, CHAINLIT_AUTH_SECRET, algorithm="HS256")
    return encoded_jwt


@app.post("/externalauth")
async def read_main(request: Request):
    try:
        json_body = await request.json()
        access_token = json_body["access_token"]
    except KeyError:
        return {"message": "Invalid request"}

    response = requests.get(f"{VALIDATION_URL}{access_token}")
    if response.status_code != 200:
        return {"message": "Invalid session id"}

    response_json = response.json()

    if not response.json().get("valid"):
        return {"message": "Invalid session id"}

    # dumb fix to make the user id unique to copilot
    userid = response_json.get("userid") + "_copilot"
    role = response_json.get("userroles")

    token = create_jwt(
        userid,
        {
            "role": role,
            "provider": "header",
        },
    )

    return {"access_token": token}


mount_chainlit(app=app, target="app.py", path="")
