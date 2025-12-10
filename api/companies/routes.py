# api/companies/routes.py
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.database import get_db
from models.company import Company
from main import templates  # ← предполагается, что templates определён в main.py

router = APIRouter()

@app.get("/companies")
async def read_companies_html(request: Request, db: AsyncSession = Depends(get_db), message: str = None):
    result = await db.execute(select(Company))
    companies = result.scalars().all()
    return templates.TemplateResponse("companies.html", {"request": request, "companies": companies, "message": message})


@app.post("/companies")
async def create_company(
    name: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    # Создаём объект компании
    new_company = Company(name=name)
    # Добавляем в сессию
    db.add(new_company)
    # Сохраняем в БД
    await db.commit()
    # Обновляем данные (например, id и created_at)
    await db.refresh(new_company)
    # Перенаправляем обратно на список
    return RedirectResponse(url="/companies?message=Компания+успешно+создана!", status_code=303)


@app.post("/companies/{company_id}/delete")
async def delete_company(company_id: int, db: AsyncSession = Depends(get_db)):
    # Найти компанию
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    # Удалить
    await db.delete(company)
    await db.commit()
    # Перенаправить обратно
    return RedirectResponse(url="/companies?message=Компания+успешно+удалена!", status_code=303)


@app.get("/companies/{company_id}/edit")
async def edit_company_form(company_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return templates.TemplateResponse("edit_company.html", {"request": request, "company": company})


@app.post("/companies/{company_id}/edit")
async def update_company(
    company_id: int,
    name: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.name = name
    await db.commit()
    return RedirectResponse(url="/companies?message=Компания+успешно+обновлена!", status_code=303)


# @app.get("/")
# async def root():
#     return RedirectResponse(url="/companies")
