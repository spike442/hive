from core.observability.audit import AuditAction


class ReviewExecutionError(RuntimeError):
    def __init__(self, cause: Exception, actions: list[AuditAction]) -> None:
        super().__init__(str(cause))
        self.actions = actions
