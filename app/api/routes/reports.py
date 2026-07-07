"""Endpoints de relatório em background com polling.

Fluxo:
  POST /api/reports          → cria job, retorna job_id
  GET  /api/reports/{job_id} → status e progresso
  GET  /api/reports/{job_id}/download → download do PDF
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import get_current_user, get_report_queue
from app.models.user import User
from app.services.report_queue import ReportQueue

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("")
def create_report(
    live_id: str = Query(..., description="ID da live"),
    user: User = Depends(get_current_user),
    queue: ReportQueue = Depends(get_report_queue),
):
    """Cria um job de geração de relatório PDF em background."""
    job_id = queue.submit(live_id, user_id=user.id)
    return {"job_id": job_id, "status": "pending"}


@router.get("/{job_id}")
def get_report_status(
    job_id: str,
    user: User = Depends(get_current_user),
    queue: ReportQueue = Depends(get_report_queue),
):
    """Retorna o status e progresso de um job de relatório."""
    status_info = queue.get_status(job_id)
    if status_info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job não encontrado.")
    return status_info


@router.get("/{job_id}/download")
def download_report(
    job_id: str,
    user: User = Depends(get_current_user),
    queue: ReportQueue = Depends(get_report_queue),
):
    """Download do PDF quando o job estiver concluído."""
    status_info = queue.get_status(job_id)
    if status_info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job não encontrado.")

    if status_info["status"] == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Relatório falhou: {status_info.get('error', 'erro desconhecido')}",
        )

    pdf_bytes = queue.get_pdf(job_id)
    if pdf_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Relatório ainda não está pronto (status: {status_info['status']}).",
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={status_info['live_id']}_report.pdf"
        },
    )
