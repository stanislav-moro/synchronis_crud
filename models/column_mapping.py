# models/column_mapping.py
from sqlalchemy import Column, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from models.base import Base

class ColumnMapping(Base):
    __tablename__ = "column_mappings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    source_type = Column(Text, nullable=False)  # 'supplier', 'customer', 'internal'
    mapping = Column(JSONB, nullable=False, default={})
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())