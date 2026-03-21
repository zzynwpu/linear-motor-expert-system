from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class SystemConfig:
    pole_pitch_mm: float = 2.0
    harmonic_count: int = 5
    lookup_spacing_mm: float = 5.0
    reference_uncertainty_um: float = 1.0
    environment_uncertainty_um: float = 0.5
    cyclic_alarm_um: float = 5.0
    repeatability_alarm_um: float = 3.0


@dataclass
class HarmonicTerm:
    order: int
    sin_coeff_um: float
    cos_coeff_um: float

    @property
    def amplitude_um(self) -> float:
        return (self.sin_coeff_um ** 2 + self.cos_coeff_um ** 2) ** 0.5


@dataclass
class DynamicModel:
    bias_um: float = 0.0
    velocity_coeff_um_per_mm_s: float = 0.0
    accel_coeff_um_per_mm_s2: float = 0.0
    direction_coeff_um: float = 0.0


@dataclass
class ThermalModel:
    ref_temperature_c: float = 20.0
    slope_um_per_c: float = 0.0


@dataclass
class LookupTablePoint:
    position_mm: float
    correction_um: float


@dataclass
class DiagnosticItem:
    code: str
    severity: str
    message: str


@dataclass
class SpectrumPeak:
    frequency_cyc_per_mm: float
    amplitude_um: float


@dataclass
class AnalysisSummary:
    peak_to_peak_um: float
    residual_rmse_um: float
    repeatability_um: float
    expanded_uncertainty_um: float


@dataclass
class AnalysisResult:
    config: SystemConfig
    summary: AnalysisSummary
    harmonic_terms: list[HarmonicTerm] = field(default_factory=list)
    lookup_table: list[LookupTablePoint] = field(default_factory=list)
    dynamic_model: DynamicModel = field(default_factory=DynamicModel)
    thermal_model: ThermalModel = field(default_factory=ThermalModel)
    spectrum_peaks: list[SpectrumPeak] = field(default_factory=list)
    diagnostics: list[DiagnosticItem] = field(default_factory=list)
    samples: list[dict[str, float]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

