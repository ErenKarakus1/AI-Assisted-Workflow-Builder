from app.core.security import create_token, decode_token, hash_password, verify_password
from app.domain.auth.repository import UserRepository
from app.models.user import User
from app.schemas.auth import TokenPair, UserCreate, UserLogin


class DuplicateUserError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def register(self, payload: UserCreate) -> User:
        email = payload.email.lower()
        existing_user = await self.users.get_by_email(email)
        if existing_user:
            raise DuplicateUserError

        user = User(
            email=email,
            full_name=payload.full_name.strip(),
            hashed_password=hash_password(payload.password),
        )
        return await self.users.create(user)

    async def login(self, payload: UserLogin) -> TokenPair:
        user = await self.users.get_by_email(payload.email.lower())
        if not user or not verify_password(payload.password, user.hashed_password):
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError

        return self.create_token_pair(user.id)

    async def refresh(self, refresh_token: str) -> TokenPair:
        user_id = decode_token(refresh_token, "refresh")
        user = await self.users.get_by_id(user_id)
        if not user:
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError

        return self.create_token_pair(user.id)

    def create_token_pair(self, user_id: str) -> TokenPair:
        return TokenPair(
            access_token=create_token(user_id, "access"),
            refresh_token=create_token(user_id, "refresh"),
        )

