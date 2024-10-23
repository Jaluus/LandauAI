import openai
import pandas as pd
import requests


def rerank_results(
    query: str,
    documents: pd.DataFrame,
    reranker,
) -> pd.DataFrame:
    contents = documents["content"].tolist()
    scores = reranker(query, contents)
    documents["rerank_score"] = scores
    return documents


def generate_multiquery(
    query: str,
    num_multiquery: int,
    openai_client: openai.Client,
) -> list[str]:

    if num_multiquery < 2:
        return []

    chat_completion = openai_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "## Task\n\n"
                f"Generate {num_multiquery} questions which are used to query a vector database "
                "based on the provided snippet.\n"
                "Each Question should be relevant to the snippet and help to return documents which are as relevant as possible.\n"
                "The snippets can be either questions or chunks of text.\n"
                "You returned questions are always in the language of the user question.\n"
                "E.g if the user question is in English, the returned questions should also be in English.\n"
                "If the user question is in German, the returned questions should also be in German.\n"
                "By generating multiple questions based on the snippet, your goal is to help the user overcome some of the limitations of the distance-based similarity search.\n"
                "Provide these alternative questions separated by newlines.\n"
                "## Example\n\n"
                "### Example Snippet\n\n"
                "How do the control mechanisms differ for exchange-only qubits, resonant exchange qubits, and always-on exchange-only qubits?\n\n"
                "### Example Output\n\n"
                "How are Exchange only qubits controlled?\n"
                "What are the control mechanisms for resonant exchange qubits?\n"
                "what are control mechanisms for always-on exchange-only qubits?\n"
                "Control Mechanisms for Qubits\n"
                "What is a control mechanism in qubits?\n\n"
                "## Provided Snippet\n\n"
                f"{query}",
            }
        ],
        model="gpt-4o",
    )

    questions = chat_completion.choices[0].message.content.split("\n")
    # remove all questions that are empty
    questions = [question for question in questions if len(question) > 0]
    return questions


def process_results(
    documents: pd.DataFrame,
    top_n: int = 5,
    rerank_score_threshold: float = 0.0,
) -> pd.DataFrame:

    # rename the score column to distance, as the "score" is typically the return value of the vector search
    # this is often the L2 or cosine distance
    documents = documents.rename(columns={"score": "distance"})

    if "rerank_score" in documents.columns:
        documents = (
            documents.sort_values(by=["rerank_score"], ascending=False)
            .query(f"rerank_score > {rerank_score_threshold}")
            .reset_index(drop=True)
            .sort_values(by=["rerank_score"], ascending=False)
            .head(top_n)
        )
        # rename the rerank_score column to score as this is the actual score we want to return
        # the score should always be a value between 0 and 1 and a high score indicates a high relevance
        documents = documents.rename(columns={"rerank_score": "score"})

    else:
        documents = (
            documents.sort_values(by=["distance"], ascending=True)
            .reset_index(drop=True)
            .sort_values(by=["distance"], ascending=True)
            .head(top_n)
        )

        # if the documents do not have a rerank_score, we can use the similarity score as the score
        # distance can be between 0 and infinity, so we need to normalize it to a score between 0 and 1
        # if distance is 0, the score will be 1, if distance is infinity, the score will be 0
        documents["score"] = documents["distance"].apply(lambda x: 1 / (1 + x))

    return documents


def poll_script(url, cookie=None):
    response = requests.get(url, cookies=cookie)
    return response.json()["index"]
