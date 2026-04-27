"""Testes para app/repositories/messages.py."""

from app.repositories.messages import create_message, list_messages_by_live


def test_create_message(db_session):
    msg = create_message(
        db_session, live_id="live1", author="User", content="Hello"
    )
    assert msg.id is not None
    assert msg.live_id == "live1"
    assert msg.author == "User"
    assert msg.message == "Hello"


def test_list_messages_by_live(db_session):
    create_message(db_session, live_id="live1", author="A", content="Msg1")
    create_message(db_session, live_id="live1", author="B", content="Msg2")
    create_message(db_session, live_id="live2", author="C", content="Msg3")

    msgs = list_messages_by_live(db_session, "live1")
    assert len(msgs) == 2

    msgs2 = list_messages_by_live(db_session, "live2")
    assert len(msgs2) == 1


def test_list_messages_empty(db_session):
    msgs = list_messages_by_live(db_session, "nonexistent")
    assert msgs == []
