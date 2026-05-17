from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    BackgroundTasks,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.database.models import User
from src.schemas import UserCreate, UserResponse, Token
from src.services.auth import (
    Hash,
    create_access_token,
    get_current_user,
    get_email_from_token,
    limiter,
)
from src.services.email import send_email
from fastapi import UploadFile, File
from src.conf.config import settings
from src.services.upload_file import UploadFileService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з таким email вже існує",
        )

    stmt = select(User).where(User.username == user_data.username)
    result = await db.execute(stmt)
    existing_username = result.scalar_one_or_none()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з таким username вже існує",
        )

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=Hash().get_password_hash(user_data.password),
        avatar=None,
        confirmed=False,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    background_tasks.add_task(
        send_email,
        new_user.email,
        new_user.username,
        str(request.base_url),
    )

    return new_user


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.username == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильний логін або пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not Hash().verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильний логін або пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Електронна адреса не підтверджена",
        )

    access_token = await create_access_token(data={"sub": user.username})

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/confirmed_email/{token}")
async def confirmed_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    email = await get_email_from_token(token)

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification error",
        )

    if user.confirmed:
        return {"message": "Ваша електронна пошта вже підтверджена"}

    user.confirmed = True
    await db.commit()

    return {"message": "Електронну пошту підтверджено"}


@router.get("/me", response_model=UserResponse)
@limiter.limit("5/minute")
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.patch("/avatar", response_model=UserResponse)
async def update_avatar(
    file: UploadFile = File(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    avatar_url = UploadFileService().upload_file(
        file,
        current_user.username
    )

    current_user.avatar = avatar_url

    await db.commit()
    await db.refresh(current_user)

    return current_user