from fastapi import APIRouter
from src.adapters.input.http.controllers.ping_pong_controller import ping, pong
from src.adapters.input.http.schemas.v1.ping_pong import PingResponse, PongResponse

router = APIRouter()


@router.get("/ping", response_model=PingResponse, summary="Ping")
def ping():
    return {"message": "pong"}


@router.get("/pong", response_model=PongResponse, summary="Pong")
def pong():
    return {"message": "ping"}
