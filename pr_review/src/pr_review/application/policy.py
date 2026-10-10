from dataclasses import dataclass

from pr_review.domain.review import ReviewDecision, ReviewResult


@dataclass(frozen=True)
class MergePolicy:
    checks_passed: bool
    mergeable: bool
    merge_enabled: bool
    allowed_risk_levels: frozenset[str]
    allowed_confidence_levels: frozenset[str]


def decide_merge(
    review: ReviewResult,
    policy: MergePolicy,
) -> ReviewDecision:
    """Apply deterministic merge rules after the review is validated."""
    if not policy.merge_enabled:
        return ReviewDecision(merge=False, reason="automatic merging is disabled")
    if not policy.checks_passed:
        return ReviewDecision(merge=False, reason="one or more validation checks failed")
    if not policy.mergeable:
        return ReviewDecision(merge=False, reason="pull request is not mergeable")
    if review.risk.value not in policy.allowed_risk_levels:
        return ReviewDecision(merge=False, reason=f"risk level is {review.risk.value}")
    if review.confidence.value not in policy.allowed_confidence_levels:
        return ReviewDecision(merge=False, reason=f"confidence level is {review.confidence.value}")
    return ReviewDecision(merge=True, reason="validation passed and policy allows merge")
