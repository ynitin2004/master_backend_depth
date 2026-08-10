"""Rename this package to your domain (scheduler/, broker/, parking/, ...)."""

from .core import Service
from .exceptions import (
    CapacityExceededError,
    DuplicateEntityError,
    EntityNotFoundError,
    InvalidStateError,
    ServiceError,
)
from .models import Entity, Priority, Result, Status

__all__ = [
    "Service",
    "Entity",
    "Priority",
    "Result",
    "Status",
    "ServiceError",
    "EntityNotFoundError",
    "DuplicateEntityError",
    "InvalidStateError",
    "CapacityExceededError",
]
