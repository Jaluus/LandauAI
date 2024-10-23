# Export the Chat history

You can export the chat History by running the `db_to_pkl.py` script.
This script will export the chat history to a pickle file.
Afterwards you can run teh `analyse_database.ipynb` to analyse the chat history.

## Notice

To be able to run the `db_to_pkl.py` script you need to expose the database port using docker-compose.
To do this you need to add the following line to the `docker-compose.yml` file:

```yaml
  postgres:
    image: "postgres:16.4"
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: postgres
    volumes:
      - ./frontend/data/postgres:/var/lib/postgresql/data
      - ./frontend/datalayer/pginit:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    ports: # add the port directive
      - 9669:5432
```

But only do this if you are sure that you dont expose the port to the wider internet!
