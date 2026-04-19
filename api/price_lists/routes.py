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
from typing import Optional
from services.log import LogInstance
from services.strategies import SortByNameStrategy, SortByDateStrategy # РАСКАТОВ ONLY

router = APIRouter()

# ИСХОДНЫЙ ВАРИАНТ ДО РАСКАТОВОЙ, ОТКАТИТЬ ПОТОМ
# @router.get("")
# async def read_price_lists(
#         request: Request,
#         company_id: Optional[str] = None,
#         db: AsyncSession = Depends(get_db),
#         message: str = None
# ):
#     await LogInstance.debug(f"[PriceLists] Запрос списка прайсов. Фильтр company_id={company_id}")
#     # Обработка пустого значения
#     if company_id == "" or company_id is None:
#         company_id_int = None
#     else:
#         try:
#             company_id_int = int(company_id)
#         except ValueError:
#             company_id_int = None
#
#     all_companies_result = await db.execute(select(Company))
#     all_companies = all_companies_result.scalars().all()
#     company_map = {c.id: c.name for c in all_companies}
#
#     query = select(PriceList)
#     if company_id_int is not None:
#         query = query.where(PriceList.company_id == company_id_int)
#
#     pl_result = await db.execute(query)
#     price_lists = pl_result.scalars().all()
#     await LogInstance.debug(f"[PriceLists] Найдено прайсов: {len(price_lists)}")
#
#     return templates.TemplateResponse(
#         "price_lists.html",
#         {
#             "request": request,
#             "price_lists": price_lists,
#             "company_map": company_map,
#             "all_companies": all_companies,
#             "selected_company_id": company_id_int,
#             "message": message
#         }
#     )


@router.get("")
async def read_price_lists(
        request: Request,
        company_id: Optional[str] = None,
        sort_by: str = "name",
        db: AsyncSession = Depends(get_db),
        message: str = None
):
    await LogInstance.debug(f"[PriceLists] Запрос списка. Фильтр: {company_id}, Сортировка: {sort_by}")

    if company_id == "" or company_id is None:
        company_id_int = None
    else:
        try:
            company_id_int = int(company_id)
        except ValueError:
            company_id_int = None

    all_companies_result = await db.execute(select(Company))
    all_companies = all_companies_result.scalars().all()
    company_map = {c.id: c.name for c in all_companies}

    query = select(PriceList)
    if company_id_int is not None:
        query = query.where(PriceList.company_id == company_id_int)

    pl_result = await db.execute(query)
    price_lists = pl_result.scalars().all()

    # Выбираем нужный алгоритм в зависимости от параметра sort_by
    if sort_by == "date":
        strategy = SortByDateStrategy()
    else:
        strategy = SortByNameStrategy()  # По умолчанию

    # Запускаем стратегию
    price_lists = await strategy.sort(price_lists)

    await LogInstance.debug(f"[PriceLists] Возвращено прайсов: {len(price_lists)}")

    return templates.TemplateResponse(
        "price_lists.html",
        {
            "request": request,
            "price_lists": price_lists,
            "company_map": company_map,
            "all_companies": all_companies,
            "selected_company_id": company_id_int,
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
    await LogInstance.info(f"[PriceLists] Запрос на создание прайса: name='{name}', company_id={company_id}, is_ref={is_ref}")

    # Проверка существования компании (как раньше)
    company_result = await db.execute(select(Company).where(Company.id == company_id))
    company = company_result.scalar_one_or_none()
    if not company:
        await LogInstance.warning(f"[PriceLists] Компания не найдена: id={company_id}")
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
        await LogInstance.info(f"[PriceLists] Прайс создан: id={new_pl.id}, name='{new_pl.name}'")
    except IntegrityError:
        await db.rollback()
        await LogInstance.warning(f"[PriceLists] Ошибка создания: уже существует эталонный прайс для company_id={company_id}")
        # Перенаправляем обратно на /price_lists с сообщением об ошибке
        return RedirectResponse(
            url="/price_lists?message=Для+этой+компании+уже+существует+эталонный+прайс-лист.+Разрешён+только+один.",
            status_code=303
        )

    return RedirectResponse(url="/price_lists?message=Прайс-лист+успешно+создан!", status_code=303)


@router.post("/{price_list_id}/delete")
async def delete_price_list(price_list_id: int, db: AsyncSession = Depends(get_db)):
    await LogInstance.info(f"[PriceLists] Запрос на удаление прайса: id={price_list_id}")
    result = await db.execute(select(PriceList).where(PriceList.id == price_list_id))
    price_list = result.scalar_one_or_none()
    if price_list is None:
        await LogInstance.warning(f"[PriceLists] Прайс не найден для удаления: id={price_list_id}")
        raise HTTPException(status_code=404, detail="Price list not found")
    await db.delete(price_list)
    await db.commit()
    await LogInstance.info(f"[PriceLists] Прайс удалён: id={price_list_id}")
    return RedirectResponse(url="/price_lists?message=Прайс-лист+успешно+удалён!", status_code=303)


@router.get("/{price_list_id}/edit")
async def edit_price_list_form(
        price_list_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    await LogInstance.debug(f"[PriceLists] Запрос формы редактирования: id={price_list_id}")
    result = await db.execute(select(PriceList).where(PriceList.id == price_list_id))
    price_list = result.scalar_one_or_none()
    if not price_list:
        await LogInstance.warning(f"[PriceLists] Прайс не найден для редактирования: id={price_list_id}")
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
    await LogInstance.info(f"[PriceLists] Запрос на обновление прайса: id={price_list_id}, new_name='{name}'")
    result = await db.execute(select(PriceList).where(PriceList.id == price_list_id))
    price_list = result.scalar_one_or_none()
    if not price_list:
        await LogInstance.warning(f"[PriceLists] Прайс не найден для обновления: id={price_list_id}")
        raise HTTPException(status_code=404, detail="Прайс-лист не найден")

    price_list.name = name
    price_list.is_reference = (is_reference == "true")

    try:
        await db.commit()
        await LogInstance.info(f"[PriceLists] Прайс обновлён: id={price_list_id}, name='{price_list.name}'")
    except IntegrityError:
        await db.rollback()
        await LogInstance.warning(f"[PriceLists] Ошибка обновления: уже существует эталонный прайс для этой компании")
        # Перенаправляем обратно на /price_lists с сообщением об ошибке
        return RedirectResponse(
            url="/price_lists?message=Для+этой+компании+уже+существует+эталонный+прайс-лист.+Разрешён+только+один.",
            status_code=303
        )

    return RedirectResponse(url="/price_lists?message=Прайс-лист+успешно+обновлён!", status_code=303)