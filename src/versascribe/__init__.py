"""VersaScribe — local meeting capture, transcription, and analysis."""

__version__ = "0.1.0"


class VersaScribeError(Exception):
    """Base exception for all VersaScribe errors."""


class DeviceNotFoundError(VersaScribeError):
    pass


class FFmpegNotFoundError(VersaScribeError):
    pass


class ExtractionError(VersaScribeError):
    pass


class ClaudeNotConfiguredError(VersaScribeError):
    pass


class TranscriptNotFoundError(VersaScribeError):
    pass
