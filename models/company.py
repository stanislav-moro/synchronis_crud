# models/company.py
from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from models.base import Base


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())