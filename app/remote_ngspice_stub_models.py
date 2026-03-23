from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .simulation_models import ArtifactRef, ParameterSweep, PassCriterion, SimulationMetric


class RemoteNgspiceJobCreate(BaseModel):
    simulation_request_id: str
    template_id: str
    tool: str
    project_context: dict = Field(default_factory=dict)
    parameter_bindings: dict = Field(default_factory=dict)
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)
    sweeps: list[ParameterSweep] = Field(default_factory=list)
    measurements: list[str] = Field(default_factory=list)
    pass_criteria: list[PassCriterion] = Field(default_factory=list)
    callback_url: str | None = None


class RemoteNgspiceProgress(BaseModel):
    completed_sweeps: int = 0
    total_sweeps: int = 0


class RemoteNgspiceJobRecord(BaseModel):
    job_id: str
    status: str
    template_id: str
    tool: str
    accepted_at: str
    started_at: str | None = None
    progress: RemoteNgspiceProgress = Field(default_factory=RemoteNgspiceProgress)


class RemoteNgspiceArtifactBundle(BaseModel):
    log_path: str
    waveforms: list[str] = Field(default_factory=list)
    raw_result_path: str


class RemoteNgspiceJobResult(BaseModel):
    job_id: str
    status: str
    summary: str
    metrics: list[SimulationMetric] = Field(default_factory=list)
    worst_case_corner: dict = Field(default_factory=dict)
    artifacts: RemoteNgspiceArtifactBundle
    tool_version: str = "ngspice-stub-0.1"
    template_version: str = "0.1.0"


class RemoteNgspiceCancelResponse(BaseModel):
    job_id: str
    status: str


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def make_job_id() -> str:
    return f"rng_{uuid4().hex[:10]}"
