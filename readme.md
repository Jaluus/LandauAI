# Landau AI

This is the Landau AI system of the 2nd Institue of Physics at the RWTH Aachen University.

> [!NOTE]  
This documentation is by no means comprehensive and will be updated regularly.

## Quickstart

To get started quickly, you can use `docker compose` to start the frontend and backend including the databases.
To do so, you can run the following command in the root directory of the project:

```bash
docker compose up --build
```

This build the docker containers and deploys them to the following ports:

| Service  | Port | Description                         |
| -------- | ---- | ----------------------------------- |
| frontend | 9668 | What the user sees                  |
| backend  | 9667 | What the LLM interacts with         |
| chroma   | 9666 | Where the scripts are stored        |
| postgres | 9669 | Where the chat histories are stored |

to stop the services, you can run:

```bash
docker compose down
```

> [!NOTE]  
> The chroma script database will be empty in the beginning.  
> To add sample scripts you can download the Feynman scripts using the `script_backend/tools/download_feynman.py` script.  
> Afterwards you need to upload the scripts to the database using the `script_backend/tools/upload_feynman_scripts.py` script.

### Frontend

To get started with the frontend, you can follow the guide in the `frontend` directory.
It can be found [here](frontend/readme.md).

### Backend

To get started with the backend, you can follow the guide in the `backend` directory.
It can be found [here](script_backend/Readme.md).
