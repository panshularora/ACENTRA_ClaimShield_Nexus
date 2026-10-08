"""Domain errors mapped to RFC 9457 problem JSON at the API boundary."""

from __future__ import annotations


class ClaimShieldError(Exception):
    status: int = 500
    type_uri: str = "about:blank"
    title: str = "Internal error"

    def __init__(self, detail: str, *, case_id: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.case_id = case_id

    def to_problem(self) -> dict[str, str | int | None]:
        body: dict[str, str | int | None] = {
            "type": self.type_uri,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
        }
        if self.case_id:
            body["case_id"] = self.case_id
        return body


class Unauthorized(ClaimShieldError):
    status = 401
    title = "Unauthorized"
    type_uri = "https://claimshield.local/problems/unauthorized"


class Forbidden(ClaimShieldError):
    status = 403
    title = "Forbidden"
    type_uri = "https://claimshield.local/problems/forbidden"


class NotFound(ClaimShieldError):
    status = 404
    title = "Not found"
    type_uri = "https://claimshield.local/problems/not-found"


class ValidationFailed(ClaimShieldError):
    status = 422
    title = "Validation failed"
    type_uri = "https://claimshield.local/problems/validation"


class Conflict(ClaimShieldError):
    status = 409
    title = "Conflict"
    type_uri = "https://claimshield.local/problems/conflict"


class RateLimited(ClaimShieldError):
    status = 429
    title = "Too many requests"
    type_uri = "https://claimshield.local/problems/rate-limited"
