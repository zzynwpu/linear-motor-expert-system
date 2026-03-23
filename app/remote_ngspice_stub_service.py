from __future__ import annotations

from .remote_ngspice_stub_models import (
    RemoteNgspiceArtifactBundle,
    RemoteNgspiceCancelResponse,
    RemoteNgspiceJobCreate,
    RemoteNgspiceJobRecord,
    RemoteNgspiceJobResult,
    RemoteNgspiceProgress,
    make_job_id,
    now_iso,
)
from .simulation_models import SimulationMetric


class RemoteNgspiceStubService:
    def __init__(self) -> None:
        self.jobs: dict[str, RemoteNgspiceJobRecord] = {}
        self.results: dict[str, RemoteNgspiceJobResult] = {}

    def create_job(self, payload: RemoteNgspiceJobCreate) -> RemoteNgspiceJobRecord:
        job_id = make_job_id()
        total_sweeps = self._estimate_sweeps(payload)
        accepted_at = now_iso()
        job = RemoteNgspiceJobRecord(
            job_id=job_id,
            status="completed",
            template_id=payload.template_id,
            tool=payload.tool,
            accepted_at=accepted_at,
            started_at=accepted_at,
            progress=RemoteNgspiceProgress(completed_sweeps=total_sweeps, total_sweeps=total_sweeps),
        )
        self.jobs[job_id] = job
        self.results[job_id] = self._build_result(job_id, payload)
        return job

    def get_job(self, job_id: str) -> RemoteNgspiceJobRecord:
        job = self.jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    def get_result(self, job_id: str) -> RemoteNgspiceJobResult:
        result = self.results.get(job_id)
        if result is None:
            raise KeyError(job_id)
        return result

    def cancel_job(self, job_id: str) -> RemoteNgspiceCancelResponse:
        job = self.get_job(job_id)
        job.status = "cancelled"
        self.jobs[job_id] = job
        return RemoteNgspiceCancelResponse(job_id=job_id, status="cancelled")

    @staticmethod
    def _estimate_sweeps(payload: RemoteNgspiceJobCreate) -> int:
        total = 1
        for sweep in payload.sweeps:
            total *= max(1, len(sweep.values))
        return total

    @staticmethod
    def _build_result(job_id: str, payload: RemoteNgspiceJobCreate) -> RemoteNgspiceJobResult:
        metrics = []
        criteria_by_metric = {item.metric: item for item in payload.pass_criteria}
        for name in payload.measurements:
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

        bundle = RemoteNgspiceArtifactBundle(
            log_path=f"/remote_jobs/{job_id}/run.log",
            waveforms=[f"/remote_jobs/{job_id}/{name}.csv" for name in payload.measurements[:2]],
            raw_result_path=f"/remote_jobs/{job_id}/result.json",
        )
        return RemoteNgspiceJobResult(
            job_id=job_id,
            status="completed",
            summary="Remote NGSpice stub accepted the job and produced a placeholder result. Replace this stub with real job execution when the provider backend is ready.",
            metrics=metrics,
            worst_case_corner={},
            artifacts=bundle,
        )


remote_ngspice_stub_service = RemoteNgspiceStubService()
