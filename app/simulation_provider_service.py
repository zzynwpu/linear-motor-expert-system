from __future__ import annotations

import json
from pathlib import Path

from .simulation_models import SimulationProvider


class SimulationProviderService:
    def __init__(self, providers_dir: Path) -> None:
        self.providers_dir = providers_dir
        self.providers: dict[str, SimulationProvider] = {}
        self._load_providers()

    def _load_providers(self) -> None:
        self.providers = {}
        if not self.providers_dir.exists():
            return

        for path in sorted(self.providers_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            provider = SimulationProvider.model_validate(payload)
            self.providers[provider.provider_id] = provider

    def list_providers(self) -> list[SimulationProvider]:
        return list(self.providers.values())

    def get_provider(self, provider_id: str) -> SimulationProvider:
        provider = self.providers.get(provider_id)
        if provider is None:
            raise KeyError(provider_id)
        return provider


provider_service = SimulationProviderService(Path(__file__).resolve().parent / "simulation_providers")
