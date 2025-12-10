# api/price_lists/routes.py
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from core.database import get_db
from models.price_list import PriceList
from models.company import Company
from core.templates import templates

router = APIRouter()


@router.get("")
async def read_price_lists(
        request: Request,
        db: AsyncSession = Depends(get_db),
        message: str = None
):
    companies_result = await db.execute(select(Company))
    companies = companies_result.scalars().all()

    pl_result = await db.execute(select(PriceList))
    price_lists = pl_result.scalars().all()

    company_map = {c.id: c.name for c in companies}

    return templates.TemplateResponse(
        "price_lists.html",
        {
            "request": request,
            "price_lists": price_lists,
            "company_map": company_map,
            "companies": companies,
            "message": message
        }
    )


@router.post("")
async def create_price_list(
        name: str = Form(...),
        company_id: int = Form(...),
        is_reference: str = Form(None),
        db: AsyncSession = Depends(get_db)
):
    is_ref = is_reference == "true"

    # Проверка существования компании (как раньше)
    company_result = await db.execute(select(Company).where(Company.id == company_id))
    company = company_result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=400, detail="Компания не найдена")

    new_pl = PriceList(
        company_id=company_id,
        name=name,
        is_reference=is_ref
    )
    db.add(new_pl)

    try:
        await db.commit()
        await db.refresh(new_pl)
    except IntegrityError:
        await db.rollback()
        # Перенаправляем обратно на /price_lists с сообщением об ошибке
        return RedirectResponse(
            url="/price_lists?message=Для+этой+компании+уже+существует+эталонный+прайс-лист.+Разрешён+только+один.",
            status_code=303
        )

    return RedirectResponse(url="/price_lists?message=Прайс-лист+успешно+создан!", status_code=303)


@router.post("/{price_list_id}/delete")
async def delete_price_list(price_list_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PriceList).where(PriceList.id == price_list_id))
    price_list = result.scalar_one_or_none()
    if price_list is None:
        raise HTTPException(status_code=404, detail="Price list not found")
    await db.delete(price_list)
    await db.commit()
    return RedirectResponse(url="/price_lists?message=Прайс-лист+успешно+удалён!", status_code=303)


@router.get("/{price_list_id}/edit")
async def edit_price_list_form(
        price_list_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(PriceList).where(PriceList.id == price_list_id))
    price_list = result.scalar_one_or_none()
    if not price_list:
        raise HTTPException(status_code=404, detail="Price list not found")
    return templates.TemplateResponse(
        "edit_price_list.html",
        {"request": request, "price_list": price_list}
    )


@router.post("/{price_list_id}/edit")
async def update_price_list(
        price_list_id: int,
        name: str = Form(...),
        is_reference: str = Form(None),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(PriceList).where(PriceList.id == price_list_id))
    price_list = result.scalar_one_or_none()
    if not price_list:
        raise HTTPException(status_code=404, detail="Прайс-лист не найден")

    price_list.name = name
    price_list.is_reference = (is_reference == "true")

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Перенаправляем обратно на /price_lists с сообщением об ошибке
        return RedirectResponse(
            url="/price_lists?message=Для+этой+компании+уже+существует+эталонный+прайс-лист.+Разрешён+только+один.",
            status_code=303
        )

    return RedirectResponse(url="/price_lists?message=Прайс-лист+успешно+обновлён!", status_code=303)