from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError
from fastapi import FastAPI, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
import json
from typing import Optional
from models import Company, PriceList, ColumnMapping

# Указываем папку с шаблонами
templates = Jinja2Templates(directory="templates")


def json_dumps(value, indent=None):
    """Кастомный фильтр для Jinja2 с поддержкой ensure_ascii=False"""
    return json.dumps(value, indent=indent, ensure_ascii=False)


# Регистрируем фильтр
templates.env.filters["json_dumps"] = json_dumps
app = FastAPI(title="Synchronis CRUD")


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


@app.get("/price_lists")
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


@app.post("/price_lists")
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


@app.post("/price_lists/{price_list_id}/delete")
async def delete_price_list(price_list_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PriceList).where(PriceList.id == price_list_id))
    price_list = result.scalar_one_or_none()
    if price_list is None:
        raise HTTPException(status_code=404, detail="Price list not found")
    await db.delete(price_list)
    await db.commit()
    return RedirectResponse(url="/price_lists?message=Прайс-лист+успешно+удалён!", status_code=303)


@app.get("/price_lists/{price_list_id}/edit")
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


@app.post("/price_lists/{price_list_id}/edit")
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


# @app.get("/")
# async def root():
#     return RedirectResponse(url="/companies")


@app.get("/column_mappings")
async def read_column_mappings(
        request: Request,
        db: AsyncSession = Depends(get_db),
        message: str = None
):
    # Получаем компании для выпадающего списка и отображения
    company_result = await db.execute(select(Company))
    companies = company_result.scalars().all()
    company_map = {c.id: c.name for c in companies}

    # Получаем все маппинги
    cm_result = await db.execute(select(ColumnMapping))
    column_mappings = cm_result.scalars().all()

    return templates.TemplateResponse(
        "column_mappings.html",
        {
            "request": request,
            "column_mappings": column_mappings,
            "company_map": company_map,
            "companies": companies,
            "message": message
        }
    )


@app.post("/column_mappings")
async def create_column_mapping(
        request: Request,
        name: str = Form(...),
        source_type: str = Form(...),
        mapping: str = Form(...),
        is_default: str = Form(None),
        company_id: int = Form(...),
        db: AsyncSession = Depends(get_db)
):
    # Загружаем данные для формы (на случай ошибки)
    companies_result = await db.execute(select(Company))
    companies = companies_result.scalars().all()
    company_map = {c.id: c.name for c in companies}
    cm_result = await db.execute(select(ColumnMapping))
    column_mappings = cm_result.scalars().all()

    # Валидация JSON
    try:
        mapping_dict = json.loads(mapping)
        if not isinstance(mapping_dict, dict):
            raise ValueError("Mapping must be a JSON object")
    except (ValueError, TypeError):
        return templates.TemplateResponse(
            "column_mappings.html",
            {
                "request": request,
                "column_mappings": column_mappings,
                "company_map": company_map,
                "companies": companies,
                "message": "Некорректный JSON в поле 'Маппинг'. Исправьте ошибку и попробуйте снова.",
                "prefill": {
                    "name": name,
                    "source_type": source_type,
                    "mapping": mapping,
                    "is_default": is_default == "true",
                    "company_id": company_id
                }
            }
        )

    # Проверка существования компании
    if company_id not in company_map:
        return templates.TemplateResponse(
            "column_mappings.html",
            {
                "request": request,
                "column_mappings": column_mappings,
                "company_map": company_map,
                "companies": companies,
                "message": "Выбрана несуществующая компания.",
                "prefill": {
                    "name": name,
                    "source_type": source_type,
                    "mapping": mapping,
                    "is_default": is_default == "true",
                    "company_id": company_id
                }
            }
        )

    # Проверка типа источника
    if source_type not in {"supplier", "customer", "internal"}:
        return templates.TemplateResponse(
            "column_mappings.html",
            {
                "request": request,
                "column_mappings": column_mappings,
                "company_map": company_map,
                "companies": companies,
                "message": "Недопустимый тип источника.",
                "prefill": {
                    "name": name,
                    "source_type": source_type,
                    "mapping": mapping,
                    "is_default": is_default == "true",
                    "company_id": company_id
                }
            }
        )

    # === СОЗДАНИЕ И СОХРАНЕНИЕ ===
    new_cm = ColumnMapping(
        name=name,
        source_type=source_type,
        mapping=mapping_dict,  # ← передаём словарь
        is_default=(is_default == "true"),
        company_id=company_id
    )
    db.add(new_cm)
    await db.commit()
    await db.refresh(new_cm)

    return RedirectResponse(
        url="/column_mappings?message=Маппинг+успешно+создан!",
        status_code=303
    )


