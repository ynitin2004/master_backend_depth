"""Written at minute 11. Thirty seconds."""


class SchedulerError(Exception):
    """Base for everything this package raises."""


class TaskNotFoundError(SchedulerError):
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"task not found: {task_id}")


class SchedulerShutdownError(SchedulerError):
    """Raised when submitting to a scheduler that is shutting down."""


class TaskNotCancellableError(SchedulerError):
    def __init__(self, task_id: str, status):
        self.task_id = task_id
        self.status = status
        label = getattr(status, "value", status)
        super().__init__(f"cannot cancel {task_id}: already {label}")
