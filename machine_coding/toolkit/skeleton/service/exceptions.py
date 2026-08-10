"""File 2 of 6. Thirty seconds. Write it first -- it's free credit."""


class ServiceError(Exception):
    """Base for everything this package raises.

    One base class means callers can `except ServiceError` and catch all of
    yours without swallowing genuine bugs like TypeError.
    """


class EntityNotFoundError(ServiceError):
    def __init__(self, entity_id: str):
        self.entity_id = entity_id
        super().__init__(f"entity not found: {entity_id}")


class DuplicateEntityError(ServiceError):
    def __init__(self, entity_id: str):
        self.entity_id = entity_id
        super().__init__(f"entity already exists: {entity_id}")


class InvalidStateError(ServiceError):
    """Raised when an operation isn't legal in the current state."""


class CapacityExceededError(ServiceError):
    """Raised when a bounded resource is full."""
