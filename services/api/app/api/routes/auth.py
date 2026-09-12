from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.api.schemas.auth import RegisterRequest, UserResponse
from services.api.app.db.session import get_db
from services.api.app.services.auth import register_user


router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        user = await register_user(
            db=db,
            email=str(request.email),
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return UserResponse.model_validate(user)
