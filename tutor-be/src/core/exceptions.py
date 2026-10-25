from fastapi import HTTPException, status


class AppHTTPException(HTTPException):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            status_code=type(self).status_code,
            detail=detail if detail is not None else type(self).detail,
        )


class BadRequestError(AppHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Bad request"


class NotFoundError(AppHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Not found"


class ConversationNotFound(AppHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Conversation not found"


class MemoryNotFound(AppHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Memory not found"


class TopicNotFound(AppHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Topic not found"


class ConflictError(AppHTTPException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Conflict"


class UnprocessableError(AppHTTPException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = "Unprocessable entity"


class TutorUnavailable(AppHTTPException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = "Tutor is not configured — set AZURE_LLM_* in .env"
