"""用户服务。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import AppError
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User


def get_user_permission_codes(user: User) -> list[str]:
    if user.is_superuser:
        return ["*"]
    codes: set[str] = set()
    for role in user.roles:
        if role.status == 1:
            codes.update(p.code for p in role.permissions)
    return sorted(codes)


def get_user_role_codes(user: User) -> list[str]:
    return [r.code for r in user.roles]


async def list_users(
    db: AsyncSession, page: int, page_size: int, keyword: str | None = None
) -> tuple[int, list[User]]:
    stmt = select(User)
    if keyword:
        stmt = stmt.where(User.username.contains(keyword) | User.nickname.contains(keyword))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        (
            await db.execute(
                stmt.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return total, list(rows)


async def get_user(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise AppError(404, "用户不存在")
    return user


async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    nickname: str = "",
    email: str = "",
    phone: str = "",
    status: int = 1,
    role_ids: list[int] | None = None,
) -> User:
    exists = (
        await db.execute(select(User.id).where(User.username == username))
    ).scalar_one_or_none()
    if exists:
        raise AppError(400, "用户名已存在")

    user = User(
        username=username,
        password_hash=hash_password(password),
        nickname=nickname,
        email=email,
        phone=phone,
        status=status,
    )
    if role_ids:
        roles = (await db.execute(select(Role).where(Role.id.in_(role_ids)))).scalars().all()
        user.roles = list(roles)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession, user_id: int, data: dict, role_ids: list[int] | None = None
) -> User:
    user = await get_user(db, user_id)
    for key, value in data.items():
        if value is None:
            continue
        if key == "password":
            user.password_hash = hash_password(value)
        else:
            setattr(user, key, value)
    if role_ids is not None:
        roles = (await db.execute(select(Role).where(Role.id.in_(role_ids)))).scalars().all()
        user.roles = list(roles)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> None:
    user = await get_user(db, user_id)
    if user.is_superuser:
        raise AppError(400, "超管账号不可删除")
    await db.delete(user)
    await db.commit()
