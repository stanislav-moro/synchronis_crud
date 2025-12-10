# core/templates.py
import json
from fastapi.templating import Jinja2Templates

# Создаём шаблонизатор
templates = Jinja2Templates(directory="templates")

# Регистрируем кастомный фильтр
def json_dumps(value, indent=None):
    """Кастомный фильтр для Jinja2 с поддержкой ensure_ascii=False"""
    return json.dumps(value, indent=indent, ensure_ascii=False)

templates.env.filters["json_dumps"] = json_dumps