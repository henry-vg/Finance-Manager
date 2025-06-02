from fastapi import APIRouter
from fastapi.responses import JSONResponse


router = APIRouter()


@router.get("/ping")
def ping():
    return JSONResponse(content={"message": "pong"})


@router.get("/pong")
def pong():
    return JSONResponse(content={"message": "ping"})
