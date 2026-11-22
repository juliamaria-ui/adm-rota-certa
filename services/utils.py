from datetime import date, datetime
import re
from decimal import Decimal, InvalidOperation

from errors import ValidationError


def required(data: dict, fields: list[str]):
    for field in fields:
        value = data.get(field)
        if value is None or str(value).strip() == "":
            raise ValidationError(f"Campo obrigatório ausente: {field}.")


def parse_date(value, field: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError(f"Campo {field} deve estar no formato YYYY-MM-DD.") from exc


def parse_decimal(value, field: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValidationError(f"Campo {field} deve ser um número válido.") from exc
    if not number.is_finite() or number >= Decimal('100000000'):
        raise ValidationError(f"Campo {field} está fora da faixa monetária.")
    if number < 0:
        raise ValidationError(f"Campo {field} não pode ser negativo.")
    return number.quantize(Decimal("0.01"))


def clean_string(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def parse_id(value, field: str) -> int:
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)) or int(value) <= 0:
        raise ValidationError(f"Campo {field} deve ser um identificador inteiro positivo.")
    return int(value)


def upper_string(value):
    cleaned = clean_string(value)
    return cleaned.upper() if cleaned else cleaned


def normalizar_cpf(value):
    raw = str(value or "").strip()
    if not re.fullmatch(r"(?:[0-9]{11}|[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2})", raw):
        raise ValidationError("Informe um CPF com 11 dígitos.")
    return re.sub(r"\D", "", raw)
