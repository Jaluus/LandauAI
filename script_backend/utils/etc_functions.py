import os


def load_env_vars() -> None:
    # Load the environment variables from the .env file
    file_dir = os.path.dirname(os.path.realpath(__file__))
    env_path = os.path.join(file_dir, "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as env_file:
            for line in env_file:
                arr = line.strip().split("=")
                key = arr[0]
                value = "=".join(arr[1:])
                value = value.strip('"')
                os.environ[key] = value
