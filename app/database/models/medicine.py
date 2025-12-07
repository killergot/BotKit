from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    BigInteger, String, Integer, Text, Date, Numeric,
    ForeignKey, TIMESTAMP, text, Enum, Table, Column, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database.psql import Base


# Enum для типов лекарств
class MedicineType(enum.Enum):
    TABLETS = "таблетки"
    CAPSULES = "капсулы"
    OINTMENT = "мазь"
    CREAM = "крем"
    DROPS = "капли"
    SYRUP = "сироп"
    SPRAY = "спрей"
    SOLUTION = "раствор"
    POWDER = "порошок"
    SUPPOSITORIES = "свечи"
    PATCH = "пластырь"
    OTHER = "другое"


# Enum для категорий
class MedicineCategory(enum.Enum):
    PAINKILLER = "обезболивающее"
    ANTI_INFLAMMATORY = "противовоспалительное"
    ANTIBIOTIC = "антибиотик"
    ANTIVIRAL = "противовирусное"
    ANTIHISTAMINE = "антигистаминное"
    ANTISEPTIC = "антисептик"
    VITAMIN = "витамины/БАД"
    CARDIOVASCULAR = "сердечно-сосудистое"
    DIGESTIVE = "для ЖКТ"
    RESPIRATORY = "для дыхательной системы"
    DERMATOLOGICAL = "дерматологическое"
    NEUROLOGICAL = "неврологическое"
    OTHER = "другое"


user_medicine_kit_association = Table(
    'user_medicine_kits',
    Base.metadata,
    Column('user_id', BigInteger, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('medicine_kit_id', Integer, ForeignKey('medicine_kits.id', ondelete='CASCADE'), primary_key=True)
)

# Модель аптечки
class MedicineKit(Base):
    __tablename__ = "medicine_kits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), default="Моя аптечка")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP")
    )

    users: Mapped[List["User"]] = relationship(
        secondary=user_medicine_kit_association,
        back_populates="medicine_kits"
    )

    items: Mapped[List["MedicineItem"]] = relationship(
        back_populates="medicine_kit", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<MedicineKit id={self.id} name='{self.name}'>"


# Справочник лекарств
class Medicine(Base):
    __tablename__ = "medicines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    medicine_type: Mapped[MedicineType] = mapped_column(
        Enum(MedicineType, native_enum=False), nullable=False
    )
    category: Mapped[MedicineCategory] = mapped_column(
        Enum(MedicineCategory, native_enum=False), nullable=False
    )
    dosage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # "500 мг", "10 мл" и т.д.

    # Дополнительные поля
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_verified: Mapped[bool] = mapped_column(default=False)  # Проверено ли лекарство

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP")
    )

    # Связи
    items: Mapped[List["MedicineItem"]] = relationship(
        back_populates="medicine", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Medicine id={self.id} name='{self.name}'>"


# Конкретный экземпляр лекарства в аптечке
class MedicineItem(Base):
    __tablename__ = "medicine_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    medicine_kit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("medicine_kits.id", ondelete="CASCADE"), nullable=False
    )
    medicine_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False
    )

    # Основные поля экземпляра
    quantity: Mapped[Numeric] = mapped_column(Numeric(10, 2), default=0)  # Остаток
    unit: Mapped[str] = mapped_column(String(20), default="шт")  # шт, мл, г и т.д.
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Дополнительные поля
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP")
    )

    # Связи
    medicine_kit: Mapped["MedicineKit"] = relationship(back_populates="items")
    medicine: Mapped["Medicine"] = relationship(back_populates="items")

    def __repr__(self):
        return f"<MedicineItem id={self.id} medicine_id={self.medicine_id} qty={self.quantity}>"