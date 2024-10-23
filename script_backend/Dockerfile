FROM python:3.12.5-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements_frozen.txt,target=requirements_frozen.txt \
    python -m pip install -r requirements_frozen.txt

COPY . .

EXPOSE 7999

CMD [ "uvicorn", "app:app", "--host=0.0.0.0", "--port=7999" ]