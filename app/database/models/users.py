from typing import Optional

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Text, TIMESTAMP, DateTime, BigInteger, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database.psql import Base
import uuid
from datetime import datetime
#from database.models.students import Student

# Модель пользователей (users)
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram user_id
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP")
    )

    def __repr__(self):
        return f"<User id={self.id}>"
