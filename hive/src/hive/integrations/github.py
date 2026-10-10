import httpx
from core.integrations.github import GitHubAppAuth, GitHubAppConfig

from hive.infrastructure.config import RepositoryConfig, Settings


class GitHubGateway:
    def __init__(self, settings: Settings):
        self.client = httpx.Client(
            base_url=settings.github.api_url.rstrip("/"),
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )
        self.auth = GitHubAppAuth(
            self.client,
            GitHubAppConfig(
                api_url=settings.github.api_url,
                app_id=settings.github_app_id,
                installation_id=settings.github_installation_id,
                private_key=settings.github_private_key,
            ),
        )

    def open_pull_requests(self, repository: RepositoryConfig) -> list[dict]:
        response = self.client.get(
            f"/repos/{repository.owner}/{repository.name}/pulls",
            headers=self.auth.headers(),
            params={"state": "open", "sort": "updated", "direction": "desc", "per_page": 100},
        )
        response.raise_for_status()
        pull_requests = []
        for item in response.json():
            pull_request = self._review_input(repository, item)
            pull_request["mergeable"] = self.is_mergeable(pull_request)
            pull_requests.append(pull_request)
        return pull_requests

    def pull_request(self, repository: RepositoryConfig, number: int) -> dict:
        response = self.client.get(
            f"/repos/{repository.owner}/{repository.name}/pulls/{number}",
            headers=self.auth.headers(),
        )
        response.raise_for_status()
        item = response.json()
        if item["state"] != "open":
            raise ValueError("Only open pull requests can be retried")
        return self._review_input(repository, item) | {
            "mergeable": item.get("mergeable") is True and item.get("mergeable_state") == "clean"
        }

    @staticmethod
    def _review_input(repository: RepositoryConfig, item: dict) -> dict:
        return {
            "owner": repository.owner,
            "repository": repository.name,
            "number": item["number"],
            "base_sha": item["base"]["sha"],
            "head_sha": item["head"]["sha"],
            "clone_url": repository.clone_url,
            "html_url": item.get("html_url", ""),
            "updated_at": item.get("updated_at", ""),
            "title": item.get("title", ""),
            "author": (item.get("user") or {}).get("login", ""),
            "head_ref": (item.get("head") or {}).get("ref", ""),
            "labels": [label.get("name", "") for label in item.get("labels", [])],
            "repository_config": repository.model_dump(mode="json"),
        }

    def create_pull_request(
        self,
        repository: RepositoryConfig,
        base_branch: str,
        head_branch: str,
        title: str,
        body: str,
        labels: list[str],
    ) -> str:
        existing = self.find_pull_request(repository, base_branch, head_branch)
        if existing:
            self._add_labels(repository, existing["number"], labels)
            return existing["html_url"]
        response = self.client.post(
            f"/repos/{repository.owner}/{repository.name}/pulls",
            headers=self.auth.headers(),
            json={
                "title": title,
                "head": head_branch,
                "base": base_branch,
                "body": body,
            },
        )
        if response.status_code == 422:
            pull_request = self.find_pull_request(repository, base_branch, head_branch)
            if pull_request is None:
                response.raise_for_status()
        else:
            response.raise_for_status()
            pull_request = response.json()
        self._add_labels(repository, pull_request["number"], labels)
        return pull_request["html_url"]

    def find_pull_request(self, repository: RepositoryConfig, base_branch: str, head_branch: str) -> dict | None:
        response = self.client.get(
            f"/repos/{repository.owner}/{repository.name}/pulls",
            headers=self.auth.headers(),
            params={"state": "all", "base": base_branch, "head": f"{repository.owner}:{head_branch}"},
        )
        response.raise_for_status()
        return next(iter(response.json()), None)

    def merged_commit(self, pull_request: dict) -> str | None:
        response = self.client.get(
            f"/repos/{pull_request['owner']}/{pull_request['repository']}/pulls/{pull_request['number']}",
            headers=self.auth.headers(),
        )
        response.raise_for_status()
        result = response.json()
        if result.get("merged") and result["head"]["sha"] == pull_request["head_sha"]:
            return result["merge_commit_sha"]
        return None

    def _add_labels(self, repository: RepositoryConfig, number: int, labels: list[str]) -> None:
        for label in labels:
            response = self.client.post(
                f"/repos/{repository.owner}/{repository.name}/labels",
                headers=self.auth.headers(),
                json={"name": label, "color": "1d76db", "description": f"Hive {label} classification"},
            )
            if response.status_code not in {201, 422}:
                response.raise_for_status()
        response = self.client.post(
            f"/repos/{repository.owner}/{repository.name}/issues/{number}/labels",
            headers=self.auth.headers(),
            json={"labels": labels},
        )
        response.raise_for_status()

    def is_mergeable(self, pull_request: dict) -> bool:
        response = self.client.get(
            f"/repos/{pull_request['owner']}/{pull_request['repository']}/pulls/{pull_request['number']}",
            headers=self.auth.headers(),
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("mergeable") is True and payload.get("mergeable_state") == "clean"

    def merge_pull_request(self, pull_request: dict, merge_method: str) -> str:
        response = self.client.put(
            f"/repos/{pull_request['owner']}/{pull_request['repository']}/pulls/{pull_request['number']}/merge",
            headers=self.auth.headers(),
            json={"sha": pull_request["head_sha"], "merge_method": merge_method},
        )
        response.raise_for_status()
        result = response.json()
        if not result.get("merged"):
            raise RuntimeError(result.get("message", "GitHub did not merge the pull request"))
        return str(result.get("sha", ""))

    def close(self) -> None:
        self.client.close()
