from datetime import date, datetime

from pydantic import Field

from .base import ApiSchemaBase


class CreateUserRequest(ApiSchemaBase):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)
    birth_date: date


class UpdateUserRequest(ApiSchemaBase):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)
    birth_date: date


class UserResponse(ApiSchemaBase):
    created_at: datetime
    updated_at: datetime
    first_name: str
    last_name: str
    email: str
    birth_date: date
