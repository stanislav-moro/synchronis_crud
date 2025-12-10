# main.py
from fastapi import FastAPI
from core.templates import templates
from api.companies.routes import router as companies_router
from api.price_lists.routes import router as price_lists_router
from api.column_mappings.routes import router as column_mappings_router  # ← новая строка

app = FastAPI(title="Synchronis CRUD")

app.include_router(companies_router, prefix="/companies")
app.include_router(price_lists_router, prefix="/price_lists")
app.include_router(column_mappings_router, prefix="/column_mappings")  # ← новая строка