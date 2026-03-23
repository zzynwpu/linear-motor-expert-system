from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .simulation_models import (
    SimulationCreateResponse,
    SimulationProvider,
    SimulationRequestCreate,
    SimulationResult,
    SimulationRun,
    SimulationTemplate,
)
from .simulation_provider_service import provider_service
from .simulation_service import simulation_service


router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.get("/providers", response_model=list[SimulationProvider])
def list_simulation_providers() -> list[SimulationProvider]:
    return provider_service.list_providers()


@router.get("/providers/{provider_id}", response_model=SimulationProvider)
def get_simulation_provider(provider_id: str) -> SimulationProvider:
    try:
        return provider_service.get_provider(provider_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown simulation provider: {provider_id}") from exc


@router.get("/templates", response_model=list[SimulationTemplate])
def list_simulation_templates() -> list[SimulationTemplate]:
    return simulation_service.list_templates()


@router.get("/templates/{template_id}", response_model=SimulationTemplate)
def get_simulation_template(template_id: str) -> SimulationTemplate:
    try:
        return simulation_service.get_template(template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown simulation template: {template_id}") from exc


@router.post("/requests", response_model=SimulationCreateResponse)
def create_simulation_request(payload: SimulationRequestCreate) -> SimulationCreateResponse:
    try:
        return simulation_service.create_request(payload)
    except KeyError as exc:
        detail = str(exc).strip("'")
        if detail.startswith("remote_") or detail.endswith("_browser"):
            raise HTTPException(status_code=404, detail=f"Unknown simulation provider: {detail}") from exc
        raise HTTPException(status_code=404, detail=f"Unknown simulation template: {payload.template_id}") from exc


@router.get("/runs/{run_id}", response_model=SimulationRun)
def get_simulation_run(run_id: str) -> SimulationRun:
    try:
        return simulation_service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown simulation run: {run_id}") from exc


@router.get("/results/{result_id}", response_model=SimulationResult)
def get_simulation_result(result_id: str) -> SimulationResult:
    try:
        return simulation_service.get_result(result_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown simulation result: {result_id}") from exc
