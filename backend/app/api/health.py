# Returns service status and confirms API is reachable

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "Med Insight AI"}
