"""SDK exception hierarchy.

All exceptions raised by the public SDK surface are subclasses of
:class:`SdkError`.  Catch that if you want a single handler for all SDK
errors; catch specific subclasses for finer-grained handling.
"""

from __future__ import annotations


class SdkError(Exception):
    """Base class for all JiuwenSwarm SDK exceptions."""


class RuntimeNotAvailableError(SdkError):
    """The ``openjiuwen`` runtime package is not installed.

    Required for in-process mode (``Agent.create``).  Install it with::

        pip install openjiuwen
    """


class ConnectionError(SdkError):
    """Cannot connect to a JiuwenSwarm server (remote / WebSocket mode)."""


class AuthError(SdkError):
    """Authentication or authorisation error from the server."""


class SessionError(SdkError):
    """Session not found, expired, or in an invalid state."""


class AgentError(SdkError):
    """Agent creation, configuration, or invocation error."""


class ToolError(SdkError):
    """Tool registration, configuration, or invocation error."""


class CheckpointError(SdkError):
    """Checkpoint save or restore error."""


class TeamError(SdkError):
    """Team creation or coordination error."""


class StreamError(SdkError):
    """Error while consuming a streaming response."""


class TimeoutError(SdkError):
    """Agent or network operation timed out."""


class ServerError(SdkError):
    """The JiuwenSwarm server returned an error response.

    Attributes:
        status_code: HTTP status code (if applicable).
        message:     Error message from the server.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
