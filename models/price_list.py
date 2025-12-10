# models/price_list.py
from sqlalchemy import Column, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from models.base import Base

class PriceList(Base):
    __tablename__ = "price_lists"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    is_reference = Column(Boolean, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())