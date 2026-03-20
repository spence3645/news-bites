from sentence_transformers import SentenceTransformer

# High-accuracy model — 768 dimensions
# Downloads once (~420MB), then cached locally
_model = SentenceTransformer("all-mpnet-base-v2")


def embed(text: str) -> list[float]:
    vector = _model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Encode a list of texts in one batched call — much faster than calling embed() one at a time."""
    vectors = _model.encode(texts, normalize_embeddings=True, batch_size=64, show_progress_bar=False)
    return [v.tolist() for v in vectors]
