"""Application-specific exceptions."""


class ThermoLabError(Exception):
    """Base exception for the application."""


class InvalidConditionError(ThermoLabError, ValueError):
    """Raised when a simulation condition is outside its supported range."""


class DatabaseError(ThermoLabError):
    """Raised when a database operation fails."""
