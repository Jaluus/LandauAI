import chromadb
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from utils.app_dataclasses import (
    ScriptInsert,
    DocumentQuery,
    FormulaRequest,
    SectionRequest,
    TOCRequest,
)
from utils.chroma_functions import (
    extend_chroma_results,
    insert_script_into_chroma,
    query_chroma_collection,
)
from utils.etc_functions import load_env_vars
from utils.query_functions import generate_multiquery, process_results, rerank_results
from utils.transform_functions import format_script, linting_script
from wrappers.cohere_wrappers import Cohere_Reranker
from wrappers.openai_wrappers import OpenAI_Embedding

load_env_vars()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

reranker = Cohere_Reranker()
embedding_function = OpenAI_Embedding()
chroma_client = chromadb.HttpClient(
    host="chroma",
    port=8000,
    settings=chromadb.Settings(
        allow_reset=True,
        anonymized_telemetry=False,
    ),
)


@app.post("/insert_script")
def insert_script(script_insert: ScriptInsert):

    script_content = script_insert.script_content
    script_name = script_insert.script_name
    script_id = script_insert.script_id

    if not script_insert.skip_format_and_lint:
        script_content = linting_script(format_script(script_content))

    insert_script_into_chroma(
        script=script_content,
        script_name=script_name,
        script_id=script_id,
        chroma_client=chroma_client,
        embedding_function=embedding_function,
        collection_name=script_insert.collection_name,
    )

    return {
        "status": f"Successfully inserted document '{script_name}' with id '{script_id}' into the collection '{script_insert.collection_name}'"
    }


@app.post("/query")
def query_database(document_query: DocumentQuery):

    try:
        collection = chroma_client.get_collection(
            name=document_query.collection_name,
            embedding_function=embedding_function,
        )
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{document_query.collection_name}' not found",
        )

    queries = [document_query.query]

    # Sometimes leads to errors, so disabled for now
    if document_query.num_multiquery > 1 and False:
        queries.append(
            generate_multiquery(
                original_query,
                num_multiquery,
                openai_client,
            )
        )

    documents: pd.DataFrame = query_chroma_collection(
        collection=collection,
        queries=queries,
        top_k=document_query.top_k,
        permitted_document_ids=document_query.permitted_document_ids,
    )

    if len(documents) == 0:
        return {
            "queries": queries,
            "documents": [],
        }

    if document_query.use_rerank:
        documents: pd.DataFrame = rerank_results(
            query=queries[0],
            documents=documents,
            reranker=reranker,
        )

    documents: pd.DataFrame = process_results(
        documents=documents,
        top_n=document_query.top_n,
        rerank_score_threshold=document_query.rerank_score_threshold,
    )

    if document_query.extend_results:
        documents: pd.DataFrame = extend_chroma_results(
            documents=documents,
            collection=collection,
        )

    return {
        "queries": queries,
        "documents": documents.to_dict(orient="records"),
    }


@app.post("/toc")
def retrieve_toc(toc_request: TOCRequest):

    try:
        collection = chroma_client.get_collection(
            name=toc_request.collection_name,
            embedding_function=embedding_function,
        )
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{toc_request.collection_name}' not found",
        )

    try:
        toc = collection.metadata[toc_request.document_id + "_toc"]
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"The Table of Content for '{toc_request.document_id}' not found in the collection '{toc_request.collection_name}'",
        )

    # now format the TOC, as Chroma supports only a string
    toc = toc.split("\n")

    return {
        "collection_name": toc_request.collection_name,
        "document_id": toc_request.document_id,
        "toc": toc,
    }


@app.post("/section")
def retrieve_section(section_request: SectionRequest):

    print(section_request)

    try:
        collection = chroma_client.get_collection(
            name=section_request.collection_name,
            embedding_function=embedding_function,
        )
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{section_request.collection_name}' not found",
        )

    db_response = collection.get(
        where={
            "$and": [
                {"document_id": section_request.document_id},
                {"chapter_id": section_request.chapter_id},
                {"section_id": section_request.section_id},
            ]
        }
    )

    if len(db_response["ids"]) == 0:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Chapter with id '{section_request.chapter_id}'"
                f"and section with id '{section_request.section_id}'"
                f"in document '{section_request.document_id}' not found in the database"
            ),
        )

    metadatas = db_response["metadatas"]
    paragraph_ids = [metadata["paragraph_id"] for metadata in metadatas]
    documents = db_response["documents"]

    # sort the documents and ref_idxs by the ref_idxs
    # this is necessary because the ref_idxs are not always in order and we concatenate the documents
    # If we don't sort the documents, the paragraphs will be out of order
    sorted_paragraph_id_indexs = sorted(
        range(len(paragraph_ids)), key=lambda k: int(paragraph_ids[k])
    )

    return {
        "document_id": section_request.document_id,
        "chapter_id": section_request.chapter_id,
        "section_id": section_request.section_id,
        "document_name": metadatas[0]["document_name"],
        "chapter_name": metadatas[0]["chapter_name"],
        "section_name": metadatas[0]["section_name"],
        "content": "\n".join([documents[i] for i in sorted_paragraph_id_indexs]),
    }


@app.post("/formula")
def retrieve_formula(formula_request: FormulaRequest):

    try:
        collection = chroma_client.get_collection(
            name=formula_request.collection_name,
            embedding_function=embedding_function,
        )
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{formula_request.collection_name}' not found",
        )

    db_response = collection.get(
        where={
            "$and": [
                {"document_id": formula_request.document_id},
                {"formula_id": formula_request.formula_id},
            ],
        }
    )

    if len(db_response["ids"]) == 0:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Formula with id '{formula_request.formula_id}'"
                f"in document '{formula_request.document_id}' not found in the database"
            ),
        )

    metadata = db_response["metadatas"][0]
    document = db_response["documents"][0]

    return {
        "document_id": metadata["document_id"],
        "chapter_id": metadata["chapter_id"],
        "section_id": metadata["section_id"],
        "formula_id": metadata["formula_id"],
        "document_name": metadata["document_name"],
        "chapter_name": metadata["chapter_name"],
        "section_name": metadata["section_name"],
        "content": document,
    }
