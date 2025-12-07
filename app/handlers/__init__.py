from aiogram import Router

from .admin import router as admin_router
from .user_handlers import router as user_router
from .medicine import router as medicine_router
from .other_handlers import router as other_router


router = Router()

router.include_router(admin_router)
router.include_router(user_router)
router.include_router(medicine_router)
router.include_router(other_router)
