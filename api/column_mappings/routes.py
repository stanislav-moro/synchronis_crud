# api/column_mappings/routes.py
import json
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.database import get_db
from models.column_mapping import ColumnMapping
from models.company import Company
from core.templates import templates
from services.log import LogInstance


router = APIRouter()


@router.get("")
async def read_column_mappings(
        request: Request,
        company_id: Optional[str] = None,
        db: AsyncSession = Depends(get_db),
        message: str = None
):
    await LogInstance.debug(f"[ColumnMappings] Запрос списка маппингов. Фильтр company_id={company_id}")

    # 1. Получаем ВСЕ компании
    all_companies_result = await db.execute(select(Company))
    all_companies = all_companies_result.scalars().all()
    company_map = {c.id: c.name for c in all_companies}

    # 2. Безопасно парсим company_id
    company_id_int = None
    if company_id and company_id.strip() != "":
        try:
            company_id_int = int(company_id)
        except (ValueError, TypeError):
            company_id_int = None

    # 3. Получаем маппинги (с фильтром, если нужно)
    query = select(ColumnMapping)
    if company_id_int is not None:
        query = query.where(ColumnMapping.company_id == company_id_int)
    cm_result = await db.execute(query)
    column_mappings = cm_result.scalars().all()

    await LogInstance.debug(f"[ColumnMappings] Найдено маппингов: {len(column_mappings)}")

    # 4. Передаём ВСЕ нужные переменные в шаблон
    return templates.TemplateResponse(
        "column_mappings.html",
        {
            "request": request,
            "column_mappings": column_mappings,
            "company_map": company_map,
            "all_companies": all_companies,
            "selected_company_id": company_id_int,
            "message": message
        }
    )


@router.post("")
async def create_column_mapping(
        request: Request,
        name: str = Form(...),
        source_type: str = Form(...),
        mapping: str = Form(...),
        is_default: str = Form(None),
        company_id: int = Form(...),
        db: AsyncSession = Depends(get_db)
):
    await LogInstance.info(
        f"[ColumnMappings] Запрос на создание маппинга: name='{name}', company_id={company_id}, source_type={source_type}")

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
        await LogInstance.warning(
            f"[ColumnMappings] Ошибка валидации JSON при создании маппинга для company_id={company_id}")
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
        await LogInstance.warning(
            f"[ColumnMappings] Компания не найдена при создании маппинга: company_id={company_id}")
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
        await LogInstance.warning(f"[ColumnMappings] Недопустимый тип источника: {source_type}")
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
        mapping=mapping_dict,
        is_default=(is_default == "true"),
        company_id=company_id
    )
    db.add(new_cm)
    await db.commit()
    await db.refresh(new_cm)

    await LogInstance.info(f"[ColumnMappings] Маппинг создан: id={new_cm.id}, name='{new_cm.name}'")
    return RedirectResponse(
        url="/column_mappings?message=Маппинг+успешно+создан!",
        status_code=303
    )


@router.post("/{mapping_id}/delete")
async def delete_column_mapping(mapping_id: int, db: AsyncSession = Depends(get_db)):
    await LogInstance.info(f"[ColumnMappings] Запрос на удаление маппинга: id={mapping_id}")

    result = await db.execute(select(ColumnMapping).where(ColumnMapping.id == mapping_id))
    mapping = result.scalar_one_or_none()

    if not mapping:
        await LogInstance.warning(f"[ColumnMappings] Маппинг не найден для удаления: id={mapping_id}")
        raise HTTPException(status_code=404, detail="Маппинг не найден")

    await db.delete(mapping)
    await db.commit()

    await LogInstance.info(f"[ColumnMappings] Маппинг удалён: id={mapping_id}")
    return RedirectResponse(url="/column_mappings?message=Маппинг+успешно+удалён!", status_code=303)


@router.get("/{mapping_id}/edit")
async def edit_column_mapping_form(
        mapping_id: int,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    await LogInstance.debug(f"[ColumnMappings] Запрос формы редактирования: id={mapping_id}")

    result = await db.execute(select(ColumnMapping).where(ColumnMapping.id == mapping_id))
    mapping = result.scalar_one_or_none()

    if not mapping:
        await LogInstance.warning(f"[ColumnMappings] Маппинг не найден для редактирования: id={mapping_id}")
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


@router.post("/{mapping_id}/edit")
async def update_column_mapping(
        mapping_id: int,
        request: Request,
        name: str = Form(...),
        source_type: str = Form(...),
        mapping: Optional[str] = Form(None),
        is_default: Optional[str] = Form(None),
        company_id: int = Form(...),
        db: AsyncSession = Depends(get_db)
):
    await LogInstance.info(
        f"[ColumnMappings] Запрос на обновление маппинга: id={mapping_id}, new_name='{name}'")

    # Получаем текущий маппинг и список компаний
    result = await db.execute(select(ColumnMapping).where(ColumnMapping.id == mapping_id))
    mapping_obj = result.scalar_one_or_none()

    if not mapping_obj:
        await LogInstance.warning(f"[ColumnMappings] Маппинг не найден для обновления: id={mapping_id}")
        raise HTTPException(status_code=404, detail="Маппинг не найден")

    companies_result = await db.execute(select(Company))
    companies = companies_result.scalars().all()

    # === РУЧНАЯ ВАЛИДАЦИЯ ===
    if not mapping:
        await LogInstance.warning(
            f"[ColumnMappings] Пустое поле 'Маппинг' при обновлении id={mapping_id}")
        return templates.TemplateResponse(
            "edit_column_mapping.html",
            {
                "request": request,
                "prefill": {
                    "id": mapping_id,
                    "name": name,
                    "source_type": source_type,
                    "mapping": "",
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
        await LogInstance.warning(
            f"[ColumnMappings] Ошибка валидации JSON при обновлении id={mapping_id}")
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
        await LogInstance.warning(
            f"[ColumnMappings] Недопустимый тип источника при обновлении: {source_type}")
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
    await LogInstance.info(f"[ColumnMappings] Маппинг обновлён: id={mapping_id}, name='{mapping_obj.name}'")

    return RedirectResponse(
        url="/column_mappings?message=Маппинг+успешно+обновлён!",
        status_code=303
    )