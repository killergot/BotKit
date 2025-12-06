from aiogram import Router

from .other_handlers import router as other_router
from .user_handlers import router as user_router

router = Router()

router.include_router(user_router)
router.include_router(other_router)
