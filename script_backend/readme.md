# Landau Script Backend

The Backend for the Landau Chatbot to handle the lecturescript.

## Installation without Docker

The Code is tested with Python 3.12.5.  
It is strongly recommended to use python >= 3.12 due to the use of type hints.
Example installation with conda and a virtual environment on a linux system:

```bash
conda create -n landau_server python=3.12
conda activate landau_server
pip install -r requirements.txt
```

Then create a `.env` file next to the `.env.example` file where you can see the required environment variables.

You can then start the chroma server by running the following command:

```bash
chroma run --path /path/to/database
```

Note that the chroma script database will be empty in the beginning.
To add sample scripts you can download the Feynman scripts using the `script_backend/tools/download_feynman.py` script.
Afterwards you need to upload the scripts to the database using the `script_backend/tools/upload_feynman_scripts.py` script.

## Loading data into the database

To load data into the database you can use the `insert_script_into_chroma` function in the `utils/chroma_functions.py` file.

### Input format

It expects the script to be a dict with the following layout:

```python
{
    "1 CHAPTER_NAME_1": {
        "1.1 SECTION_NAME_1": {
            "0": "PARAGRAPH_TEXT"
            "1": "PARAGRAPH_TEXT"
            ...
        },
        "1.2 SECTION_NAME_2": {
            "0": "PARAGRAPH_TEXT"
            "1": "PARAGRAPH_TEXT"
            ...
        },
    },
    "2 CHAPTER_NAME_2": {
        "2.1 SECTION_NAME_1": {
            "0": "PARAGRAPH_TEXT"
            "1": "PARAGRAPH_TEXT"
            ...
        },
        ...
    },
}
        ...
```

Here is an example from the Feynam Lectures Vol I.:

```python
{
    "1 Atoms in Motion": {
        "1.1 Introduction": {
            "0": "This two-year course in physics ...",
            "1": "Surprisingly enough, in spite of t...",
            "2": "You might ask ...",
            ...
        },
        "1.2 Matter is made of atoms": {
            "0": "If, in some cataclysm, all of scientific ...",
            "1": "To illustrate the ..."
            ...
        },
        ...
    }
    ...
}
```

## Start the server

Running the following command at the root of the project will start the server:

```bash
uvicorn app:app --host 0.0.0.0 --port 7999 --workers 4
```
