from fastapi import APIRouter

router = APIRouter()


@router.get("/hello-world")
def read_test():
    return {"message": "Hello world!"}