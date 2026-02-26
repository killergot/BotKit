from datetime import datetime

from sqlalchemy import BigInteger, Integer, Text, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.psql import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    interval_days: Mapped[int] = mapped_column(Integer)
    is_one_time: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    next_fire_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=sa_text("CURRENT_TIMESTAMP")
    )

    user = relationship("User", back_populates="reminders")

    def __repr__(self):
        return f"<Reminder id={self.id} user_id={self.user_id}>"
