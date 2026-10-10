from enum import StrEnum


class WorkflowType(StrEnum):
    SRE_INCIDENT = "SreIncidentWorkflow"
    PR_REVIEW = "PullRequestReviewWorkflow"
    PR_REVIEW_POLL = "PullRequestReviewPollWorkflow"
    MANUAL_ACTION = "ManualActionWorkflow"


class ActivityName(StrEnum):
    AGENT_IS_ACTIVE = "hive.agent_is_active"
    SRE_QUEUE_REPLAY = "hive.sre_queue_replay"
    SRE_RAG_CONTEXT = "hive.sre_rag_context"
    SRE_MARK_PROCESSING = "hive.sre_mark_processing"
    SRE_COMPLETE = "hive.sre_complete"
    SRE_FAIL = "hive.sre_fail"
    SRE_INVESTIGATE = "sre.investigate"
    PR_DISCOVER = "hive.pr_discover"
    PR_ACKNOWLEDGE = "hive.pr_acknowledge"
    PR_CLAIM = "hive.pr_claim"
    PR_PREPARE = "hive.pr_prepare"
    PR_COMPLETE = "hive.pr_complete"
    PR_FAIL = "hive.pr_fail"
    PR_REVIEW = "pr_review.review"
    MANUAL_ACTION = "hive.manual_action"
