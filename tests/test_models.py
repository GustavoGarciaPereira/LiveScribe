"""Testes para o modelo Message."""

from datetime import datetime
from app.models.message import Message
from app.core.timezone import now as now_local


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
    # SQLite armazena datetime como naive; compara com now_local() também naive
    naive_now = now_local().replace(tzinfo=None)
    diff = abs((msg.created_at - naive_now).total_seconds())
    assert diff < 5  # criado nos últimos 5 segundos
