import copy
from typing import List

import chromadb
import pandas as pd
import tiktoken

from .transform_functions import add_embeddings, formatted_script_to_pandas


def add_toc_to_chroma(
    script_dataframe: pd.DataFrame,
    script_id: str,
    collection: chromadb.Collection,
) -> None:
    chapter_names = script_dataframe["chapter_name"].unique()
    chapter_names = sorted(chapter_names, key=lambda x: int(x.split(" ")[0]))
    toc = ""
    for chapter_name in chapter_names:
        chapter_df = script_dataframe[script_dataframe["chapter_name"] == chapter_name]
        section_names = chapter_df["section_name"].unique()
        section_names = sorted(
            section_names, key=lambda x: int(x.split(" ")[0].split(".")[1])
        )
        toc += f"{chapter_name}\n"
        for section_name in section_names:
            toc += f"{section_name}\n"
    toc = toc.strip()

    if collection.metadata is None:
        collection_metadata = {}
    else:
        collection_metadata = copy.deepcopy(collection.metadata)
    collection_metadata.update({script_id + "_toc": toc})
    collection.modify(metadata=collection_metadata)


def insert_script_into_chroma(
    script: dict,
    script_name: str,
    script_id: str,
    chroma_client: chromadb.ClientAPI,
    embedding_function: chromadb.EmbeddingFunction,
    collection_name: str,
) -> None:

    print("Converting Script to Pandas...", end=" ")
    script_dataframe = formatted_script_to_pandas(
        script=script,
        script_name=script_name,
        script_id=script_id,
    )
    print("Done")

    print("Adding Embeddings...", end=" ", flush=True)
    script_dataframe = add_embeddings(
        script_dataframe,
        embedding_function,
        token_target=0,
        overlap=0,
    )
    print("Done")

    print("Loading Chroma DB...", end=" ")
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function,
    )
    print("Done")

    print("Purging old script data if it exists...", end=" ")
    collection.delete(where={"document_id": script_id})
    if collection.metadata is not None:
        if (script_id + "_toc") in collection.metadata:
            collection_metadata = copy.deepcopy(collection.metadata)
            del collection_metadata[script_id + "_toc"]
            collection.modify(metadata=collection_metadata)
    print("Done")

    print("Adding table of contents to DB...", end=" ")
    add_toc_to_chroma(
        script_id=script_id,
        script_dataframe=script_dataframe,
        collection=collection,
    )
    print("Done")

    ids = script_dataframe["id"].astype(str).tolist()
    documents = script_dataframe["content"].astype(str).tolist()
    embeddings = script_dataframe["embedding"].tolist()
    metadatas = script_dataframe[
        script_dataframe.columns.difference(["content", "id", "embedding"])
    ].to_dict("records")

    ADD_PER_ITER = 1000
    for i in range(0, len(ids), ADD_PER_ITER):

        if i + ADD_PER_ITER < len(ids):
            print(f"Adding papers {i} to {i + ADD_PER_ITER}...")
            id_batch = ids[i : i + ADD_PER_ITER]
            embeddding_batch = embeddings[i : i + ADD_PER_ITER]
            document_batch = documents[i : i + ADD_PER_ITER]
            metadata_batch = metadatas[i : i + ADD_PER_ITER]
        else:
            print(f"Adding papers {i} to {len(ids)}...")
            id_batch = ids[i:]
            embeddding_batch = embeddings[i:]
            document_batch = documents[i:]
            metadata_batch = metadatas[i:]

        collection.upsert(
            ids=id_batch,
            embeddings=embeddding_batch,
            documents=document_batch,
            metadatas=metadata_batch,
        )


