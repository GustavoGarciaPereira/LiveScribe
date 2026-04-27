"""Testes para o modelo Message."""

from datetime import datetime, timezone
from app.models.message import Message


def test_message_created_at_is_set(db_session):
    """Verifica que o default é aplicado ao persistir."""
    msg = Message(live_id="test", author="A", message="Teste")
    db_session.add(msg)
    db_session.commit()
    assert msg.created_at is not None
    assert isinstance(msg.created_at, datetime)


def test_message_created_at_is_recent(db_session):
    """Verifica que o created_at é próximo do momento atual."""
    msg = Message(live_id="test", author="A", message="Teste")
    db_session.add(msg)
    db_session.commit()
    # SQLite armazena datetime como naive; converte para UTC-aware para comparar
    naive_now = datetime.now(timezone.utc).replace(tzinfo=None)
    diff = abs((msg.created_at - naive_now).total_seconds())
    assert diff < 5  # criado nos últimos 5 segundos
