from datetime import date, datetime

from .base import ApiSchemaBase


class CreateUserRequest(ApiSchemaBase):
    first_name: str
    last_name: str
    email: str
    password: str
    birth_date: date


class UpdateUserRequest(ApiSchemaBase):
    first_name: str
    last_name: str
    email: str
    password: str
    birth_date: date


class UserResponse(ApiSchemaBase):
    first_name: str
    last_name: str
    email: str
    birth_date: date
    created_at: datetime
    updated_at: datetime
