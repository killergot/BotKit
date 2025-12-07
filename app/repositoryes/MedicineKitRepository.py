from typing import Optional, List
import logging

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.database.models.medicine import MedicineKit
from app.database.models.users import User
from app.repositoryes.template import TemplateRepository

log = logging.getLogger(__name__)


class MedicineKitRepository(TemplateRepository):
    """Репозиторий для работы с аптечками"""

    async def get_all(
            self,
            name: Optional[str] = None,
            user_id: Optional[int] = None,
            deleted: Optional[bool] = None
    ) -> List[MedicineKit]:
        """Получить все аптечки с фильтрами"""
        query = select(MedicineKit)
        filters = []

        if name is not None:
            filters.append(MedicineKit.name.ilike(f"%{name}%"))

        if user_id is not None:
            query = query.join(MedicineKit.users)
            filters.append(User.id == user_id)
        
        if deleted is not None:
            filters.append(MedicineKit.deleted == deleted)

        if filters:
            query = query.where(and_(*filters))
        
        

        query = query.options(
            selectinload(MedicineKit.users),
            selectinload(MedicineKit.items)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get(self, kit_id: int) -> Optional[MedicineKit]:
        """Получить аптечку по ID"""
        query = select(MedicineKit).where(MedicineKit.id == kit_id).options(
            selectinload(MedicineKit.users),
            selectinload(MedicineKit.items)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: int, deleted: Optional[bool] = None) -> List[MedicineKit]:
        """Получить все аптечки пользователя (можно фильтровать по удалённым)"""
        return await self.get_all(user_id=user_id, deleted=deleted)

    async def create(
            self,
            name: str = "Моя аптечка",
            description: Optional[str] = None,
            user_ids: Optional[List[int]] = None
    ) -> MedicineKit:
        """Создать новую аптечку"""
        new_kit = MedicineKit(name=name, description=description)

        # Добавляем пользователей, если указаны
        if user_ids:
            users = await self.db.execute(select(User).where(User.id.in_(user_ids)))
            new_kit.users = list(users.scalars().all())

        self.db.add(new_kit)
        await self.db.commit()
        await self.db.refresh(new_kit, ["users", "items"])

        return new_kit

    async def update(
            self,
            kit_id: int,
            name: Optional[str] = None,
            description: Optional[str] = None,
            deleted: Optional[bool] = None,
    ) -> Optional[MedicineKit]:
        """Обновить аптечку"""
        kit = await self.get(kit_id)
        if not kit:
            return None

        if name is not None:
            kit.name = name
        if description is not None:
            kit.description = description
        if deleted is not None:
            kit.deleted = deleted

        await self.db.commit()
        await self.db.refresh(kit)

        return kit

    async def add_user(self, kit_id: int, user_id: int) -> bool:
        """Добавить пользователя в аптечку"""
        kit = await self.get(kit_id)
        user = await self.db.get(User, user_id)

        if not kit or not user:
            return False

        if user not in kit.users:
            kit.users.append(user)
            await self.db.commit()

        return True

    async def remove_user(self, kit_id: int, user_id: int) -> bool:
        """Удалить пользователя из аптечки"""
        kit = await self.get(kit_id)
        user = await self.db.get(User, user_id)

        if not kit or not user:
            return False

        if user in kit.users:
            kit.users.remove(user)
            await self.db.commit()

        return True

    async def delete(self, kit_id: int) -> bool:
        """Удалить аптечку"""
        kit = await self.get(kit_id)
        if not kit:
            return False

        await self.db.delete(kit)
        await self.db.commit()

        return True