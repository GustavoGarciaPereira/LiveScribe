"""Utilitários de fuso horário — Brasil (BRT, America/Sao_Paulo).

Como o SQLite armazena datetimes como naive (sem tzinfo), armazenamos
diretamente no fuso configurado (default BRT) em vez de UTC. Isso evita
conversões desnecessárias e entrega os horários que o usuário espera ver.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def _get_tz() -> ZoneInfo:
    return ZoneInfo(settings.TIMEZONE)


def now() -> datetime:
    """Retorna o datetime atual no fuso configurado (default BRT)."""
    return datetime.now(tz=_get_tz())


def to_local(dt: datetime) -> datetime:
    """Converte um datetime qualquer para o fuso configurado."""
    if dt.tzinfo is None:
        # Datetime naive — assume que já está no fuso local (ex: SQLite)
        return dt.replace(tzinfo=_get_tz())
    return dt.astimezone(_get_tz())
