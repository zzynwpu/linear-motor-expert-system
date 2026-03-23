from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .provider_adapters import get_provider_adapter
from .simulation_models import (
    PassCriterion,
    ParameterSweep,
    ProviderDispatchRecord,
    SimulationCreateResponse,
    SimulationMetric,
    SimulationRequestCreate,
    SimulationRequestRecord,
    SimulationResult,
    SimulationRun,
    SimulationTemplate,
)
from .simulation_provider_service import provider_service


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class SimulationService:
    def __init__(self, templates_dir: Path) -> None:
        self.templates_dir = templates_dir
        self.templates: dict[str, SimulationTemplate] = {}
        self.requests: dict[str, SimulationRequestRecord] = {}
        self.runs: dict[str, SimulationRun] = {}
        self.results: dict[str, SimulationResult] = {}
        self.dispatches: dict[str, ProviderDispatchRecord] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        self.templates = {}
        if not self.templates_dir.exists():
            return

        for path in sorted(self.templates_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            template = SimulationTemplate.model_validate(payload)
            self.templates[template.template_id] = template

    def list_templates(self) -> list[SimulationTemplate]:
        return list(self.templates.values())

    def get_template(self, template_id: str) -> SimulationTemplate:
        template = self.templates.get(template_id)
        if template is None:
            raise KeyError(template_id)
        return template

    def get_dispatch(self, dispatch_id: str) -> ProviderDispatchRecord:
        dispatch = self.dispatches.get(dispatch_id)
        if dispatch is None:
            raise KeyError(dispatch_id)
        return dispatch

    def create_request(self, payload: SimulationRequestCreate) -> SimulationCreateResponse:
        template = self.get_template(payload.template_id)
        provider_id = payload.provider_id or self._default_provider_id(template)
        provider = provider_service.get_provider(provider_id) if provider_id else None
        request_id = f"simreq_{uuid4().hex[:10]}"
        run_id = f"simrun_{uuid4().hex[:10]}"
        created_at = _now_iso()

        effective_sweeps = payload.sweeps or template.default_sweeps
        effective_measurements = payload.measurements or template.key_measurements
        effective_criteria = payload.pass_criteria or template.pass_criteria
        effective_target = provider.execution_target if provider else payload.execution_target

        request_record = SimulationRequestRecord(
            simulation_request_id=request_id,
            created_at=created_at,
            task_type=payload.task_type,
            motor_type=payload.motor_type,
            simulation_level=payload.simulation_level,
            simulation_goal=payload.simulation_goal,
            selected_tool=payload.selected_tool,
            template_id=payload.template_id,
            provider_id=provider_id,
            execution_target=effective_target,
            project_context=payload.project_context,
            input_artifacts=payload.input_artifacts,
            parameter_bindings=payload.parameter_bindings,
            sweeps=effective_sweeps,
            measurements=effective_measurements,
            pass_criteria=effective_criteria,
            priority=payload.priority,
            auto_stub_result=payload.auto_stub_result,
        )
        self.requests[request_id] = request_record

        sweep_instances = max(1, self._estimate_sweep_instances(effective_sweeps))
        run = SimulationRun(
            simulation_run_id=run_id,
            simulation_request_id=request_id,
            tool=payload.selected_tool,
            provider_id=provider_id,
            execution_target=effective_target,
            status="queued",
            started_at=created_at,
            execution_mode="remote" if effective_target in {"browser", "remote_service", "agent_tool"} else "batch",
            template_id=payload.template_id,
            sweep_instances=sweep_instances,
        )
        self.runs[run_id] = run

        dispatch = self._dispatch_to_provider(request_record, template)
        if dispatch is not None:
            self.dispatches[dispatch.provider_dispatch_id] = dispatch

        result = None
        if payload.auto_stub_result:
            result = self._build_stub_result(
                run_id=run_id,
                template=template,
                measurements=effective_measurements,
                criteria=effective_criteria,
                provider_id=provider_id,
                execution_target=effective_target,
                dispatch=dispatch,
            )
            self.results[result.simulation_result_id] = result
            run.status = "completed"
            run.ended_at = _now_iso()
            run.runtime_seconds = 0
            self.runs[run_id] = run

        return SimulationCreateResponse(request=request_record, run=run, result=result, provider_dispatch=dispatch)

    def get_run(self, run_id: str) -> SimulationRun:
        run = self.runs.get(run_id)
        if run is None:
            raise KeyError(run_id)
        return run

    def get_result(self, result_id: str) -> SimulationResult:
        result = self.results.get(result_id)
        if result is None:
            raise KeyError(result_id)
        return result

    def _dispatch_to_provider(self, request: SimulationRequestRecord, template: SimulationTemplate) -> ProviderDispatchRecord | None:
        adapter = get_provider_adapter(request.provider_id)
        return adapter.dispatch(request, template)

    @staticmethod
    def _estimate_sweep_instances(sweeps: list[ParameterSweep]) -> int:
        total = 1
        for sweep in sweeps:
            count = max(1, len(sweep.values))
            total *= count
        return total

    @staticmethod
    def _default_provider_id(template: SimulationTemplate) -> str | None:
        return template.recommended_provider_ids[0] if template.recommended_provider_ids else None

    @staticmethod
    def _build_stub_result(
        run_id: str,
        template: SimulationTemplate,
        measurements: list[str],
        criteria: list[PassCriterion],
        provider_id: str | None,
        execution_target: str,
        dispatch: ProviderDispatchRecord | None,
    ) -> SimulationResult:
        metrics: list[SimulationMetric] = []
        criteria_by_metric = {item.metric: item for item in criteria}

        for name in measurements:
            criterion = criteria_by_metric.get(name)
            metrics.append(
                SimulationMetric(
                    name=name,
                    value=None,
                    unit=criterion.unit if criterion else None,
                    limit=criterion.value if criterion else None,
                    judgement="unknown",
                )
            )

        provider_note = provider_id or "no_provider_selected"
        dispatch_note = dispatch.provider_job_id if dispatch and dispatch.provider_job_id else "no_provider_job"
        return SimulationResult(
            simulation_result_id=f"simres_{uuid4().hex[:10]}",
            simulation_run_id=run_id,
            overall_status="inconclusive",
            summary="Stub execution only. A remote/web simulation adapter has not been connected to real external execution yet, so this result is a placeholder for the orchestration flow.",
            provider_id=provider_id,
            execution_target=execution_target,
            metrics=metrics,
            worst_case_corner={},
            waveform_refs=[],
            derived_insights=[
                f"Template '{template.template_id}' was resolved successfully.",
                f"Provider routing target: '{provider_note}'.",
                f"Provider job reference: '{dispatch_note}'.",
                "Replace the stub adapter internals with a real HTTP client when the remote provider is ready.",
            ],
        )


simulation_service = SimulationService(Path(__file__).resolve().parent / "simulation_templates")
