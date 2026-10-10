"""Domain-specific orchestration owned by Hive."""

from core.domain import AgentDomain

from hive.domains.contracts import DomainRuntime


def agents(settings, database, github, rag, temporal) -> dict[AgentDomain, DomainRuntime]:
    """Import and initialize only the domains configured for this process."""
    runtimes: dict[AgentDomain, DomainRuntime] = {}
    runtime: DomainRuntime
    for config in settings.agents:
        match config.domain:
            case AgentDomain.SRE:
                from hive.domains.sre.runtime import SreRuntime

                runtime = SreRuntime.load(
                    config=config,
                    settings=settings,
                    database=database,
                    github=github,
                    temporal=temporal,
                    rag=rag,
                )
            case AgentDomain.PULL_REQUEST_REVIEW:
                from hive.domains.pr_review.runtime import PrReviewRuntime

                runtime = PrReviewRuntime.load(
                    config=config,
                    settings=settings,
                    database=database,
                    github=github,
                    temporal=temporal,
                    rag=rag,
                )
            case _:
                raise ValueError(f"unsupported agent domain: {config.domain}")
        runtimes[runtime.config.domain] = runtime
    return runtimes


__all__ = ["DomainRuntime", "agents"]
