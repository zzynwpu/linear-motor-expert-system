from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SimulationLevel = Literal["circuit", "system"]
RunStatus = Literal["queued", "running", "completed", "failed", "partial", "cancelled"]
ResultStatus = Literal["pass", "pass_with_margin_risk", "risk", "fail", "inconclusive"]
ExecutionTarget = Literal["browser", "remote_service", "agent_tool", "local"]
ProviderCapability = Literal["circuit", "system", "education", "power_electronics", "control", "browser_ui", "api_ready"]
DispatchStatus = Literal["prepared", "submitted", "queued", "running", "completed", "failed", "cancelled"]


class ArtifactRef(BaseModel):
    artifact_type: str
    path: str


class ParameterSweep(BaseModel):
    name: str
    type: Literal["corner", "list", "monte_carlo"] = "corner"
    values: list[Any] = Field(default_factory=list)


class PassCriterion(BaseModel):
    metric: str
    operator: Literal[">=", ">", "<=", "<", "=="]
    value: float
    unit: str | None = None


class SimulationProvider(BaseModel):
    provider_id: str
    name: str
    execution_target: ExecutionTarget
    engine: str
    homepage: str | None = None
    strengths: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    suitable_for: list[str] = Field(default_factory=list)
    capabilities: list[ProviderCapability] = Field(default_factory=list)
    recommended: bool = False
    notes: str | None = None


class SimulationTemplate(BaseModel):
    template_id: str
    name: str
    simulation_level: SimulationLevel
    applicable_motor_types: list[str] = Field(default_factory=list)
    applicable_task_types: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    default_sweeps: list[ParameterSweep] = Field(default_factory=list)
    key_measurements: list[str] = Field(default_factory=list)
    pass_criteria: list[PassCriterion] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)
    recommended_provider_ids: list[str] = Field(default_factory=list)
    version: str = "0.1.0"


class SimulationRequestCreate(BaseModel):
    task_type: str
    motor_type: str
    simulation_level: SimulationLevel
    simulation_goal: str
    selected_tool: str
    template_id: str
    provider_id: str | None = None
    execution_target: ExecutionTarget = "remote_service"
    project_context: dict[str, Any] = Field(default_factory=dict)
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)
    parameter_bindings: dict[str, Any] = Field(default_factory=dict)
    sweeps: list[ParameterSweep] = Field(default_factory=list)
    measurements: list[str] = Field(default_factory=list)
    pass_criteria: list[PassCriterion] = Field(default_factory=list)
    priority: Literal["low", "medium", "high"] = "medium"
    auto_stub_result: bool = True


class SimulationRequestRecord(SimulationRequestCreate):
    simulation_request_id: str
    created_at: str


class SimulationRun(BaseModel):
    simulation_run_id: str
    simulation_request_id: str
    tool: str
    provider_id: str | None = None
    execution_target: ExecutionTarget = "remote_service"
    status: RunStatus
    started_at: str
    ended_at: str | None = None
    runtime_seconds: int | None = None
    execution_mode: Literal["stub", "batch", "remote"] = "stub"
    template_id: str
    sweep_instances: int = 0
    retry_count: int = 0


class SimulationMetric(BaseModel):
    name: str
    value: float | None = None
    unit: str | None = None
    limit: float | None = None
    judgement: Literal["pass", "fail", "unknown"] = "unknown"


class SimulationResult(BaseModel):
    simulation_result_id: str
    simulation_run_id: str
    overall_status: ResultStatus
    summary: str
    provider_id: str | None = None
    execution_target: ExecutionTarget = "remote_service"
    metrics: list[SimulationMetric] = Field(default_factory=list)
    worst_case_corner: dict[str, Any] = Field(default_factory=dict)
    waveform_refs: list[dict[str, str]] = Field(default_factory=list)
    derived_insights: list[str] = Field(default_factory=list)


class ProviderDispatchRecord(BaseModel):
    provider_dispatch_id: str
    provider_id: str
    adapter_id: str
    dispatch_status: DispatchStatus
    provider_job_id: str | None = None
    dispatched_at: str
    request_preview: dict[str, Any] = Field(default_factory=dict)
    provider_response: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class SimulationCreateResponse(BaseModel):
    request: SimulationRequestRecord
    run: SimulationRun
    result: SimulationResult | None = None
    provider_dispatch: ProviderDispatchRecord | None = None
