from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    player_id: str


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
