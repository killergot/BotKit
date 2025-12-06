from aiogram import Router

from .other_handlers import router as other_router
from .user_handlers import router as user_router
from .medicine.upload_items import router as upload_items_router

router = Router()

router.include_router(upload_items_router)
router.include_router(user_router)
router.include_router(other_router)
