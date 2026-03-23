from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .remote_ngspice_stub_models import (
    RemoteNgspiceCancelResponse,
    RemoteNgspiceJobCreate,
    RemoteNgspiceJobRecord,
    RemoteNgspiceJobResult,
)
from .remote_ngspice_stub_service import remote_ngspice_stub_service


router = APIRouter(prefix="/stub/remote-ngspice", tags=["remote-ngspice-stub"])


@router.post("/v1/jobs", response_model=RemoteNgspiceJobRecord)
def create_remote_ngspice_job(payload: RemoteNgspiceJobCreate) -> RemoteNgspiceJobRecord:
    return remote_ngspice_stub_service.create_job(payload)


@router.get("/v1/jobs/{job_id}", response_model=RemoteNgspiceJobRecord)
def get_remote_ngspice_job(job_id: str) -> RemoteNgspiceJobRecord:
    try:
        return remote_ngspice_stub_service.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown remote_ngspice job: {job_id}") from exc


@router.get("/v1/jobs/{job_id}/result", response_model=RemoteNgspiceJobResult)
def get_remote_ngspice_result(job_id: str) -> RemoteNgspiceJobResult:
    try:
        return remote_ngspice_stub_service.get_result(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown remote_ngspice result: {job_id}") from exc


@router.post("/v1/jobs/{job_id}/cancel", response_model=RemoteNgspiceCancelResponse)
def cancel_remote_ngspice_job(job_id: str) -> RemoteNgspiceCancelResponse:
    try:
        return remote_ngspice_stub_service.cancel_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown remote_ngspice job: {job_id}") from exc
