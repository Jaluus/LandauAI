FROM python:3.12.5-slim AS base

# install the dependencies for ffmpeg and openCV
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN mkdir -p /app/data

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements_frozen.txt,target=requirements_frozen.txt \
    python -m pip install -r requirements_frozen.txt

COPY . .

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Change ownership of the application directory
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

EXPOSE 7998

CMD ["chainlit", "run", "app.py", "--port=7998", "-h"]
