from datetime import datetime

from sqlalchemy import CHAR, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from models.users import Base


class AIDocument(Base):
    __tablename__ = "ai_documents"
    __table_args__ = (UniqueConstraint("user_id", "sha256", name="uq_ai_document_owner_hash"),)

    id: Mapped[str] = mapped_column(CHAR(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer().with_variant(INTEGER(unsigned=True), "mysql"), ForeignKey("user.id"))
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(CHAR(64))
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
