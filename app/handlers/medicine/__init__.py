from aiogram import Router

from .upload_items import router as upload_items_router
from .expired import router as expired_router
from .share_kit import router as share_kit_router
from .delete import router as delete_router
from .update import router as update_router
from .kits import router as kits_router
from .search import router as search_router



router = Router()

router.include_router(upload_items_router)
router.include_router(share_kit_router)
router.include_router(expired_router)
router.include_router(delete_router)
router.include_router(update_router)
router.include_router(kits_router)
# Должен быть в конце, так как ловит все безусловно
router.include_router(search_router)
