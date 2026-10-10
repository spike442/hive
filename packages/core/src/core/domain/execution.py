from pydantic import BaseModel, Field


class RetrievedContext(BaseModel):
    """One knowledge chunk selected for an agent run."""

    content: str
    source: str
    score: float


class PullRequest(BaseModel):
    """Repository and revision identity shared by Hive and PR Review."""

    owner: str
    repository: str
    number: int
    base_sha: str
    head_sha: str
    clone_url: str
    html_url: str = ""
    updated_at: str = ""
    title: str = ""
    author: str = ""
    head_ref: str = ""
    labels: list[str] = Field(default_factory=list)
    mergeable: bool = False
