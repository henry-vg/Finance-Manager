from fastapi import status


def ping():
    return {"message": "pong"}, status.HTTP_200_OK


def pong():
    return {"message": "ping"}, status.HTTP_200_OK
