"""One error family. The API turns each into a JSON body with a stable code."""
from __future__ import annotations


class KestrelError(Exception):
    status = 500
    code = "internal_error"

    def __init__(self, message: str, details=None):
        super().__init__(message)
        self.message = message
        self.details = details

    def as_dict(self) -> dict:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


class DataNotFoundError(KestrelError):
    status = 409
    code = "data_not_found"


class DataValidationError(KestrelError):
    status = 422
    code = "data_invalid"


class ModelNotReadyError(KestrelError):
    status = 503
    code = "model_not_ready"


class PipelineBusyError(KestrelError):
    status = 409
    code = "pipeline_busy"


class ExtensionError(KestrelError):
    status = 400
    code = "extension_error"


class NotFoundError(KestrelError):
    status = 404
    code = "not_found"
