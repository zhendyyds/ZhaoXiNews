import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import aclosing
from datetime import date
from typing import Annotated, Literal
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, StringConstraints, model_validator
from sqlalchemy.exc import SQLAlchemyError

from config.db_conf import AsyncSessionLocal
from services import documents
from utils.auth import get_current_user


router = APIRouter(prefix="/api/ai", tags=["ai"])
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=6000)]


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=9)
    mode: Literal["news", "auto", "favorites", "documents"] = "news"
    startDate: date | None = None
    endDate: date | None = None

    @model_validator(mode="after")
    def validate_question(self):
        if self.messages[-1].role != "user":
            raise ValueError("最后一条消息必须是用户问题")
        if self.startDate and self.endDate and self.startDate > self.endDate:
            raise ValueError("开始日期不能晚于结束日期")
        return self


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def ai_user(authorization: Annotated[str | None, Header()] = None) -> int:
    if not authorization:
        raise HTTPException(status_code=401, detail="请先登录后使用新闻助手")
    try:
        async with asyncio.timeout(8), AsyncSessionLocal() as db:
            user = await get_current_user(authorization, db)
            return user.id
    except (SQLAlchemyError, TimeoutError) as exc:
        logger.warning("新闻助手鉴权查询失败 (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="暂时无法验证登录，请稍后重试") from exc


@router.post("/chat")
async def chat(data: ChatRequest, owner: Annotated[int, Depends(ai_user)]):
    if not os.getenv("DASHSCOPE_API_KEY", "").strip():
        raise HTTPException(status_code=503, detail="新闻助手尚未配置 DASHSCOPE_API_KEY")
    try:
        from langsmith import tracing_context
        from services.news_agent import get_model, stream_timeline

        if data.mode != "news":
            from services.assistant import stream_assistant

        model = get_model()
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="新闻助手尚未安装 requirements-ai.txt 中的依赖") from exc

    async def events() -> AsyncIterator[str]:
        yield sse("status", {"text": "正在检索站内新闻…" if data.mode == "news" else "正在分析问题…"})
        try:
            messages = [message.model_dump() for message in data.messages]
            async with asyncio.timeout(60):
                if data.mode == "news":
                    stream = stream_timeline(model, messages, data.startDate, data.endDate)
                else:
                    stream = stream_assistant(model, messages, data.mode, owner, data.startDate, data.endDate)
                with tracing_context(enabled=False):
                    async with aclosing(stream):
                        async for event, payload in stream:
                            yield sse(event, payload)
        except TimeoutError:
            yield sse("error", {"message": "新闻助手响应超时，请稍后重试。"})
        except Exception as exc:
            logger.warning("新闻助手运行失败 (%s)", type(exc).__name__)
            yield sse("error", {"message": "新闻助手暂时无法完成请求，请稍后重试。"})
        else:
            yield sse("done", {})

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/documents")
async def list_documents(owner: Annotated[int, Depends(ai_user)]):
    return await documents.list_documents(owner)


@router.post("/documents")
async def upload_document(request: Request, owner: Annotated[int, Depends(ai_user)],
                          x_document_name: Annotated[str, Header(max_length=3072)]):
    try:
        filename = unquote(x_document_name, errors="strict").strip()
    except UnicodeError as exc:
        raise HTTPException(422, "文件名编码无效") from exc
    if not filename or len(filename) > 255 or any(char in '/\\' or ord(char) < 32 for char in filename):
        raise HTTPException(422, "文件名无效")
    if not filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(415, "仅支持 PDF 和 TXT")

    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > documents.MAX_UPLOAD_BYTES:
            raise HTTPException(413, "文件大小不能超过 10 MB")
        content.extend(chunk)
    if not content:
        raise HTTPException(422, "文件内容为空")
    if not os.getenv("DASHSCOPE_API_KEY", "").strip():
        raise HTTPException(503, "资料库尚未配置 DASHSCOPE_API_KEY")
    try:
        return await documents.upload_document(owner, filename, bytes(content))
    except ImportError as exc:
        raise HTTPException(503, "资料库尚未安装 requirements-ai.txt 中的依赖") from exc


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: Annotated[str, Path(pattern="^[a-f0-9]{32}$")],
                          owner: Annotated[int, Depends(ai_user)]):
    await documents.delete_document(owner, document_id)
    return Response(status_code=204)
