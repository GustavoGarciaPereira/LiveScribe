"""Testes do módulo de YouTube Comments."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_db, get_current_user


# ── Helpers ────────────────────────────────────────────────────

def _make_fake_thread(thread_id: str, author: str, text: str, likes: int,
                      replies: int, published: str = "2024-01-01T00:00:00Z"):
    """Cria um comment thread fake similar à resposta da API."""
    item = {
        "id": thread_id,
        "snippet": {
            "topLevelComment": {
                "snippet": {
                    "authorDisplayName": author,
                    "textDisplay": text,
                    "likeCount": likes,
                    "totalReplyCount": replies,
                    "publishedAt": published,
                }
            }
        },
    }
    if replies > 0:
        item["snippet"]["totalReplyCount"] = replies
    return item


def _make_fake_reply(author: str, text: str, likes: int, published: str = "2024-01-01T00:00:00Z"):
    """Cria uma reply fake."""
    return {
        "snippet": {
            "authorDisplayName": author,
            "textDisplay": text,
            "likeCount": likes,
            "publishedAt": published,
        }
    }


def _make_mock_youtube(threads: list | None = None, replies: list | None = None,
                       video_title: str = "Test Video"):
    """Cria um mock completo do youtube.build retorno."""
    mock_youtube = MagicMock()

    # Mock videos().list()
    mock_videos_list = MagicMock()
    mock_videos_list.execute.return_value = {
        "items": [{"snippet": {"title": video_title}}]
    }
    mock_youtube.videos().list.return_value = mock_videos_list

    # Mock commentThreads().list()
    mock_threads_list = MagicMock()
    mock_threads_list.execute.return_value = {
        "items": threads or [],
        "nextPageToken": None,
    }
    mock_youtube.commentThreads().list.return_value = mock_threads_list

    # Mock comments().list() para replies
    mock_comments_list = MagicMock()
    mock_comments_list.execute.return_value = {
        "items": replies or [],
        "nextPageToken": None,
    }
    mock_youtube.comments().list.return_value = mock_comments_list

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
        result = service.fetch_comments("dQw4w9WgXcQ", user_id=1)

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
            user_id=1, is_reply=False,
        ))
        db_session.add(YouTubeComment(
            video_id="vid1", author="User2", comment="Reply",
            user_id=1, is_reply=True, parent_id="abc",
        ))
        db_session.commit()

        service = YouTubeCommentService(db_session)
        comments = service.get_comments("vid1", 1)

        assert len(comments) == 2
        assert comments[0]["author"] == "User"
        assert comments[1]["is_reply"] is True

    @patch("app.services.youtube_comments.build")
    def test_get_comments_empty(self, mock_build, db_session):
        """Verifica retorno vazio para vídeo sem comentários."""
        from app.services.youtube_comments import YouTubeCommentService

        service = YouTubeCommentService(db_session)
        comments = service.get_comments("vid1", 1)

        assert comments == []

    @patch("app.services.youtube_comments.build")
    def test_export_csv(self, mock_build, db_session):
        """Verifica exportação CSV."""
        from app.models.youtube_comment import YouTubeComment
        from app.services.youtube_comments import YouTubeCommentService

        db_session.add(YouTubeComment(
            video_id="vid1", author="User", comment="Test comment",
            like_count=5, reply_count=0, is_reply=False,
            user_id=1,
        ))
        db_session.add(YouTubeComment(
            video_id="vid1", author="User2", comment="Reply comment",
            like_count=1, reply_count=0, is_reply=True, parent_id="abc",
            user_id=1,
        ))
        db_session.commit()

        service = YouTubeCommentService(db_session)
        csv_bytes = service.export_csv("vid1", 1)
        csv_text = csv_bytes.decode("utf-8-sig")

        assert "author,comment,like_count,reply_count,is_reply,published_at" in csv_text
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
        from app.infrastructure.database import SessionLocal

        # Registra usuário e obtém o db_session usado
        token = self._create_user_and_login(client)
        # Obtém o db session da dependência
        db = next(app.dependency_overrides[get_db]())

        # Insere comentários diretamente
        db.add(YouTubeComment(
            video_id="vid1", video_title="Test", author="User",
            comment="Great video!", like_count=5, user_id=1,
            is_reply=False,
        ))
        db.add(YouTubeComment(
            video_id="vid1", author="User2", comment="Thanks!",
            like_count=1, user_id=1, is_reply=True, parent_id="abc",
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
            user_id=1, is_reply=False,
        ))
        db.commit()

        resp = client.get(
            "/api/youtube/comments/vid1/export?format=csv",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "Test CSV" in resp.text

    def test_ui_page(self, client):
        """Verifica que a página /youtube-comments carrega."""
        resp = client.get("/youtube-comments")
        assert resp.status_code == 200
        assert "📺 Comentários de Vídeos" in resp.text
