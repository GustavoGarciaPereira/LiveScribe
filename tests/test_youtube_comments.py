"""Testes do módulo de YouTube Comments."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_db, get_current_user


# ── Helpers ────────────────────────────────────────────────────

def _make_fake_thread(thread_id: str, author: str, text: str, likes: int,
                      replies: int, published: str = "2024-01-01T00:00:00Z"):
    """Cria um comment thread fake similar à resposta REAL da API.

    A API retorna totalReplyCount no nível snippet (thread),
    NÃO dentro de topLevelComment.snippet.
    """
    item = {
        "id": thread_id,
        "snippet": {
            "topLevelComment": {
                "snippet": {
                    "authorDisplayName": author,
                    "textDisplay": text,
                    "likeCount": likes,
                    "publishedAt": published,
                    # totalReplyCount NÃO está aqui na API real
                }
            },
            # totalReplyCount está AQUI no nível do thread
            "totalReplyCount": replies,
        },
    }
    return item


def _make_fake_reply(author: str, text: str, likes: int,
                     published: str = "2024-01-01T00:00:00Z"):
    """Cria uma reply fake."""
    return {
        "id": "r1",
        "snippet": {
            "authorDisplayName": author,
            "textDisplay": text,
            "likeCount": likes,
            "publishedAt": published,
        }
    }


def _make_mock_youtube(threads: list | None = None, replies: list | None = None,
                       video_title: str = "Test Video",
                       reply_sequences: list[list] | None = None):
    """Cria um mock completo do youtube.build retorno.

    Args:
        threads: Lista de threads para commentThreads().list().execute()
        replies: Lista de replies padrão para comments().list().execute()
        reply_sequences: Lista de listas, cada uma para uma chamada sequencial
                         de comments().list().execute(). Se fornecido, substitui replies.
    """
    mock_youtube = MagicMock()

    # Mock videos().list().execute()
    mock_youtube.videos().list.return_value.execute.return_value = {
        "items": [{"snippet": {"title": video_title}}]
    }

    # Mock commentThreads().list().execute()
    mock_youtube.commentThreads().list.return_value.execute.return_value = {
        "items": threads or [],
        "nextPageToken": None,
    }

    # Mock comments().list().execute()
    if reply_sequences:
        mock_youtube.comments().list.return_value.execute.side_effect = [
            {"items": r, "nextPageToken": None} for r in reply_sequences
        ]
    else:
        mock_youtube.comments().list.return_value.execute.return_value = {
            "items": replies or [],
            "nextPageToken": None,
        }

    return mock_youtube


# ── Teste: extract_video_id ────────────────────────────────────

class TestExtractVideoId:
    def test_extract_from_url(self):
        from app.services.youtube_comments import extract_video_id
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_from_short_url(self):
        from app.services.youtube_comments import extract_video_id
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_from_embed_url(self):
        from app.services.youtube_comments import extract_video_id
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_from_shorts_url(self):
        from app.services.youtube_comments import extract_video_id
        assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_raw_id(self):
        from app.services.youtube_comments import extract_video_id
        assert extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_invalid_id(self):
        from app.services.youtube_comments import extract_video_id
        assert extract_video_id("not-a-valid-id") is None

    def test_extract_empty(self):
        from app.services.youtube_comments import extract_video_id
        assert extract_video_id("") is None


# ── Teste: funções auxiliares de data ──────────────────────────

class TestDateHelpers:
    def test_parse_published_utc(self):
        from app.services.youtube_comments import _parse_published_utc
        from datetime import datetime

        dt = _parse_published_utc("2024-06-15T14:30:00Z")
        assert dt.year == 2024
        assert dt.month == 6
        assert dt.day == 15
        assert dt.hour == 14
        assert dt.minute == 30
        assert dt.tzinfo is None, "deve ser naive (UTC representado sem tz)"

    def test_parse_published_utc_with_offset(self):
        from app.services.youtube_comments import _parse_published_utc
        from datetime import datetime

        # Horário com offset -03:00 deve ser convertido para UTC
        dt = _parse_published_utc("2024-06-15T11:30:00-03:00")
        assert dt.hour == 14  # 11:30 -03:00 = 14:30 UTC
        assert dt.minute == 30
        assert dt.tzinfo is None

    def test_format_brt(self):
        from app.services.youtube_comments import _format_brt
        from datetime import datetime

        # 14:30 UTC = 11:30 BRT (UTC-3)
        dt = datetime(2024, 6, 15, 14, 30, 0)
        result = _format_brt(dt)
        assert result is not None
        # A string ISO deve refletir -03:00
        assert "-03:00" in result or result.endswith("-03:00"), (
            f"Esperava offset -03:00, got: {result}"
        )

    def test_format_brt_none(self):
        from app.services.youtube_comments import _format_brt
        assert _format_brt(None) is None


# ── Teste: serviço ────────────────────────────────────────────

class TestYouTubeCommentService:
    @patch("app.services.youtube_comments.build")
    def test_fetch_comments_creates_records(self, mock_build, db_session):
        """Verifica que fetch_comments salva comentários no banco."""
        from app.models.youtube_comment import YouTubeComment
        from app.services.youtube_comments import YouTubeCommentService

        threads = [
            _make_fake_thread("t1", "Autor1", "Comentário principal", 5, 0),
            _make_fake_thread("t2", "Autor2", "Segundo comentário", 2, 1),
        ]
        replies = [
            _make_fake_reply("ReplyAutor", "Resposta ao comentário", 1),
        ]
        mock_youtube = _make_mock_youtube(threads=threads, replies=replies)
        mock_build.return_value = mock_youtube

        service = YouTubeCommentService(db_session)
        result = service.fetch_comments("dQw4w9WgXcQ", user_id=1, max_depth=1)

        assert result["video_id"] == "dQw4w9WgXcQ"
        assert result["video_title"] == "Test Video"
        assert result["total_comments"] == 2  # 2 threads
        assert result["total_replies"] == 1   # 1 reply
        assert result["total_items"] == 3     # total

        # Verifica registros no banco
        records = db_session.query(YouTubeComment).all()
        assert len(records) == 3

        # Verifica o comentário principal
        top = [r for r in records if not r.is_reply]
        assert len(top) == 2
        assert top[0].author == "Autor1"
        assert top[0].comment == "Comentário principal"
        assert top[0].like_count == 5
        assert top[0].video_id == "dQw4w9WgXcQ"
        assert top[0].video_title == "Test Video"

        # Verifica a reply
        replies_rec = [r for r in records if r.is_reply]
        assert len(replies_rec) == 1
        assert replies_rec[0].author == "ReplyAutor"
        assert replies_rec[0].parent_id == "t2"

    @patch("app.services.youtube_comments.build")
    def test_fetch_comments_reply_count(self, mock_build, db_session):
        """Verifica que reply_count é lido do snippet (thread level)."""
        from app.models.youtube_comment import YouTubeComment
        from app.services.youtube_comments import YouTubeCommentService

        threads = [
            _make_fake_thread("t1", "Autor", "Sem replies", 3, 0),
            _make_fake_thread("t2", "Autor2", "Com 5 replies", 1, 5),
            _make_fake_thread("t3", "Autor3", "Com 2 replies", 0, 2),
        ]
        mock_youtube = _make_mock_youtube(threads=threads, replies=[])
        mock_build.return_value = mock_youtube

        service = YouTubeCommentService(db_session)
        service.fetch_comments("vid1", user_id=1, max_depth=0)

        records = db_session.query(YouTubeComment).order_by(YouTubeComment.id).all()
        assert len(records) == 3
        assert records[0].reply_count == 0  # sem replies
        assert records[1].reply_count == 5  # 5 replies no thread level
        assert records[2].reply_count == 2  # 2 replies

    @patch("app.services.youtube_comments.build")
    def test_fetch_comments_max_depth_0(self, mock_build, db_session):
        """max_depth=0: apenas comentários principais, sem replies."""
        from app.services.youtube_comments import YouTubeCommentService
        from app.models.youtube_comment import YouTubeComment

        threads = [
            _make_fake_thread("t1", "Autor1", "Texto", 0, 3),
        ]
        # Mesmo com replies disponíveis, não deve buscá-las
        replies = [
            _make_fake_reply("R1", "Reply 1", 0),
            _make_fake_reply("R2", "Reply 2", 0),
        ]
        mock_youtube = _make_mock_youtube(threads=threads, replies=replies)
        mock_build.return_value = mock_youtube

        service = YouTubeCommentService(db_session)
        result = service.fetch_comments("vid1", user_id=1, max_depth=0)

        assert result["total_comments"] == 1
        assert result["total_replies"] == 0
        assert result["total_items"] == 1

        records = db_session.query(YouTubeComment).all()
        assert len(records) == 1  # apenas o principal
        assert records[0].reply_level == 0

    @patch("app.services.youtube_comments.build")
    def test_fetch_comments_max_depth_1(self, mock_build, db_session):
        """max_depth=1: principal + respostas imediatas."""
        from app.services.youtube_comments import YouTubeCommentService
        from app.models.youtube_comment import YouTubeComment

        threads = [
            _make_fake_thread("t1", "Autor1", "Texto", 0, 2),
        ]
        replies = [
            _make_fake_reply("R1", "Reply 1", 0),
            _make_fake_reply("R2", "Reply 2", 0),
        ]
        mock_youtube = _make_mock_youtube(threads=threads, replies=replies)
        mock_build.return_value = mock_youtube

        service = YouTubeCommentService(db_session)
        result = service.fetch_comments("vid1", user_id=1, max_depth=1)

        assert result["total_comments"] == 1
        assert result["total_replies"] == 2
        assert result["total_items"] == 3

        records = db_session.query(YouTubeComment).order_by(YouTubeComment.id).all()
        assert len(records) == 3

        principal = [r for r in records if r.is_reply is False]
        respostas = [r for r in records if r.is_reply]
        assert len(principal) == 1
        assert len(respostas) == 2
        for r in respostas:
            assert r.reply_level == 1  # N1

    @patch("app.services.youtube_comments.build")
    def test_fetch_comments_reply_levels(self, mock_build, db_session):
        """Verifica reply_level em profundidade N2."""
        from app.services.youtube_comments import YouTubeCommentService
        from app.models.youtube_comment import YouTubeComment

        # Thread com 1 reply, que por sua vez tem 1 sub-reply
        threads = [
            _make_fake_thread("t1", "Autor", "Principal", 0, 1),
        ]
        # Reply nível 1
        reply_n1 = _make_fake_reply("R1", "Resposta N1", 0)
        # Reply nível 2 (resposta da resposta N1)
        reply_n2 = _make_fake_reply("R2", "Resposta N2", 0)

        # Sequência de replies:
        # 1ª chamada (parentId=t1)      → [reply_n1]
        # 2ª chamada (parentId=r1)      → [reply_n2]
        # 3ª chamada (parentId=r2)      → []  → para a recursão
        mock_youtube = _make_mock_youtube(
            threads=threads,
            reply_sequences=[[reply_n1], [reply_n2], []],
        )
        mock_build.return_value = mock_youtube

        service = YouTubeCommentService(db_session)
        result = service.fetch_comments("vid1", user_id=1, max_depth=2)

        assert result["total_comments"] == 1
        assert result["total_replies"] == 2
        assert result["total_items"] == 3

        records = db_session.query(YouTubeComment).order_by(YouTubeComment.id).all()
        assert len(records) == 3

        principal = [r for r in records if r.reply_level == 0]
        n1 = [r for r in records if r.reply_level == 1]
        n2 = [r for r in records if r.reply_level == 2]
        assert len(principal) == 1
        assert len(n1) == 1
        assert len(n2) == 1

    @patch("app.services.youtube_comments.build")
    def test_fetch_comments_clears_old_data(self, mock_build, db_session):
        """Verifica que fetch sobrescreve dados antigos do mesmo video."""
        from app.models.youtube_comment import YouTubeComment
        from app.services.youtube_comments import YouTubeCommentService

        # Dado: dados antigos
        old = YouTubeComment(
            video_id="dQw4w9WgXcQ", video_title="Old", author="Old",
            comment="Old", user_id=1, is_reply=False
        )
        db_session.add(old)
        db_session.commit()

        threads = [
            _make_fake_thread("t1", "NovoAutor", "Novo comentário", 0, 0),
        ]
        mock_youtube = _make_mock_youtube(threads=threads)
        mock_build.return_value = mock_youtube

        service = YouTubeCommentService(db_session)
        result = service.fetch_comments("dQw4w9WgXcQ", user_id=1)

        assert result["total_items"] == 1

        records = db_session.query(YouTubeComment).all()
        assert len(records) == 1
        assert records[0].author == "NovoAutor"

    @patch("app.services.youtube_comments.build")
    def test_list_videos(self, mock_build, db_session):
        """Verifica listagem de vídeos agrupados."""
        from app.models.youtube_comment import YouTubeComment
        from app.services.youtube_comments import YouTubeCommentService

        # Insere dados de teste diretamente
        for i in range(3):
            db_session.add(YouTubeComment(
                video_id=f"vid{i}", video_title=f"Video {i}",
                author="User", comment="Test", user_id=1,
                is_reply=False,
                collected_at=None,
            ))
        db_session.commit()

        service = YouTubeCommentService(db_session)
        videos = service.list_videos(1)

        assert len(videos) == 3
        assert videos[0]["video_id"] in ("vid0", "vid1", "vid2")

    @patch("app.services.youtube_comments.build")
    def test_list_videos_filters_by_user(self, mock_build, db_session):
        """Verifica que list_videos filtra por user_id."""
        from app.models.youtube_comment import YouTubeComment
        from app.services.youtube_comments import YouTubeCommentService

        db_session.add(YouTubeComment(
            video_id="vid1", author="User", comment="Test",
            user_id=1, is_reply=False,
        ))
        db_session.add(YouTubeComment(
            video_id="vid2", author="User2", comment="Test2",
            user_id=99, is_reply=False,
        ))
        db_session.commit()

        service = YouTubeCommentService(db_session)
        videos = service.list_videos(1)

        assert len(videos) == 1
        assert videos[0]["video_id"] == "vid1"

    @patch("app.services.youtube_comments.build")
    def test_get_comments(self, mock_build, db_session):
        """Verifica retorno de comentários de um vídeo."""
        from app.models.youtube_comment import YouTubeComment
        from app.services.youtube_comments import YouTubeCommentService

        db_session.add(YouTubeComment(
            video_id="vid1", author="User", comment="Test",
            user_id=1, is_reply=False, reply_level=0,
        ))
        db_session.add(YouTubeComment(
            video_id="vid1", author="User2", comment="Reply",
            user_id=1, is_reply=True, reply_level=1, parent_id="abc",
        ))
        db_session.commit()

        service = YouTubeCommentService(db_session)
        comments = service.get_comments("vid1", 1)

        assert len(comments) == 2
        assert comments[0]["author"] == "User"
        assert comments[1]["is_reply"] is True
        assert comments[1]["reply_level"] == 1

    @patch("app.services.youtube_comments.build")
    def test_get_comments_empty(self, mock_build, db_session):
        """Verifica retorno vazio para vídeo sem comentários."""
        from app.services.youtube_comments import YouTubeCommentService

        service = YouTubeCommentService(db_session)
        comments = service.get_comments("vid1", 1)

        assert comments == []

    @patch("app.services.youtube_comments.build")
    def test_get_comments_timezone_brt(self, mock_build, db_session):
        """Verifica que published_at é retornado em BRT (-03:00)."""
        from datetime import datetime, timezone
        from app.models.youtube_comment import YouTubeComment
        from app.services.youtube_comments import YouTubeCommentService

        # Salva um datetime UTC naive (como armazenado no SQLite)
        db_session.add(YouTubeComment(
            video_id="vid1", author="User", comment="Test",
            published_at=datetime(2024, 6, 15, 14, 30, 0),  # 14:30 UTC
            user_id=1, is_reply=False,
        ))
        db_session.commit()

        service = YouTubeCommentService(db_session)
        comments = service.get_comments("vid1", 1)

        assert len(comments) == 1
        published = comments[0]["published_at"]
        assert published is not None
        # BRT é UTC-3, então 14:30 UTC vira 11:30 BRT
        assert "11:30" in published
        assert "-03:00" in published

    @patch("app.services.youtube_comments.build")
    def test_export_csv(self, mock_build, db_session):
        """Verifica exportação CSV."""
        from app.models.youtube_comment import YouTubeComment
        from app.services.youtube_comments import YouTubeCommentService

        db_session.add(YouTubeComment(
            video_id="vid1", author="User", comment="Test comment",
            like_count=5, reply_count=0, is_reply=False, reply_level=0,
            user_id=1,
        ))
        db_session.add(YouTubeComment(
            video_id="vid1", author="User2", comment="Reply comment",
            like_count=1, reply_count=0, is_reply=True, reply_level=1,
            parent_id="abc", user_id=1,
        ))
        db_session.commit()

        service = YouTubeCommentService(db_session)
        csv_bytes = service.export_csv("vid1", 1)
        csv_text = csv_bytes.decode("utf-8-sig")

        assert "author,comment,like_count,reply_count,is_reply,reply_level,published_at" in csv_text
        assert "Test comment" in csv_text
        assert "Reply comment" in csv_text
        assert "User" in csv_text

    @patch("app.services.youtube_comments.build")
    def test_export_csv_filters_by_user(self, mock_build, db_session):
        """Verifica que export respeita user_id."""
        from app.models.youtube_comment import YouTubeComment
        from app.services.youtube_comments import YouTubeCommentService

        db_session.add(YouTubeComment(
            video_id="vid1", author="User", comment="Test",
            user_id=1, is_reply=False,
        ))
        db_session.add(YouTubeComment(
            video_id="vid1", author="Other", comment="Other",
            user_id=99, is_reply=False,
        ))
        db_session.commit()

        service = YouTubeCommentService(db_session)
        csv_bytes = service.export_csv("vid1", 1)
        csv_text = csv_bytes.decode("utf-8-sig")

        assert "User" in csv_text
        assert "Other" not in csv_text


# ── Testes de rota ────────────────────────────────────────────

class TestYouTubeCommentRoutes:
    @pytest.fixture(autouse=True)
    def setup(self, db_session):
        """Configura dependências para os testes de rota."""
        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        yield
        app.dependency_overrides.clear()

    def _create_user_and_login(self, client: TestClient) -> str:
        """Cria usuário e retorna token JWT."""
        client.post("/api/auth/register", json={
            "email": "yt@test.com",
            "name": "YT User",
            "password": "testpass123",
        })
        login_resp = client.post("/api/auth/login", json={
            "email": "yt@test.com",
            "password": "testpass123",
        })
        return login_resp.json()["access_token"]

    def test_fetch_without_auth(self, client):
        """Verifica que POST /api/youtube/comments/fetch sem token retorna 401."""
        resp = client.post("/api/youtube/comments/fetch", json={"video_id": "dQw4w9WgXcQ"})
        assert resp.status_code == 401

    def test_fetch_invalid_id(self, client):
        """Verifica que ID inválido retorna 400."""
        token = self._create_user_and_login(client)
        resp = client.post(
            "/api/youtube/comments/fetch",
            json={"video_id": "invalid"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_fetch_invalid_max_depth(self, client):
        """Verifica que max_depth inválido retorna 400."""
        token = self._create_user_and_login(client)
        resp = client.post(
            "/api/youtube/comments/fetch",
            json={"video_id": "dQw4w9WgXcQ", "max_depth": -2},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_fetch_invalid_max_depth_type(self, client):
        """Verifica que max_depth não inteiro retorna 400."""
        token = self._create_user_and_login(client)
        resp = client.post(
            "/api/youtube/comments/fetch",
            json={"video_id": "dQw4w9WgXcQ", "max_depth": "all"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    @patch("app.services.youtube_comments.build")
    def test_fetch_success(self, mock_build, client):
        """Verifica coleta de comentários com sucesso."""
        threads = [
            _make_fake_thread("t1", "Autor1", "Ótimo vídeo!", 10, 0),
        ]
        mock_youtube = _make_mock_youtube(threads=threads)
        mock_build.return_value = mock_youtube

        token = self._create_user_and_login(client)
        resp = client.post(
            "/api/youtube/comments/fetch",
            json={"video_id": "dQw4w9WgXcQ"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["video_id"] == "dQw4w9WgXcQ"
        assert data["total_items"] == 1
        assert data["max_depth"] == -1  # default

    @patch("app.services.youtube_comments.build")
    def test_fetch_with_max_depth(self, mock_build, client):
        """Verifica coleta com max_depth=0."""
        threads = [
            _make_fake_thread("t1", "Autor1", "Texto", 0, 3),
        ]
        mock_youtube = _make_mock_youtube(threads=threads)
        mock_build.return_value = mock_youtube

        token = self._create_user_and_login(client)
        resp = client.post(
            "/api/youtube/comments/fetch",
            json={"video_id": "dQw4w9WgXcQ", "max_depth": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["max_depth"] == 0
        assert data["total_items"] == 1  # só o principal

    def test_list_videos_without_auth(self, client):
        """Verifica que GET sem token retorna 401."""
        resp = client.get("/api/youtube/comments")
        assert resp.status_code == 401

    def test_list_videos_empty(self, client):
        """Verifica listagem vazia."""
        token = self._create_user_and_login(client)
        resp = client.get(
            "/api/youtube/comments",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["videos"] == []

    @patch("app.services.youtube_comments.build")
    def test_get_comments_route(self, mock_build, client):
        """Verifica rota de listar comentários de um vídeo."""
        from app.models.youtube_comment import YouTubeComment

        token = self._create_user_and_login(client)
        db = next(app.dependency_overrides[get_db]())

        # Insere comentários diretamente
        db.add(YouTubeComment(
            video_id="vid1", video_title="Test", author="User",
            comment="Great video!", like_count=5, user_id=1,
            is_reply=False, reply_level=0,
        ))
        db.add(YouTubeComment(
            video_id="vid1", author="User2", comment="Thanks!",
            like_count=1, user_id=1, is_reply=True, reply_level=1,
            parent_id="abc",
        ))
        db.commit()

        resp = client.get(
            "/api/youtube/comments/vid1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["author"] == "User"
        assert data[0]["reply_level"] == 0
        assert data[1]["reply_level"] == 1

    def test_get_comments_not_found(self, client):
        """Verifica 404 para vídeo sem comentários."""
        token = self._create_user_and_login(client)
        resp = client.get(
            "/api/youtube/comments/nonexistent",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @patch("app.services.youtube_comments.build")
    def test_export_csv_route(self, mock_build, client):
        """Verifica exportação CSV via rota."""
        from app.models.youtube_comment import YouTubeComment
        db = next(app.dependency_overrides[get_db]())

        token = self._create_user_and_login(client)

        db.add(YouTubeComment(
            video_id="vid1", author="User", comment="Test CSV",
            user_id=1, is_reply=False, reply_level=0,
        ))
        db.commit()

        resp = client.get(
            "/api/youtube/comments/vid1/export?format=csv",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "Test CSV" in resp.text

    def test_ui_page_without_auth(self, client):
        """Verifica que /youtube-comments sem auth redireciona para /login."""
        resp = client.get("/youtube-comments", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers.get("location", "")

    def test_ui_page_authenticated(self, client):
        """Verifica que a página /youtube-comments carrega com auth."""
        # Cria usuário e faz login via cookie
        from app.models.user import User
        from app.services.auth import create_access_token
        db = next(app.dependency_overrides.get(get_db, lambda: None)())

        if db:
            user = User(email="ui@test.com", name="UI Test",
                        google_id="ui_test", provider="local")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_access_token(user.id)
            db.close()

            client.cookies.set("access_token", token)
            resp = client.get("/youtube-comments")
            assert resp.status_code == 200
            assert "📺 Comentários de Vídeos" in resp.text
        else:
            # fallback: se não conseguir db, só verifica o redirect
            resp = client.get("/youtube-comments", follow_redirects=False)
            assert resp.status_code == 303
        assert "Todas as respostas" in resp.text  # dropdown presente
