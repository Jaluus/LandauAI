import json
import os
import requests

FILE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

scripts = {
    "FEYNMANI": "data/scripts/FEYNMANI.json",
    "FEYNMANII": "data/scripts/FEYNMANII.json",
    "FEYNMANIII": "data/scripts/FEYNMANIII.json",
}
script_names = [
    "The Feynman Lectures I",
    "The Feynman Lectures II",
    "The Feynman Lectures III",
]

for index, (script_id, script_path) in enumerate(scripts.items()):
    script_path = os.path.join(FILE_DIR, script_path)
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    json_body = {
        "script_id": script_id,
        "script_content": script,
        "script_name": script_names[index],
    }

    response = requests.post("http://localhost:9667/insert_script", json=json_body)

    print(response.json())
