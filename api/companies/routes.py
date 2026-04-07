# api/companies/routes.py
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.database import get_db
from models.company import Company
from core.templates import templates
from services.log import LogInstance

router = APIRouter()

@router.get("")
async def read_companies_html(request: Request, db: AsyncSession = Depends(get_db), message: str = None):
    await LogInstance.debug("[Companies] Запрос списка компаний")
    result = await db.execute(select(Company))
    companies = result.scalars().all()
    return templates.TemplateResponse("companies.html", {"request": request, "companies": companies, "message": message})

@router.post("")
async def create_company(
    name: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    await LogInstance.info(f"[Companies] Запрос на создание компании: name='{name}'")
    new_company = Company(name=name)
    db.add(new_company)
    await db.commit()
    await db.refresh(new_company)
    await LogInstance.info(f"[Companies] Компания создана: id={new_company.id}, name='{new_company.name}'")
    return RedirectResponse(url="/companies?message=Компания+успешно+создана!", status_code=303)

@router.post("/{company_id}/delete")
async def delete_company(company_id: int, db: AsyncSession = Depends(get_db)):
    await LogInstance.info(f"[Companies] Запрос на удаление компании: id={company_id}")
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if company is None:
        await LogInstance.warning(f"[Companies] Компания не найдена для удаления: id={company_id}")
        raise HTTPException(status_code=404, detail="Company not found")
    await db.delete(company)
    await db.commit()
    await LogInstance.info(f"[Companies] Компания удалена: id={company_id}")
    return RedirectResponse(url="/companies?message=Компания+успешно+удалена!", status_code=303)

@router.get("/{company_id}/edit")
async def edit_company_form(company_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    await LogInstance.debug(f"[Companies] Запрос формы редактирования: id={company_id}")
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        await LogInstance.warning(f"[Companies] Компания не найдена для редактирования: id={company_id}")
        raise HTTPException(status_code=404, detail="Company not found")
    return templates.TemplateResponse("edit_company.html", {"request": request, "company": company})

@router.post("/{company_id}/edit")
async def update_company(
    company_id: int,
    name: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    await LogInstance.info(f"[Companies] Запрос на обновление компании: id={company_id}, new_name='{name}'")
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        await LogInstance.warning(f"[Companies] Компания не найдена для обновления: id={company_id}")
        raise HTTPException(status_code=404, detail="Company not found")
    company.name = name
    await db.commit()
    await LogInstance.info(f"[Companies] Компания обновлена: id={company_id}, name='{company.name}'")
    return RedirectResponse(url="/companies?message=Компания+успешно+обновлена!", status_code=303)