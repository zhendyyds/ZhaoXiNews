from io import BytesIO
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from pypdf.errors import PyPdfError


SEPARATORS = ["\n\n", "\n", ".", "!", "?", "。", "！", "？", " ", ""]


class InvalidDocument(ValueError):
    pass


def parse_document(filename: str, content: bytes) -> list[Document]:
    try:
        if Path(filename).suffix.lower() == ".pdf":
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise InvalidDocument("请上传未加密的 PDF")
            pages = [Document(page_content=page.extract_text(), metadata={"page": number})
                     for number, page in enumerate(reader.pages, start=1)]
        else:
            pages = [Document(page_content=content.decode("utf-8-sig"))]
    except (UnicodeError, PyPdfError, RecursionError) as exc:
        raise InvalidDocument("无法解析文件，请检查 PDF 或 TXT 格式") from exc

    # 与原 RAG 一样按中英文标点切分，分片保留 PDF 的原始页码。
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80, separators=SEPARATORS)
    chunks = splitter.split_documents(pages)
    if not chunks:
        raise InvalidDocument("文件没有可索引的文本，请上传有文字层的 PDF 或 UTF-8 TXT")
    if len(chunks) > 2000:
        raise InvalidDocument("文件切分后的片段过多，请拆成较短的文件上传")
    return chunks


class DocumentIndex:
    def __init__(self, directory: str, embeddings):
        self.store = Chroma(
            collection_name="zhaoxi_private_documents_v1",
            persist_directory=directory,
            embedding_function=embeddings,
            collection_metadata={"hnsw:space": "cosine"},
        )

    def add(self, owner: int, document_id: str, chunks: list[Document]):
        # 固定 ID 和删除旧分片让失败的入库可以安全重试。
        self.delete(owner, document_id)
        for offset in range(0, len(chunks), 10):
            batch = chunks[offset:offset + 10]
            ids = []
            for number, chunk in enumerate(batch, start=offset + 1):
                chunk.metadata.update(owner_id=owner, document_id=document_id, chunk=number)
                ids.append(f"{document_id}:{number}")
            self.store.add_documents(batch, ids=ids)

    def delete(self, owner: int, document_id: str):
        self.store.delete(where={"$and": [{"owner_id": owner}, {"document_id": document_id}]})

    def search(self, owner: int, ready_ids: list[str], query: str):
        where = {"$and": [{"owner_id": owner}, {"document_id": {"$in": ready_ids}}]}
        results = self.store.similarity_search_with_score(query, k=6, filter=where)
        return [chunk for chunk, distance in results if distance <= 0.60]
