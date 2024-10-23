from typing import Self

from fastapi import HTTPException
from pydantic import BaseModel, model_validator


class DocumentQuery(BaseModel):
    query: str
    collection_name: str = "default"
    top_k: int = 10
    top_n: int = 5
    num_multiquery: int = 0
    rerank_score_threshold: float = 0.0
    use_rerank: bool = False
    extend_results: bool = False
    permitted_document_ids: list[str] | None = None

    @model_validator(mode="after")
    def custom_validation(self) -> Self:

        if len(self.query.strip()) < 5:
            raise HTTPException(
                400,
                detail="query must be at least 5 characters long",
            )

        if self.collection_name.strip() == "":
            raise HTTPException(
                400,
                detail="collection_name must not be empty",
            )

        if self.top_k < 1:
            raise HTTPException(
                400,
                detail="top_k must be greater than 0",
            )

        if self.top_n < 1:
            raise HTTPException(
                400,
                detail="top_n must be greater than 0",
            )

        if self.top_k < self.top_n:
            raise HTTPException(
                400,
                detail="top_k must be greater than or equal to top_n",
            )

        if self.num_multiquery < 0:
            raise HTTPException(
                400,
                detail="num_multiquery must be greater than or equal to 0",
            )

        if self.rerank_score_threshold < 0 or self.rerank_score_threshold > 1:
            raise HTTPException(
                400,
                detail="rerank_score_threshold must be between 0 and 1",
            )

        return self


class TOCRequest(BaseModel):
    document_id: str
    collection_name: str = "default"

    @model_validator(mode="after")
    def custom_validation(self) -> Self:

        if self.document_id.strip() == "":
            raise HTTPException(
                400,
                detail="document_id must not be empty",
            )

        if self.collection_name.strip() == "":
            raise HTTPException(
                400,
                detail="collection_name must not be empty",
            )

        return self


class SectionRequest(BaseModel):
    document_id: str
    chapter_id: str
    section_id: str
    collection_name: str = "default"


class FormulaRequest(BaseModel):
    document_id: str
    formula_id: str
    collection_name: str = "default"

    @model_validator(mode="after")
    def custom_validation(self) -> Self:

        if self.formula_id.strip() == "":
            raise HTTPException(
                400,
                detail="formula must not be empty",
            )

        if self.collection_name.strip() == "":
            raise HTTPException(
                400,
                detail="collection_name must not be empty",
            )

        return self


class ScriptInsert(BaseModel):
    script_content: dict
    script_name: str
    script_id: str
    collection_name: str = "default"
    skip_format_and_lint: bool = True

    @model_validator(mode="after")
    def custom_validation(self) -> Self:

        if self.script_name.strip() == "":
            raise HTTPException(
                400,
                detail="name must not be empty",
            )

        if self.script_id.strip() == "":
            raise HTTPException(
                400,
                detail="id must not be empty",
            )

        return self
