from typing import Optional, List
import logging

from sqlalchemy import select, and_

from app.database.models.medicine import Medicine, MedicineType, MedicineCategory
from app.repositoryes.template import TemplateRepository
from app.utils.verified_medicines import is_medicine_verified
from app.utils.flags import Flags

log = logging.getLogger(__name__)


class MedicineRepository(TemplateRepository):
    """Репозиторий для работы со справочником лекарств"""

    async def get_all(
            self,
            name: Optional[str] = None,
            medicine_type: Optional[MedicineType] = None,
            category: Optional[MedicineCategory] = None,
            dosage: Optional[str] = None,
            verified: Optional[bool] = None
        ) -> List[Medicine]:
        """Получить все лекарства с фильтрами"""
        query = select(Medicine)
        filters = []

        if name is not None:
            filters.append(Medicine.name.ilike(f"%{name}%"))
        if medicine_type is not None:
            filters.append(Medicine.medicine_type == medicine_type)
        if category is not None:
            filters.append(Medicine.category == category)
        if dosage is not None:
            filters.append(Medicine.dosage == dosage)

        # Фильтрация по флагам: если verified=True, возвращаем только те, у которых установлен бит VERIFIED
        if verified is not None:
            if verified:
                filters.append(Medicine.flags.op('&')(Flags.VERIFIED) != 0)
            else:
                filters.append(Medicine.flags.op('&')(Flags.VERIFIED) == 0)

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(Medicine.name)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get(self, medicine_id: int) -> Optional[Medicine]:
        """Получить лекарство по ID"""
        return await self.db.get(Medicine, medicine_id)

    async def search(self, search_term: str) -> List[Medicine]:
        """Поиск лекарств по названию"""
        return await self.get_all(name=search_term)

    async def get_by_category(self, category: MedicineCategory) -> List[Medicine]:
        """Получить лекарства по категории"""
        return await self.get_all(category=category)

    async def get_by_type(self, medicine_type: MedicineType) -> List[Medicine]:
        """Получить лекарства по типу"""
        return await self.get_all(medicine_type=medicine_type)

    async def create(
            self,
            name: str,
            medicine_type: MedicineType,
            category: MedicineCategory,
            dosage: Optional[str] = None,
            notes: Optional[str] = None,
            flags: Optional[int] = None
    ) -> Medicine:
        """Создать новое лекарство"""
        # Если флаги переданы явно — используем их, иначе решаем в репозитории (на случай внешнего вызова)
        if flags is None:
            is_verified = is_medicine_verified(name)
            flags_value = Flags.VERIFIED if is_verified else 0
        else:
            flags_value = int(flags)

        new_medicine = Medicine(
            name=name,
            medicine_type=medicine_type,
            category=category,
            dosage=dosage,
            notes=notes,
            flags=flags_value
        )

        self.db.add(new_medicine)
        await self.db.commit()
        await self.db.refresh(new_medicine)

        return new_medicine

    async def update(
            self,
            medicine_id: int,
            name: Optional[str] = None,
            medicine_type: Optional[MedicineType] = None,
            category: Optional[MedicineCategory] = None,
            dosage: Optional[str] = None,
            notes: Optional[str] = None,
            flags: Optional[int] = None
        ) -> Optional[Medicine]:
        """Обновить лекарство"""
        medicine = await self.get(medicine_id)
        if not medicine:
            return None

        if name is not None:
            medicine.name = name

        # Если flags переданы явно, устанавливаем их (бизнес-логика по вычислению флагов
        # должна происходить на уровне хэндлера)
        if flags is not None:
            try:
                medicine.flags = int(flags)
            except Exception:
                pass
        if medicine_type is not None:
            medicine.medicine_type = medicine_type
        if category is not None:
            medicine.category = category
        if dosage is not None:
            medicine.dosage = dosage
        if notes is not None:
            medicine.notes = notes

        await self.db.commit()
        await self.db.refresh(medicine)

        return medicine

    async def delete(self, medicine_id: int) -> bool:
        """Удалить лекарство"""
        medicine = await self.get(medicine_id)
        if not medicine:
            return False

        await self.db.delete(medicine)
        await self.db.commit()

        return True

    async def get_or_create(
            self,
            name: str,
            medicine_type: MedicineType,
            category: MedicineCategory,
            dosage: Optional[str] = None,
            flags: Optional[int] = None
    ) -> Medicine:
        """Получить существующее или создать новое лекарство"""
        query = select(Medicine).where(
            Medicine.name == name,
            Medicine.medicine_type == medicine_type,
            Medicine.dosage == dosage
        )
        result = await self.db.execute(query)
        medicine = result.scalar_one_or_none()

        if medicine:
            return medicine

        return await self.create(
            name=name,
            medicine_type=medicine_type,
            category=category,
            dosage=dosage,
            flags=flags
        )