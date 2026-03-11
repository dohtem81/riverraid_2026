from fastapi import APIRouter, HTTPException, status

from riverraid.application.use_cases import LoginWithConfiguredCredentials
from riverraid.interfaces.http.schemas import ErrorResponse, LoginRequest, LoginResponse


def build_auth_router(login_use_case: LoginWithConfiguredCredentials) -> APIRouter:
    router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

    @router.post("/login", response_model=LoginResponse)
    def login(body: LoginRequest) -> LoginResponse:
        result = login_use_case.execute(username=body.username, password=body.password)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "INVALID_CREDENTIALS",
                        "message": "Invalid username or password",
                    }
                },
            )

        return LoginResponse(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
            player_id=result.player_id,
        )

    @router.post("/register", responses={501: {"model": ErrorResponse}})
    def register() -> None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "error": {
                    "code": "NOT_IMPLEMENTED_PHASE0",
                    "message": "This endpoint is not available in Phase 0",
                }
            },
        )

    @router.post("/refresh", responses={501: {"model": ErrorResponse}})
    def refresh() -> None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "error": {
                    "code": "NOT_IMPLEMENTED_PHASE0",
                    "message": "This endpoint is not available in Phase 0",
                }
            },
        )

    @router.post("/logout", responses={501: {"model": ErrorResponse}})
    def logout() -> None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "error": {
                    "code": "NOT_IMPLEMENTED_PHASE0",
                    "message": "This endpoint is not available in Phase 0",
                }
            },
        )

    return router
