DEFAULT_SETTINGS = {
    "retrieval_settings": {
        "use_rerank": True,  # Use reranking
        "rerank_score_threshold": 0.1,  # Threshold for reranking
        "top_k": 200,  # Number of snippets to send to the Reranker
        "top_n": 5,  # Number of snippets to return to the LLM
        "collection_name": "default",  # The chroma collection to use
        "extend_results": True,  # Extend the documents with adjecent snippets
    },
    "model_settings": {
        "temperature": 0.3,  # Temperature for sampling
        "top_p": 0.4,  # Top p for nucleus sampling
        "streaming": True,  # Streaming mode
    },
    "app_settings": {
        "max_tokens": -1,  # Maximum amount of tokens to send to the model, -1 for unlimited
        "max_tool_recursion": 5,  # Maximum amount of tool recursions, the model must respond to the user after this amount
        "max_images": 1,  # Maximum amount of images to send to the model
        "max_messages": -1,  # Maximum amount of messages the user can send before the chat is stopped
    },
}
