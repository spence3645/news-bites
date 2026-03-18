from sentence_transformers import SentenceTransformer

# High-accuracy model — 768 dimensions
# Downloads once (~420MB), then cached locally
_model = SentenceTransformer("all-mpnet-base-v2")


def embed(text: str) -> list[float]:
    """
    Convert text to a vector embedding.
    Input should be title + summary combined for best similarity results.
    Returns a list of 384 floats.
    """
    vector = _model.encode(text, normalize_embeddings=True)
    return vector.tolist()
