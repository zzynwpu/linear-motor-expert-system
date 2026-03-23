from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from .remote_ngspice_stub_models import RemoteNgspiceJobCreate
from .remote_ngspice_stub_service import remote_ngspice_stub_service
from .simulation_models import ProviderDispatchRecord, SimulationRequestRecord, SimulationTemplate


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class BaseProviderAdapter:
    adapter_id = "base"
    provider_id = ""

    def dispatch(self, request: SimulationRequestRecord, template: SimulationTemplate) -> ProviderDispatchRecord:
        raise NotImplementedError


class RemoteNgspiceStubAdapter(BaseProviderAdapter):
    adapter_id = "remote_ngspice_stub_adapter"
    provider_id = "remote_ngspice_service"

    def dispatch(self, request: SimulationRequestRecord, template: SimulationTemplate) -> ProviderDispatchRecord:
        provider_payload = RemoteNgspiceJobCreate(
            simulation_request_id=request.simulation_request_id,
            template_id=template.template_id,
            tool=request.selected_tool,
            project_context=request.project_context,
            parameter_bindings=request.parameter_bindings,
            input_artifacts=request.input_artifacts,
            sweeps=request.sweeps,
            measurements=request.measurements,
            pass_criteria=request.pass_criteria,
            callback_url=None,
        )
        job = remote_ngspice_stub_service.create_job(provider_payload)
        return ProviderDispatchRecord(
            provider_dispatch_id=f"dispatch_{uuid4().hex[:10]}",
            provider_id=self.provider_id,
            adapter_id=self.adapter_id,
            dispatch_status="completed" if job.status == "completed" else "queued",
            provider_job_id=job.job_id,
            dispatched_at=_now_iso(),
            request_preview=provider_payload.model_dump(mode="json"),
            provider_response=job.model_dump(mode="json"),
            notes=[
                "Stub adapter dispatched the request in-process to the remote_ngspice stub service.",
                "Replace this adapter's internals with a real HTTP client when the external provider is ready.",
            ],
        )


class NullProviderAdapter(BaseProviderAdapter):
    adapter_id = "null_adapter"

    def dispatch(self, request: SimulationRequestRecord, template: SimulationTemplate) -> ProviderDispatchRecord:
        provider_id = request.provider_id or "unknown_provider"
        return ProviderDispatchRecord(
            provider_dispatch_id=f"dispatch_{uuid4().hex[:10]}",
            provider_id=provider_id,
            adapter_id=self.adapter_id,
            dispatch_status="prepared",
            provider_job_id=None,
            dispatched_at=_now_iso(),
            request_preview={
                "simulation_request_id": request.simulation_request_id,
                "template_id": template.template_id,
                "selected_tool": request.selected_tool,
            },
            provider_response={},
            notes=[
                "No concrete provider adapter is implemented for this provider yet.",
                "Keep this dispatch record as a placeholder until a real adapter is added.",
            ],
        )


ADAPTERS: dict[str, BaseProviderAdapter] = {
    RemoteNgspiceStubAdapter.provider_id: RemoteNgspiceStubAdapter(),
}
DEFAULT_ADAPTER = NullProviderAdapter()


def get_provider_adapter(provider_id: str | None) -> BaseProviderAdapter:
    if not provider_id:
        return DEFAULT_ADAPTER
    return ADAPTERS.get(provider_id, DEFAULT_ADAPTER)
