import uuid
from typing import Optional
import logging

from sqlalchemy import select

from uuid import UUID
from app.database.models.users import User
from app.repositoryes.template import TemplateRepository

log = logging.getLogger(__name__)

class UserRepository(TemplateRepository):
    async def get_all(self):
        data = select(User)
        users = await self.db.execute(data)
        return users.scalars().all()

    async def get(self, user_id: int):
        return await self.db.get(User, user_id)

    async def create(self,telegram_id, username: Optional[str] = None) -> User:
        new_user = User(id=telegram_id, username=username)
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        return new_user

    async def delete(self, user_id: int) -> bool:
        await self.db.delete(await self.get(user_id))
        await self.db.commit()
        return True