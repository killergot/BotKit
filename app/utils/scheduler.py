import logging
from datetime import datetime

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import load_config
from app.database.psql import AsyncSessionLocal
from app.repositoryes.ReminderRepository import ReminderRepository
from app.lexicon.lexicon_reminder import REMINDER_LEXICON_RU as L

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _check_reminders(bot: Bot):
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        repo = ReminderRepository(session)
        due = await repo.get_due_reminders(now)

        for reminder in due:
            try:
                await bot.send_message(
                    chat_id=reminder.user_id,
                    text=L["notification"].format(text=reminder.text),
                )
            except Exception as e:
                log.warning("Failed to send reminder %s to %s: %s", reminder.id, reminder.user_id, e)
                continue

            if reminder.is_one_time:
                await repo.deactivate(reminder.id)
            else:
                await repo.advance_next_fire(reminder.id)

        log.debug("Checked reminders: %d due", len(due))


def setup_scheduler(bot: Bot):
    global _scheduler
    config = load_config()
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(_check_reminders, "interval", seconds=config.scheduler_interval, args=[bot])
    _scheduler.start()
    log.info("Scheduler started")


async def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("Scheduler stopped")
