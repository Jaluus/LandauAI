import os
import time
from typing import Literal

import chromadb
from openai import AzureOpenAI, OpenAI


class OpenAI_Embedding(chromadb.EmbeddingFunction):
    def __init__(
        self,
        api_key: str | None = None,
        used_api: Literal["openai", "azure_openai"] | None = None,
        azure_deployment: str | None = None,
        azure_endpoint: str | None = None,
        azure_api_version: str | None = None,
        embedding_model: Literal[
            "text-embedding-3-small",
            "text-embedding-3-large",
        ] = "text-embedding-3-large",
        max_chunks_per_call: int = 2048,
        dim: int = -1,
        verbose: bool = False,
    ):

        used_api, api_key = self.__validate_api_keys(used_api, api_key)

        if azure_deployment is None:
            azure_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", None)
        if azure_endpoint is None:
            azure_endpoint = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT", None)
        if azure_api_version is None:
            azure_api_version = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION", None)

        if used_api == "openai":
            self.client = OpenAI(api_key=api_key)
        elif used_api == "azure_openai":
            if azure_deployment is None:
                raise ValueError(
                    "azure_deployment must be provided as an argument or in the environment variable AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
                )
            if azure_endpoint is None:
                raise ValueError(
                    "azure_endpoint must be provided as an argument or in the environment variable AZURE_OPENAI_EMBEDDING_ENDPOINT"
                )
            if azure_api_version is None:
                raise ValueError(
                    "azure_api_version must be provided as an argument or in the environment variable AZURE_OPENAI_EMBEDDING_API_VERSION"
                )
            self.client = AzureOpenAI(
                api_key=api_key,
                azure_deployment=azure_deployment,
                azure_endpoint=azure_endpoint,
                api_version=azure_api_version,
            )
        else:
            raise ValueError(
                f"USED_EMBEDDING_API must be one of 'openai' or 'azure', got {used_api}"
            )

        self.embedding_model = embedding_model
        self.dim = dim
        self.verbose = verbose
        if max_chunks_per_call > 2048:
            raise ValueError(
                f"max_chunks_per_call must be <= 2048, got {max_chunks_per_call}, OpenAI will only accept up to 2048 inputs per chunk."
            )
        self.max_chunks_per_call = max_chunks_per_call

    def __validate_api_keys(
        self,
        used_api: str | None = None,
        api_key: str | None = None,
    ) -> None:
        if used_api is None:
            used_api = os.getenv("USED_EMBEDDING_API", None)
            if used_api is None:
                print(f"WARNING: USED_EMBEDDING_API is None, using openai as default")
                used_api = "openai"

        if api_key is None:
            if used_api == "openai":
                api_key = os.getenv("OPENAI_API_KEY", None)
                if api_key is None:
                    raise ValueError(
                        "api_key must be provided as an argument or in the environment variable OPENAI_API_KEY as you are using the OpenAI API"
                    )

            elif used_api == "azure_openai":
                api_key = os.getenv("AZURE_OPENAI_EMBEDDING_API_KEY", None)
                if api_key is None:
                    raise ValueError(
                        "api_key must be provided as an argument or in the environment variable AZURE_OPENAI_EMBEDDING_API_KEY as you are using the Azure OpenAI API"
                    )

            else:
                raise ValueError(
                    f"USED_EMBEDDING_API must be one of 'openai' or 'azure', got {used_api}"
                )

        return used_api, api_key

    def __call__(
        self,
        input_list: list[str],
        sleep_time: int = 0,
    ) -> chromadb.Embeddings:
        embeddings = []
        for i in range(0, len(input_list), self.max_chunks_per_call):
            if i + self.max_chunks_per_call > len(input_list):
                if self.verbose:
                    print(f"Processing chunk {i} to {len(input_list)} (last chunk)")
                chunk = input_list[i:]
            else:
                if self.verbose:
                    print(
                        f"Processing chunk {i} to {i + self.max_chunks_per_call} of {len(input_list)}"
                    )
                chunk = input_list[i : i + self.max_chunks_per_call]
            embedding = self.client.embeddings.create(
                input=chunk,
                model=self.embedding_model,
            )
            embeddings.extend(
                [
                    (
                        embedding.data[i].embedding[: self.dim]
                        if self.dim > 0
                        else embedding.data[i].embedding
                    )
                    for i in range(len(embedding.data))
                ]
            )
            if i + self.max_chunks_per_call < len(input_list):
                time.sleep(sleep_time)
        return embeddings