@app.post("/column_mappings/{mapping_id}/delete")
async def delete_column_mapping(mapping_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ColumnMapping).where(ColumnMapping.id == mapping_id))
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="Маппинг не найден")
    await db.delete(mapping)
    await db.commit()
    return RedirectResponse(url="/column_mappings?message=Маппинг+успешно+удалён!", status_code=303)


@app.get("/column_mappings/{mapping_id}/edit")
async def edit_column_mapping_form(
        mapping_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ColumnMapping).where(ColumnMapping.id == mapping_id))
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="Маппинг не найден")

    # Получаем компании для выпадающего списка
    companies_result = await db.execute(select(Company))
    companies = companies_result.scalars().all()

    return templates.TemplateResponse(
        "edit_column_mapping.html",
        {
            "request": request,
            "mapping": mapping,
            "companies": companies
        }
    )


@app.post("/column_mappings/{mapping_id}/edit")
async def update_column_mapping(
        mapping_id: int,
        request: Request,
        name: str = Form(...),
        source_type: str = Form(...),
        mapping: Optional[str] = Form(None),  # ← стало опциональным
        is_default: Optional[str] = Form(None),
        company_id: int = Form(...),
        db: AsyncSession = Depends(get_db)
):
    # Получаем текущий маппинг и список компаний
    result = await db.execute(select(ColumnMapping).where(ColumnMapping.id == mapping_id))
    mapping_obj = result.scalar_one_or_none()
    if not mapping_obj:
        raise HTTPException(status_code=404, detail="Маппинг не найден")

    companies_result = await db.execute(select(Company))
    companies = companies_result.scalars().all()

    # === РУЧНАЯ ВАЛИДАЦИЯ ===
    if not mapping:
        return templates.TemplateResponse(
            "edit_column_mapping.html",
            {
                "request": request,
                "prefill": {
                    "id": mapping_id,
                    "name": name,
                    "source_type": source_type,
                    "mapping": "",  # пустая строка
                    "is_default": is_default == "true",
                    "company_id": company_id
                },
                "companies": companies,
                "message": "Поле 'Маппинг' обязательно для заполнения."
            }
        )

    # Валидация JSON
    try:
        mapping_dict = json.loads(mapping)
        if not isinstance(mapping_dict, dict):
            raise ValueError("Mapping must be a JSON object")
    except (ValueError, TypeError):
        return templates.TemplateResponse(
            "edit_column_mapping.html",
            {
                "request": request,
                "prefill": {
                    "id": mapping_id,
                    "name": name,
                    "source_type": source_type,
                    "mapping": mapping,
                    "is_default": is_default == "true",
                    "company_id": company_id
                },
                "companies": companies,
                "message": "Некорректный JSON в поле 'Маппинг'. Исправьте ошибку и попробуйте снова."
            }
        )

    if source_type not in {"supplier", "customer", "internal"}:
        return templates.TemplateResponse(
            "edit_column_mapping.html",
            {
                "request": request,
                "prefill": {
                    "id": mapping_id,
                    "name": name,
                    "source_type": source_type,
                    "mapping": mapping,
                    "is_default": is_default == "true",
                    "company_id": company_id
                },
                "companies": companies,
                "message": "Недопустимый тип источника."
            }
        )

    # Обновляем запись
    mapping_obj.name = name
    mapping_obj.source_type = source_type
    mapping_obj.mapping = mapping_dict
    mapping_obj.is_default = (is_default == "true")
    mapping_obj.company_id = company_id

    await db.commit()
    return RedirectResponse(
        url="/column_mappings?message=Маппинг+успешно+обновлён!",
        status_code=303
    )