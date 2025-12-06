from typing import Optional, List
from datetime import date, timedelta
from decimal import Decimal
import logging

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.database.models.medicine import MedicineItem, Medicine
from app.repositoryes.template import TemplateRepository

log = logging.getLogger(__name__)


class MedicineItemRepository(TemplateRepository):
    """Репозиторий для работы с экземплярами лекарств в аптечке"""

    async def get_all(
            self,
            medicine_kit_id: Optional[int] = None,
            medicine_id: Optional[int] = None,
            location: Optional[str] = None,
            is_expired: Optional[bool] = None,
            is_expiring_soon: Optional[bool] = None,
            expiring_days: int = 30
    ) -> List[MedicineItem]:
        """Получить все экземпляры лекарств с фильтрами"""
        query = select(MedicineItem)
        filters = []

        if medicine_kit_id is not None:
            filters.append(MedicineItem.medicine_kit_id == medicine_kit_id)
        if medicine_id is not None:
            filters.append(MedicineItem.medicine_id == medicine_id)
        if location is not None:
            filters.append(MedicineItem.location.ilike(f"%{location}%"))

        # Фильтр для просроченных
        if is_expired is not None:
            today = date.today()
            if is_expired:
                filters.append(MedicineItem.expiry_date < today)
            else:
                filters.append(
                    and_(
                        MedicineItem.expiry_date.isnot(None),
                        MedicineItem.expiry_date >= today
                    )
                )

        # Фильтр для истекающих скоро
        if is_expiring_soon is not None and is_expiring_soon:
            expiry_threshold = date.today() + timedelta(days=expiring_days)
            filters.append(
                and_(
                    MedicineItem.expiry_date.isnot(None),
                    MedicineItem.expiry_date <= expiry_threshold,
                    MedicineItem.expiry_date >= date.today()
                )
            )

        if filters:
            query = query.where(and_(*filters))

        query = query.options(
            selectinload(MedicineItem.medicine),
            selectinload(MedicineItem.medicine_kit)
        ).order_by(MedicineItem.medicine_id)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get(self, item_id: int) -> Optional[MedicineItem]:
        """Получить экземпляр по ID"""
        query = select(MedicineItem).where(MedicineItem.id == item_id).options(
            selectinload(MedicineItem.medicine),
            selectinload(MedicineItem.medicine_kit)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_kit(self, kit_id: int) -> List[MedicineItem]:
        """Получить все лекарства из аптечки"""
        return await self.get_all(medicine_kit_id=kit_id)

    async def get_expiring_soon(
            self,
            kit_id: int,
            days: int = 30
    ) -> List[MedicineItem]:
        """Получить лекарства с истекающим сроком годности"""
        return await self.get_all(
            medicine_kit_id=kit_id,
            is_expiring_soon=True,
            expiring_days=days
        )

    async def get_expired(self, kit_id: int) -> List[MedicineItem]:
        """Получить просроченные лекарства"""
        return await self.get_all(
            medicine_kit_id=kit_id,
            is_expired=True
        )

    async def get_low_stock(
            self,
            kit_id: int,
            threshold: Decimal = Decimal("5")
    ) -> List[MedicineItem]:
        """Получить лекарства с низким остатком"""
        query = (
            select(MedicineItem)
            .where(
                and_(
                    MedicineItem.medicine_kit_id == kit_id,
                    MedicineItem.quantity <= threshold
                )
            )
            .options(selectinload(MedicineItem.medicine))
            .order_by(MedicineItem.quantity)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create(
            self,
            medicine_kit_id: int,
            medicine_id: int,
            quantity: Decimal = Decimal("0"),
            unit: str = "шт",
            expiry_date: Optional[date] = None,
            location: Optional[str] = None,
            notes: Optional[str] = None
    ) -> MedicineItem:
        """Добавить лекарство в аптечку"""
        new_item = MedicineItem(
            medicine_kit_id=medicine_kit_id,
            medicine_id=medicine_id,
            quantity=quantity,
            unit=unit,
            expiry_date=expiry_date,
            location=location,
            notes=notes
        )

        self.db.add(new_item)
        await self.db.commit()
        await self.db.refresh(new_item, ["medicine", "medicine_kit"])

        return new_item

    async def update(
            self,
            item_id: int,
            quantity: Optional[Decimal] = None,
            unit: Optional[str] = None,
            expiry_date: Optional[date] = None,
            location: Optional[str] = None,
            notes: Optional[str] = None
    ) -> Optional[MedicineItem]:
        """Обновить экземпляр лекарства"""
        item = await self.get(item_id)
        if not item:
            return None

        if quantity is not None:
            item.quantity = quantity
        if unit is not None:
            item.unit = unit
        if expiry_date is not None:
            item.expiry_date = expiry_date
        if location is not None:
            item.location = location
        if notes is not None:
            item.notes = notes

        await self.db.commit()
        await self.db.refresh(item)

        return item

    async def update_quantity(
            self,
            item_id: int,
            quantity_change: Decimal
    ) -> Optional[MedicineItem]:
        """Изменить количество (добавить/убавить)"""
        item = await self.get(item_id)
        if not item:
            return None

        item.quantity += quantity_change

        # Не даем уйти в минус
        if item.quantity < 0:
            item.quantity = Decimal("0")

        await self.db.commit()
        await self.db.refresh(item)

        return item

    async def delete(self, item_id: int) -> bool:
        """Удалить экземпляр лекарства"""
        item = await self.get(item_id)
        if not item:
            return False

        await self.db.delete(item)
        await self.db.commit()

        return True

    async def search_in_kit(
            self,
            kit_id: int,
            search_term: str
    ) -> List[MedicineItem]:
        """Поиск лекарств в аптечке"""
        query = (
            select(MedicineItem)
            .join(Medicine)
            .where(
                and_(
                    MedicineItem.medicine_kit_id == kit_id,
                    Medicine.name.ilike(f"%{search_term}%")
                )
            )
            .options(selectinload(MedicineItem.medicine))
        )
        result = await self.db.execute(query)
        return result.scalars().all()