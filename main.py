# main.py
from fastapi import FastAPI
from fastapi.responses import RedirectResponse  # ← добавьте этот импорт
from core.templates import templates
from api.companies.routes import router as companies_router
from api.price_lists.routes import router as price_lists_router
from api.column_mappings.routes import router as column_mappings_router

app = FastAPI(title="Synchronis CRUD")

# Маршрут для корня
@app.get("/")
async def root():
    return RedirectResponse(url="/companies")

app.include_router(companies_router, prefix="/companies")
app.include_router(price_lists_router, prefix="/price_lists")
app.include_router(column_mappings_router, prefix="/column_mappings")