from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.governance import router as governance_router
from app.api.routes.health import router as health_router
from app.api.routes.message_center import router as message_center_router
from app.api.routes.operations import router as operations_router
from app.api.routes.planner import router as planner_router
from app.api.routes.resource_center import router as resource_center_router


api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(governance_router)
api_router.include_router(planner_router)
api_router.include_router(resource_center_router)
api_router.include_router(message_center_router)
api_router.include_router(operations_router)
