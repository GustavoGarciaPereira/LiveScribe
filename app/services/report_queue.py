"""Fila de relatórios em segundo plano (worker thread).

Permite que a geração de PDF (pesada) seja desacoplada do request HTTP.
O cliente cria um job, faz polling do status e baixa o PDF quando pronto.
"""

import threading
import uuid
import time
import logging
from queue import Queue

from app.infrastructure.database import SessionLocal
from app.services.chat import ChatService
from app.services.report import ReportService
from app.services.sentiment import LeiaSentimentAnalyzer
from app.services.topics import TfidfTopicExtractor
from app.services.emojis import RegexEmojiExtractor
from app.services.modality import LexiconModalityAnalyzer
from app.services.emotion import LexiconEmotionAnalyzer

logger = logging.getLogger(__name__)


class ReportJob:
    """Representa um job de geração de relatório."""

    def __init__(self, job_id: str, live_id: str, user_id: int | None):
        self.job_id = job_id
        self.live_id = live_id
        self.user_id = user_id
        self.status = "pending"  # pending | processing | done | failed
        self.progress = 0
        self.pdf_bytes: bytes | None = None
        self.error: str | None = None
        self.created_at = time.time()
        self.finished_at: float | None = None

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "live_id": self.live_id,
            "status": self.status,
            "progress": self.progress,
            "error": self.error,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
        }


class ReportQueue:
    """Fila de jobs de relatório processada por uma thread em background."""

    def __init__(self):
        self._jobs: dict[str, ReportJob] = {}
        self._queue: Queue = Queue()
        self._worker: threading.Thread | None = None
        self._running = False
        self._lock = threading.Lock()

    def start(self):
        """Inicia a thread de processamento."""
        if self._running:
            return
        self._running = True
        self._worker = threading.Thread(target=self._process_jobs, daemon=True)
        self._worker.start()
        logger.info("ReportQueue worker thread started.")

    def stop(self):
        """Para a thread de processamento (graceful)."""
        self._running = False
        if self._worker and self._worker.is_alive():
            self._queue.put(None)  # sentinel to unblock
            self._worker.join(timeout=10)
        logger.info("ReportQueue worker thread stopped.")

    def submit(self, live_id: str, user_id: int | None = None) -> str:
        """Enfileira um job e retorna o job_id."""
        job_id = uuid.uuid4().hex[:12]
        job = ReportJob(job_id, live_id, user_id)
        with self._lock:
            self._jobs[job_id] = job
        self._queue.put(job_id)
        logger.info(f"Report job {job_id} submitted (live={live_id}).")
        return job_id

    def get_status(self, job_id: str) -> dict | None:
        """Retorna o status de um job ou None se não encontrado."""
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            return None
        return job.to_dict()

    def get_pdf(self, job_id: str) -> bytes | None:
        """Retorna o PDF do job concluído ou None se não pronto."""
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None or job.status != "done":
            return None
        return job.pdf_bytes

    def _process_jobs(self):
        """Loop principal da thread de processamento."""
        while self._running:
            job_id = self._queue.get()
            if job_id is None:  # sentinel
                break

            with self._lock:
                job = self._jobs.get(job_id)
            if job is None:
                continue

            job.status = "processing"
            job.progress = 10

            db = SessionLocal()
            try:
                # Constrói o ChatService com analisadores reais
                sentiment = LeiaSentimentAnalyzer()
                topic = TfidfTopicExtractor()
                emoji = RegexEmojiExtractor()
                modality = LexiconModalityAnalyzer()
                emotion = LexiconEmotionAnalyzer()
                chat_service = ChatService(db, sentiment, topic, emoji, modality, emotion)

                job.progress = 30
                # Recarrega o modulo report.py para evitar cache do worker thread
                import importlib
                import app.services.report
                importlib.reload(app.services.report)
                from app.services.report import ReportService
                report_service = ReportService(chat_service)

                job.progress = 50
                pdf_bytes = report_service.generate_pdf(job.live_id, user_id=job.user_id)

                job.progress = 90
                job.pdf_bytes = pdf_bytes
                job.status = "done"
                job.progress = 100
                logger.info(f"Report job {job_id} completed.")
            except Exception as e:
                job.status = "failed"
                job.error = str(e)
                logger.error(f"Report job {job_id} failed: {e}")
            finally:
                db.close()
                job.finished_at = time.time()
                self._queue.task_done()
