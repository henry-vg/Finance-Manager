from pydantic import BaseModel


class PingResponse(BaseModel):
    message: str


class PongResponse(BaseModel):
    message: str
