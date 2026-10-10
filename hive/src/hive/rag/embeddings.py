from collections.abc import Sequence

from openai import OpenAI


class OpenAIEmbeddings:
    """Create embeddings with one explicit OpenAI model and dimension."""

    def __init__(self, api_key: str, model: str, dimensions: int):
        self.model = model
        self.dimensions = dimensions
        self.client = OpenAI(api_key=api_key)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            model=self.model,
            input=list(texts),
            dimensions=self.dimensions,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]

    def close(self) -> None:
        self.client.close()
