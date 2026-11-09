import asyncio
import logging
import os
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from config.db_conf import AsyncSessionLocal
from models.ai_document import AIDocument


logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@lru_cache(maxsize=1)
def get_index():
    from langchain_community.embeddings import DashScopeEmbeddings
    from zhaoxi_agent.documents import DocumentIndex

    directory = os.getenv("AI_CHROMA_DIR") or str(Path(__file__).resolve().parents[1] / "data" / "ai_chroma")
    return DocumentIndex(directory, DashScopeEmbeddings(model="text-embedding-v4"))


def describe(row: AIDocument) -> dict:
    return {"id": row.id, "filename": row.filename, "status": row.status, "createdAt": row.created_at.isoformat()}


async def list_documents(owner: int):
    async with AsyncSessionLocal() as db:
        stmt = select(AIDocument).where(AIDocument.user_id == owner).order_by(AIDocument.created_at.desc())
        return [describe(row) for row in (await db.scalars(stmt)).all()]


async def upload_document(owner: int, filename: str, content: bytes):
    from zhaoxi_agent.documents import InvalidDocument, parse_document

    digest = sha256(content).hexdigest()
    stmt = select(AIDocument).where(AIDocument.user_id == owner, AIDocument.sha256 == digest)
    async with AsyncSessionLocal.begin() as db:
        if not await db.scalar(stmt):
            db.add(AIDocument(id=uuid4().hex, user_id=owner, filename=filename, sha256=digest, status="indexing"))
            try:
                await db.flush()
            except IntegrityError:
                # 另一请求已经插入同一用户的同一文件。
                await db.rollback()

    error = None
    async with AsyncSessionLocal.begin() as db:
        row = await db.scalar(stmt.with_for_update())
        if row is None or row.status == "deleting":
            raise HTTPException(409, "该文件正在删除，请稍后重试")
        if row.status == "ready":
            return describe(row)
        document_id = row.id
        try:
            def index_file():
                chunks = parse_document(filename, content)
                get_index().add(owner, document_id, chunks)

            await asyncio.to_thread(index_file)
        except InvalidDocument as exc:
            row.status = "failed"
            error = HTTPException(422, str(exc))
        except Exception as exc:
            row.status = "failed"
            logger.warning("资料入库失败 (%s)", type(exc).__name__)
            error = HTTPException(503, "资料入库失败，可以重新上传重试")
        else:
            row.status = "ready"
            row.filename = filename
        result = describe(row)
    if error:
        raise error
    return result


async def delete_document(owner: int, document_id: str):
    stmt = select(AIDocument).where(AIDocument.id == document_id, AIDocument.user_id == owner).with_for_update()
    async with AsyncSessionLocal.begin() as db:
        row = await db.scalar(stmt)
        if row is None:
            raise HTTPException(404, "资料不存在")
        row.status = "deleting"

    async with AsyncSessionLocal.begin() as db:
        row = await db.scalar(stmt)
        if row is not None:
            try:
                await asyncio.to_thread(lambda: get_index().delete(owner, document_id))
            except Exception as exc:
                logger.warning("资料索引清理失败 (%s)", type(exc).__name__)
                raise HTTPException(503, "资料已退出检索，请重试删除以完成清理") from exc
            await db.delete(row)


async def search_documents(owner: int, query: str):
    ready = select(AIDocument.id, AIDocument.filename).where(AIDocument.user_id == owner, AIDocument.status == "ready")
    async with AsyncSessionLocal() as db:
        ids = list((await db.execute(ready)).scalars())
    if not ids:
        return []
    chunks = await asyncio.to_thread(lambda: get_index().search(owner, ids, query))
    if not chunks:
        return []
    # 再确认命中的文件仍可读取，避免检索期间已删除的片段进入提示词。
    async with AsyncSessionLocal() as db:
        current = dict((await db.execute(ready.where(AIDocument.id.in_(
            {chunk.metadata["document_id"] for chunk in chunks}
        )))).all())
    return [
        {"kind": "document", "id": chunk.metadata["document_id"], "title": current[chunk.metadata["document_id"]],
         "page": chunk.metadata.get("page"), "chunk": chunk.metadata["chunk"], "excerpt": chunk.page_content}
        for chunk in chunks if chunk.metadata["document_id"] in current and chunk.metadata["owner_id"] == owner
    ]
