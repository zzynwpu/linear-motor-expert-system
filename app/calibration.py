from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .models import (
    AnalysisResult,
    AnalysisSummary,
    DynamicModel,
    HarmonicTerm,
    LookupTablePoint,
    SpectrumPeak,
    SystemConfig,
    ThermalModel,
)
from .rules import evaluate_rules


REQUIRED_COLUMNS = {"position_mm", "sensor_position_mm", "reference_position_mm"}


ELECTROMAGNETIC_TERMS = [
    "推力波动等效误差",
    "齿槽力等效误差",
    "磁场均匀性等效误差",
    "推力常数波动等效误差",
    "气隙变化敏感误差",
    "磁场谐波等效误差",
    "端部效应等效误差",
    "电流纹波等效误差",
    "反电势谐波等效误差",
    "磁性能温漂等效误差",
]


def normalize_measurements(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"输入 CSV 缺少必要列: {sorted(missing)}")

    enriched = df.copy()
    enriched["error_mm"] = enriched["sensor_position_mm"] - enriched["reference_position_mm"]
    if "velocity_mm_s" not in enriched:
        enriched["velocity_mm_s"] = 0.0
    if "temperature_c" not in enriched:
        enriched["temperature_c"] = 20.0
    if "direction" not in enriched:
        direction = np.sign(np.gradient(enriched["position_mm"].to_numpy(dtype=float), edge_order=1))
        direction[direction == 0] = 1.0
        enriched["direction"] = direction
    enriched = enriched.sort_values("position_mm").reset_index(drop=True)
    return enriched


