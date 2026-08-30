from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db

bearer_scheme = HTTPBearer()


class CurrentUser:
    def __init__(self, user_id: UUID, company_id: UUID, permissions: list[str]):
        self.user_id = user_id
        self.company_id = company_id
        self.permissions = permissions

    def require(self, permission: str) -> None:
        if permission not in self.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": f"Permission required: {permission}"},
            )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> CurrentUser:
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        user_id=UUID(payload["sub"]),
        company_id=UUID(payload["company_id"]),
        permissions=payload.get("permissions", []),
    )


DBSession = Annotated[AsyncSession, Depends(get_db)]
AuthUser = Annotated[CurrentUser, Depends(get_current_user)]
