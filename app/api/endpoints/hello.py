# app/api/endpoints/hello.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/hello")
async def say_hello():
    """A simple endpoint that returns a greeting."""
    return {"message": "Hello from the Autonomous AI Team!"}
