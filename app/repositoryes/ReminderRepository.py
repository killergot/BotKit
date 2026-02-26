from datetime import datetime, timedelta
from typing import Optional, List
import logging

from sqlalchemy import select

from app.database.models.reminder import Reminder
from app.repositoryes.template import TemplateRepository

log = logging.getLogger(__name__)


class ReminderRepository(TemplateRepository):

    async def get_by_user(self, user_id: int) -> List[Reminder]:
        query = select(Reminder).where(
            Reminder.user_id == user_id,
            Reminder.is_active == True,
        ).order_by(Reminder.next_fire_at)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get(self, reminder_id: int) -> Optional[Reminder]:
        return await self.db.get(Reminder, reminder_id)

    async def get_due_reminders(self, now: datetime) -> List[Reminder]:
        query = select(Reminder).where(
            Reminder.next_fire_at <= now,
            Reminder.is_active == True,
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create(
        self,
        user_id: int,
        text: str,
        interval_days: int,
        is_one_time: bool = False,
    ) -> Reminder:
        now = datetime.utcnow()
        next_fire = (now + timedelta(days=interval_days)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )

        reminder = Reminder(
            user_id=user_id,
            text=text,
            interval_days=interval_days,
            is_one_time=is_one_time,
            next_fire_at=next_fire,
        )
        self.db.add(reminder)
        await self.db.commit()
        await self.db.refresh(reminder)
        return reminder

    async def update(
        self,
        reminder_id: int,
        text: Optional[str] = None,
        interval_days: Optional[int] = None,
    ) -> Optional[Reminder]:
        reminder = await self.get(reminder_id)
        if not reminder:
            return None

        if text is not None:
            reminder.text = text
        if interval_days is not None:
            reminder.interval_days = interval_days
            reminder.next_fire_at = (
                datetime.utcnow() + timedelta(days=interval_days)
            ).replace(hour=9, minute=0, second=0, microsecond=0)

        await self.db.commit()
        await self.db.refresh(reminder)
        return reminder

    async def delete(self, reminder_id: int) -> bool:
        reminder = await self.get(reminder_id)
        if not reminder:
            return False
        await self.db.delete(reminder)
        await self.db.commit()
        return True

    async def deactivate(self, reminder_id: int) -> bool:
        reminder = await self.get(reminder_id)
        if not reminder:
            return False
        reminder.is_active = False
        await self.db.commit()
        return True

    async def advance_next_fire(self, reminder_id: int) -> Optional[Reminder]:
        reminder = await self.get(reminder_id)
        if not reminder:
            return None

        now = datetime.utcnow()
        next_fire = reminder.next_fire_at

        while next_fire <= now:
            next_fire += timedelta(days=reminder.interval_days)

        next_fire = next_fire.replace(hour=9, minute=0, second=0, microsecond=0)
        reminder.next_fire_at = next_fire

        await self.db.commit()
        await self.db.refresh(reminder)
        return reminder
