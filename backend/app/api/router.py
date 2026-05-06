from fastapi import APIRouter

from app.api.routes.agent import router as agent_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.memories import router as memories_router
from app.api.routes.projects import router as projects_router
from app.api.routes.retrieval import router as retrieval_router
from app.api.routes.repos import router as repos_router
from app.api.routes.skills import router as skills_router
from app.api.routes.skill_candidates import router as skill_candidates_router
from app.api.routes.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(projects_router)
api_router.include_router(documents_router)
api_router.include_router(repos_router)
api_router.include_router(retrieval_router)
api_router.include_router(agent_router)
api_router.include_router(memories_router)
api_router.include_router(skills_router)
api_router.include_router(skill_candidates_router)
api_router.include_router(tasks_router)
