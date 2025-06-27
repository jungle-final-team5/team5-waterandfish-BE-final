from fastapi import FastAPI
from .api import user_router

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, team5-waterandfish-BE!"}

app.include_router(user_router) 