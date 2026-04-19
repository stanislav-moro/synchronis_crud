# main.py
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from core.templates import templates
from api.companies.routes import router as companies_router
from api.price_lists.routes import router as price_lists_router
from api.column_mappings.routes import router as column_mappings_router
from fastapi.staticfiles import StaticFiles
from pathlib import Path


app = FastAPI(title="Synchronis CRUD")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return RedirectResponse(url="/companies")

app.include_router(companies_router, prefix="/companies")
app.include_router(price_lists_router, prefix="/price_lists")
app.include_router(column_mappings_router, prefix="/column_mappings")


# === Временная страница просмотра логов ===
@app.get("/logs")
async def read_logs(request: Request):
    log_file = Path("logs/synchronis_log.txt")
    if log_file.exists():
        lines = log_file.read_text(encoding="utf-8").splitlines()
        content = "\n".join(lines[-200:]) if len(lines) > 200 else log_file.read_text(encoding="utf-8")
    else:
        content = "📂 Лог-файл ещё не создан. Сделай любое действие в приложении."
    return templates.TemplateResponse("logs.html", {"request": request, "content": content})

# Запуск сервера: uvicorn main:app --reload (через терминал)
# Для запуска с ноута - запустить сервер с компа со следующими параметрами: uvicorn main:app --host 0.0.0.0 --port 8000