def load_measurements(csv_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    return normalize_measurements(df)


def fit_harmonics(position_mm: np.ndarray, error_um: np.ndarray, config: SystemConfig) -> tuple[np.ndarray, list[HarmonicTerm]]:
    columns = []
    for order in range(1, config.harmonic_count + 1):
        angle = 2.0 * np.pi * order * position_mm / config.pole_pitch_mm
        columns.append(np.sin(angle))
        columns.append(np.cos(angle))

    design = np.column_stack(columns) if columns else np.zeros((len(position_mm), 0))
    if design.size == 0:
        return np.zeros_like(error_um), []

    coeffs, *_ = np.linalg.lstsq(design, error_um, rcond=None)
    fitted = design @ coeffs

    terms: list[HarmonicTerm] = []
    for index in range(config.harmonic_count):
        sin_coeff = float(coeffs[2 * index])
        cos_coeff = float(coeffs[2 * index + 1])
        terms.append(HarmonicTerm(order=index + 1, sin_coeff_um=sin_coeff, cos_coeff_um=cos_coeff))
    return fitted, terms


def fit_dynamic_model(df: pd.DataFrame, residual_um: np.ndarray) -> tuple[np.ndarray, DynamicModel]:
    velocity = df["velocity_mm_s"].to_numpy(dtype=float)
    direction = df["direction"].to_numpy(dtype=float)
    position = df["position_mm"].to_numpy(dtype=float)

    if len(position) > 2:
        accel = np.gradient(velocity, position, edge_order=1)
        accel = np.nan_to_num(accel)
    else:
        accel = np.zeros_like(velocity)

    design = np.column_stack([np.ones(len(df)), velocity, accel, direction])
    coeffs, *_ = np.linalg.lstsq(design, residual_um, rcond=None)
    fitted = design @ coeffs
    model = DynamicModel(
        bias_um=float(coeffs[0]),
        velocity_coeff_um_per_mm_s=float(coeffs[1]),
        accel_coeff_um_per_mm_s2=float(coeffs[2]),
        direction_coeff_um=float(coeffs[3]),
    )
    return fitted, model


def fit_thermal_model(df: pd.DataFrame, residual_um: np.ndarray) -> tuple[np.ndarray, ThermalModel]:
    temperature = df["temperature_c"].to_numpy(dtype=float)
    ref_temp = float(np.mean(temperature))
    delta_t = temperature - ref_temp
    slope = 0.0
    if np.ptp(temperature) > 1e-9:
        slope = float(np.dot(delta_t, residual_um) / max(np.dot(delta_t, delta_t), 1e-9))
    fitted = slope * delta_t
    model = ThermalModel(ref_temperature_c=ref_temp, slope_um_per_c=slope)
    return fitted, model


def build_lookup_table(position_mm: np.ndarray, residual_um: np.ndarray, spacing_mm: float) -> list[LookupTablePoint]:
    start = float(np.min(position_mm))
    stop = float(np.max(position_mm))
    grid = np.arange(start, stop + spacing_mm, spacing_mm)
    binned = np.interp(grid, position_mm, residual_um)
    return [LookupTablePoint(position_mm=float(x), correction_um=float(-y)) for x, y in zip(grid, binned)]


def compute_repeatability(df: pd.DataFrame, residual_um: np.ndarray) -> float:
    temp = df.copy()
    temp["residual_um"] = residual_um
    temp["bucket"] = temp["position_mm"].round(3)
    grouped = temp.groupby("bucket")["residual_um"].std(ddof=0).dropna()
    if grouped.empty:
        return float(np.std(residual_um))
    return float(grouped.mean())


def extract_spectrum_peaks(position_mm: np.ndarray, error_um: np.ndarray, top_n: int = 5) -> list[SpectrumPeak]:
    if len(position_mm) < 8:
        return []

    dx = float(np.median(np.diff(position_mm)))
    if dx <= 0:
        return []

    uniform_grid = np.arange(position_mm.min(), position_mm.max(), dx)
    uniform_error = np.interp(uniform_grid, position_mm, error_um)
    centered = uniform_error - np.mean(uniform_error)

    fft_values = np.fft.rfft(centered)
    freqs = np.fft.rfftfreq(len(uniform_grid), d=dx)
    amplitudes = 2.0 * np.abs(fft_values) / max(len(uniform_grid), 1)

    peaks: list[SpectrumPeak] = []
    for freq, amp in zip(freqs[1:], amplitudes[1:]):
        peaks.append(SpectrumPeak(frequency_cyc_per_mm=float(freq), amplitude_um=float(amp)))

    peaks.sort(key=lambda item: item.amplitude_um, reverse=True)
    return peaks[:top_n]


def analyze_measurements(df: pd.DataFrame, config: SystemConfig | None = None) -> AnalysisResult:
    config = config or SystemConfig()
    df = normalize_measurements(df)
    position_mm = df["position_mm"].to_numpy(dtype=float)
    error_um = df["error_mm"].to_numpy(dtype=float) * 1000.0

    cyclic_um, harmonic_terms = fit_harmonics(position_mm, error_um, config)
    after_cyclic_um = error_um - cyclic_um

    thermal_um, thermal_model = fit_thermal_model(df, after_cyclic_um)
    after_thermal_um = after_cyclic_um - thermal_um

    dynamic_um, dynamic_model = fit_dynamic_model(df, after_thermal_um)
    residual_um = after_thermal_um - dynamic_um

    lookup_table = build_lookup_table(position_mm, residual_um, config.lookup_spacing_mm)
    spectrum_peaks = extract_spectrum_peaks(position_mm, error_um)

    direction_series = df["direction"].to_numpy(dtype=float)
    forward_mask = direction_series >= 0
    reverse_mask = direction_series < 0
    forward_mean = float(np.mean(error_um[forward_mask])) if np.any(forward_mask) else 0.0
    reverse_mean = float(np.mean(error_um[reverse_mask])) if np.any(reverse_mask) else 0.0
    forward_reverse_gap_um = forward_mean - reverse_mean

    temperature_series = df["temperature_c"].to_numpy(dtype=float)
    if np.std(temperature_series) > 1e-9 and np.std(error_um) > 1e-9:
        temperature_correlation = float(np.corrcoef(temperature_series, error_um)[0, 1])
    else:
        temperature_correlation = 0.0

    repeatability_um = compute_repeatability(df, residual_um)
    residual_rmse_um = float(np.sqrt(np.mean(np.square(residual_um))))
    expanded_uncertainty_um = float(
        2.0
        * np.sqrt(
            (repeatability_um / 2.0) ** 2
            + residual_rmse_um**2
            + config.reference_uncertainty_um**2
            + config.environment_uncertainty_um**2
        )
    )

    diagnostics = evaluate_rules(
        config=config,
        harmonics=harmonic_terms,
        spectrum_peaks=spectrum_peaks,
        forward_reverse_gap_um=forward_reverse_gap_um,
        temperature_correlation=temperature_correlation,
        repeatability_um=repeatability_um,
    )

    summary = AnalysisSummary(
        peak_to_peak_um=float(np.ptp(error_um)),
        residual_rmse_um=residual_rmse_um,
        repeatability_um=repeatability_um,
        expanded_uncertainty_um=expanded_uncertainty_um,
    )

    samples = []
    total_comp_um = cyclic_um + thermal_um + dynamic_um
    for x, err, corr, res in zip(position_mm, error_um, total_comp_um, residual_um):
        samples.append(
            {
                "position_mm": float(x),
                "original_error_um": float(err),
                "estimated_correction_um": float(-corr),
                "residual_um": float(res),
            }
        )

    return AnalysisResult(
        config=config,
        summary=summary,
        harmonic_terms=harmonic_terms,
        lookup_table=lookup_table,
        dynamic_model=dynamic_model,
        thermal_model=thermal_model,
        spectrum_peaks=spectrum_peaks,
        diagnostics=diagnostics,
        samples=samples,
    )


def analyze_csv(csv_path: str | Path, config: SystemConfig | None = None) -> AnalysisResult:
    df = load_measurements(csv_path)
    return analyze_measurements(df, config=config)


def save_result_json(result: AnalysisResult, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def _electromagnetic_position_equivalents(params: dict[str, float]) -> dict[str, float]:
    thermal_delta_c = abs(float(params.get("thermal_delta_c", 2.0)))
    force_ripple_percent = abs(float(params.get("force_ripple_percent", 0.0)))
    force_ripple_pp_n = abs(float(params.get("force_ripple_pp_n", 0.0)))
    cogging_force_pp_n = abs(float(params.get("cogging_force_pp_n", 0.0)))
    magnetic_field_uniformity_percent = abs(float(params.get("magnetic_field_uniformity_percent", 0.0)))
    thrust_constant_variation_percent = abs(float(params.get("thrust_constant_variation_percent", 0.0)))
    air_gap_variation_um = abs(float(params.get("air_gap_variation_um", 0.0)))
    magnetic_harmonic_percent = abs(float(params.get("magnetic_harmonic_percent", 0.0)))
    end_effect_percent = abs(float(params.get("end_effect_percent", 0.0)))
    current_ripple_percent = abs(float(params.get("current_ripple_percent", 0.0)))
    back_emf_harmonic_percent = abs(float(params.get("back_emf_harmonic_percent", 0.0)))
    magnetic_temp_drift_percent_per_c = abs(float(params.get("magnetic_temp_drift_percent_per_c", 0.0)))

    return {
        "推力波动等效误差": 0.6 * force_ripple_percent + 0.8 * force_ripple_pp_n,
        "齿槽力等效误差": 0.9 * cogging_force_pp_n,
        "磁场均匀性等效误差": 0.8 * magnetic_field_uniformity_percent,
        "推力常数波动等效误差": 0.7 * thrust_constant_variation_percent,
        "气隙变化敏感误差": 0.25 * air_gap_variation_um,
        "磁场谐波等效误差": 0.7 * magnetic_harmonic_percent,
        "端部效应等效误差": 0.5 * end_effect_percent,
        "电流纹波等效误差": 0.5 * current_ripple_percent,
        "反电势谐波等效误差": 0.4 * back_emf_harmonic_percent,
        "磁性能温漂等效误差": 0.6 * magnetic_temp_drift_percent_per_c * thermal_delta_c,
    }


def estimate_error_budget(params: dict[str, float]) -> dict[str, Any]:
    stroke_mm = max(float(params.get("stroke_mm", 1000.0)), 1e-6)
    pole_pitch_mm = max(float(params.get("pole_pitch_mm", 2.0)), 1e-6)
    motor_pole_pitch_mm = max(float(params.get("motor_pole_pitch_mm", pole_pitch_mm)), 1e-6)
    scale_pitch_accuracy_um_per_m = abs(float(params.get("scale_pitch_accuracy_um_per_m", 10.0)))
    scale_cyclic_um = abs(float(params.get("scale_cyclic_um", 5.0)))
    interpolation_error_um = abs(float(params.get("interpolation_error_um", 2.0)))
    guide_straightness_um = abs(float(params.get("guide_straightness_um", 8.0)))
    mounting_flatness_um = abs(float(params.get("mounting_flatness_um", 6.0)))
    assembly_parallelism_um = abs(float(params.get("assembly_parallelism_um", 5.0)))
    abbe_offset_mm = abs(float(params.get("abbe_offset_mm", 30.0)))
    angular_error_arcsec = abs(float(params.get("angular_error_arcsec", 20.0)))
    thermal_delta_c = abs(float(params.get("thermal_delta_c", 2.0)))
    thermal_expansion_ppm_c = abs(float(params.get("thermal_expansion_ppm_c", 11.5)))
    servo_following_um = abs(float(params.get("servo_following_um", 3.0)))
    measurement_uncertainty_um = abs(float(params.get("measurement_uncertainty_um", 1.5)))

    angular_error_rad = angular_error_arcsec * np.pi / (180.0 * 3600.0)

    base_contributor_map = {
        "磁栅累计节距误差": scale_pitch_accuracy_um_per_m * stroke_mm / 1000.0,
        "2 mm 周期误差": scale_cyclic_um + interpolation_error_um,
        "导轨直线度": guide_straightness_um,
        "安装平面度": mounting_flatness_um,
        "装配平行度": assembly_parallelism_um,
        "Abbe 误差": abbe_offset_mm * angular_error_rad * 1000.0,
        "热伸缩误差": stroke_mm * thermal_delta_c * thermal_expansion_ppm_c / 1000.0,
        "伺服跟随误差": servo_following_um,
        "测量链不确定度": measurement_uncertainty_um,
    }
    electromagnetic_contributor_map = _electromagnetic_position_equivalents(params)
    contributor_map = {**base_contributor_map, **electromagnetic_contributor_map}

    contributors = [
        {"name": name, "estimate_um": float(value)}
        for name, value in sorted(contributor_map.items(), key=lambda item: item[1], reverse=True)
    ]

    values = np.array([item["estimate_um"] for item in contributors], dtype=float)
    worst_case_um = float(np.sum(values))
    rss_um = float(np.sqrt(np.sum(np.square(values))))

    geometry_total_um = float(
        contributor_map["导轨直线度"]
        + contributor_map["安装平面度"]
        + contributor_map["装配平行度"]
        + contributor_map["Abbe 误差"]
    )
    sensor_total_um = float(contributor_map["磁栅累计节距误差"] + contributor_map["2 mm 周期误差"])
    electromagnetic_total_um = float(sum(contributor_map[name] for name in ELECTROMAGNETIC_TERMS))
    thermal_total_um = float(contributor_map["热伸缩误差"] + contributor_map["磁性能温漂等效误差"])
    control_total_um = float(contributor_map["伺服跟随误差"] + contributor_map["电流纹波等效误差"])
    measurement_total_um = float(contributor_map["测量链不确定度"])

    diagnostics: list[dict[str, str]] = []
    dominant_name = contributors[0]["name"] if contributors else ""
    dominant_value = contributors[0]["estimate_um"] if contributors else 0.0
    if dominant_value > 0.35 * max(worst_case_um, 1e-6):
        diagnostics.append(
            {
                "severity": "high",
                "message": f"当前主导误差为“{dominant_name}”，建议优先压缩该项公差或增加专门补偿。",
            }
        )

    if contributor_map["2 mm 周期误差"] >= 5.0:
        diagnostics.append(
            {
                "severity": "medium",
                "message": "2 mm 磁极距相关周期误差占比较高，后续若实测可优先做周期谐波补偿。",
            }
        )

    if geometry_total_um >= 0.4 * max(worst_case_um, 1e-6):
        diagnostics.append(
            {
                "severity": "medium",
                "message": "几何装配误差占比较大，建议优先优化基面、导轨安装和测量基准布局。",
            }
        )

    if contributor_map["热伸缩误差"] >= 0.15 * max(worst_case_um, 1e-6):
        diagnostics.append(
            {
                "severity": "medium",
                "message": "热误差不可忽略，建议把温差控制和温漂补偿纳入方案。",
            }
        )

    if electromagnetic_total_um >= 0.22 * max(worst_case_um, 1e-6):
        diagnostics.append(
            {
                "severity": "high" if electromagnetic_total_um >= geometry_total_um else "medium",
                "message": "电磁误差贡献已不可忽略，建议把推力波动、齿槽力、磁场质量和气隙变化纳入正式建模。",
            }
        )

    if contributor_map["齿槽力等效误差"] >= 2.0 or contributor_map["推力波动等效误差"] >= 3.0:
        diagnostics.append(
            {
                "severity": "medium",
                "message": "低速平稳性存在风险，建议重点关注齿槽力、推力波动以及速度环参数匹配。",
            }
        )

    if contributor_map["磁场均匀性等效误差"] >= 2.0 or contributor_map["磁场谐波等效误差"] >= 2.0:
        diagnostics.append(
            {
                "severity": "medium",
                "message": "磁场质量可能成为周期残差的重要来源，后续实测时应与传感器周期误差分开判别。",
            }
        )

    if contributor_map["端部效应等效误差"] >= 2.0:
        diagnostics.append(
            {
                "severity": "medium",
                "message": "行程端部误差风险上升，建议在端部保留裕量并单独评估端部效应。",
            }
        )

    if not diagnostics:
        diagnostics.append(
            {
                "severity": "info",
                "message": "当前公差预算较均衡，可在拿到实测数据后进一步用标定曲线细化补偿表。",
            }
        )

    positions = np.linspace(0.0, stroke_mm, 600)
    normalized = positions / stroke_mm
    estimated_curve_um = (
        contributor_map["磁栅累计节距误差"] * normalized
        + contributor_map["2 mm 周期误差"] * np.sin(2.0 * np.pi * positions / pole_pitch_mm)
        + 0.7 * contributor_map["导轨直线度"] * np.sin(2.0 * np.pi * normalized)
        + 0.5 * contributor_map["安装平面度"] * np.cos(np.pi * normalized)
        + contributor_map["装配平行度"] * (normalized - 0.5)
        + contributor_map["Abbe 误差"] * np.sin(np.pi * normalized)
        + contributor_map["热伸缩误差"] * (normalized - 0.5)
        + contributor_map["推力波动等效误差"] * np.sin(2.0 * np.pi * positions / motor_pole_pitch_mm)
        + contributor_map["齿槽力等效误差"] * np.cos(4.0 * np.pi * positions / motor_pole_pitch_mm)
        + contributor_map["磁场均匀性等效误差"] * np.sin(np.pi * normalized)
        + contributor_map["气隙变化敏感误差"] * np.cos(2.0 * np.pi * normalized)
        + contributor_map["端部效应等效误差"] * (np.exp(-5.0 * normalized) + np.exp(-5.0 * (1.0 - normalized)))
    )

    category_totals = {
        "sensor_um": sensor_total_um,
        "geometry_um": geometry_total_um,
        "electromagnetic_um": electromagnetic_total_um,
        "thermal_um": thermal_total_um,
        "control_um": control_total_um,
        "measurement_um": measurement_total_um,
    }
    denominator = max(worst_case_um, 1e-6)
    category_ratios = {
        key.replace("_um", "_ratio_percent"): float(value / denominator * 100.0)
        for key, value in category_totals.items()
    }

    samples = [
        {
            "position_mm": float(x),
            "estimated_error_um": float(y),
            "upper_bound_um": float(y + rss_um),
            "lower_bound_um": float(y - rss_um),
        }
        for x, y in zip(positions, estimated_curve_um)
    ]

    return {
        "mode": "tolerance_budget_v2",
        "inputs": {key: float(value) for key, value in params.items()},
        "summary": {
            "worst_case_um": worst_case_um,
            "rss_um": rss_um,
            "dominant_error": dominant_name,
            "electromagnetic_um": electromagnetic_total_um,
            "electromagnetic_ratio_percent": category_ratios["electromagnetic_ratio_percent"],
            "geometry_ratio_percent": category_ratios["geometry_ratio_percent"],
            "sensor_ratio_percent": category_ratios["sensor_ratio_percent"],
            "thermal_ratio_percent": category_ratios["thermal_ratio_percent"],
        },
        "contributors": contributors,
        "category_totals": category_totals,
        "category_ratios": category_ratios,
        "diagnostics": diagnostics,
        "samples": samples,
    }