def extend_chroma_results(
    documents: pd.DataFrame,
    collection: chromadb.Collection,
    extend_radius: int = 4,
) -> pd.DataFrame:
    def _extract_continuous_segments(numbers):
        continuous_segments = []
        current_segment = []

        for number in sorted(numbers):
            if not current_segment or number == current_segment[-1] + 1:
                current_segment.append(number)
            else:
                continuous_segments.append(current_segment)
                current_segment = [number]

        if current_segment:
            continuous_segments.append(current_segment)

        return continuous_segments

    encoder = tiktoken.get_encoding("o200k_base")
    section_groups = documents.groupby(["document_id", "chapter_id", "section_id"])
    extended_documents = []

    for dcs_id, section_group in section_groups:
        dcs_id = f"{dcs_id[0]}.{dcs_id[1]}.{dcs_id[2]}"

        paragraph_ids = [entry["paragraph_id"] for _, entry in section_group.iterrows()]
        document_id = section_group["document_id"].values[0]

        # dont extend the paragraphs for the Feynman lectures they are already quite long
        if "FEYNMAN" in document_id:
            extented_paragraph_ids = [[paragraph_id] for paragraph_id in paragraph_ids]
        else:
            extented_paragraph_ids = []
            for paragraph_id in paragraph_ids:
                extented_paragraph_ids.extend(
                    [
                        paragraph_id + i
                        for i in range(-extend_radius, extend_radius + 1)
                        if paragraph_id + i >= 0
                    ]
                )
            extented_paragraph_ids = sorted(list(set(extented_paragraph_ids)))
            extented_paragraph_ids = _extract_continuous_segments(
                extented_paragraph_ids
            )

        max_scores = [0.0 for _ in extented_paragraph_ids]
        main_paragraph_ids = [None for _ in extented_paragraph_ids]
        # extract the max score for each group of paragraphs
        # if multiple paragraphs overlap, only the highest score is kept
        for i, extented_paragraph_id_group in enumerate(extented_paragraph_ids):
            paragraph_group = section_group[
                section_group["paragraph_id"].isin(extented_paragraph_id_group)
            ]
            main_paragraph = paragraph_group[
                paragraph_group["score"] == paragraph_group["score"].max()
            ]
            max_scores[i] = main_paragraph["score"].values[0]
            main_paragraph_ids[i] = main_paragraph["paragraph_id"].values[0]

        for extented_paragraph_id_group, max_score, main_paragraph_id in zip(
            extented_paragraph_ids, max_scores, main_paragraph_ids
        ):
            dcsp_ids = [
                f"{dcs_id}.{paragraph_id}"
                for paragraph_id in extented_paragraph_id_group
            ]

            results = collection.get(ids=dcsp_ids)
            metadatas = results["metadatas"]

            main_metadata = metadatas[0]
            if "reference_anchor" in main_metadata:
                del main_metadata["reference_anchor"]

            paragraph_ids = [int(metadata["paragraph_id"]) for metadata in metadatas]
            sorted_indices = sorted(
                range(len(paragraph_ids)), key=lambda k: paragraph_ids[k]
            )
            documents = [results["documents"][i] for i in sorted_indices]

            content = " ".join(documents)
            extendend_document: dict = main_metadata.copy()
            extendend_document.update(
                {
                    "id": f"{dcs_id}.{main_paragraph_id}",
                    "paragraph_id": main_paragraph_id,
                    "content": content,
                    "score": max_score,
                    "num_tokens": len(encoder.encode(content)),
                }
            )

            extended_documents.append(extendend_document)

    return pd.DataFrame(extended_documents)


def query_chroma_collection(
    queries: List[str],
    collection: chromadb.Collection,
    top_k: int = 25,
    permitted_document_ids: List[str] | None = None,
) -> pd.DataFrame:

    rows = []
    if permitted_document_ids:
        results = collection.query(
            query_texts=queries,
            n_results=top_k,
            include=["distances", "metadatas", "documents"],
            where={
                "document_id": {
                    "$in": permitted_document_ids,
                },
            },
        )
    else:
        results = collection.query(
            query_texts=queries,
            n_results=top_k,
            include=["distances", "metadatas", "documents"],
        )

    if len(results["ids"]) == 0:
        return pd.DataFrame()

    for query_idx in range(len(queries)):
        query_ids = results["ids"][query_idx]
        query_metadatas = results["metadatas"][query_idx]
        query_documents = results["documents"][query_idx]
        query_distances = results["distances"][query_idx]
        for result_idx in range(min(top_k, len(query_ids))):
            row = {
                "id": query_ids[result_idx],
                "score": query_distances[result_idx],
                "content": query_documents[result_idx],
            }
            ## Merge the metadata directly into the row dictionary
            row.update(query_metadatas[result_idx])
            rows.append(row)

    # Convert the list of row data into a DataFrame in one go
    final_df = pd.DataFrame(rows)
    # Drop duplicates by 'id' if necessary
    final_df = final_df.drop_duplicates(subset=["id"])

    return final_df
