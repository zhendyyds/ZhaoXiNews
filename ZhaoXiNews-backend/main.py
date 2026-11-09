from fastapi import FastAPI
from routers import ai, news, users, favorite, history
from fastapi.middleware.cors import CORSMiddleware

from config.settings import CORS_ORIGINS
from utils.exception_handlers import register_exception_handlers

# uvicorn main:app --reload 终端执行

app = FastAPI()

# 注册异常处理
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

app.include_router(news.router)
app.include_router(users.router)
app.include_router(favorite.router)
app.include_router(history.router)
app.include_router(ai.router)
