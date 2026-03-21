from __future__ import annotations

from typing import Iterable

from .models import DiagnosticItem, HarmonicTerm, SpectrumPeak, SystemConfig


def evaluate_rules(
    config: SystemConfig,
    harmonics: Iterable[HarmonicTerm],
    spectrum_peaks: Iterable[SpectrumPeak],
    forward_reverse_gap_um: float,
    temperature_correlation: float,
    repeatability_um: float,
) -> list[DiagnosticItem]:
    diagnostics: list[DiagnosticItem] = []
    harmonic_list = list(harmonics)
    peak_list = list(spectrum_peaks)

    first_order = next((h for h in harmonic_list if h.order == 1), None)
    second_order = next((h for h in harmonic_list if h.order == 2), None)

    if first_order and first_order.amplitude_um >= config.cyclic_alarm_um:
        diagnostics.append(
            DiagnosticItem(
                code="CYCLIC_2MM",
                severity="high",
                message=(
                    "检测到与 2 mm 磁极距同步的显著周期误差，"
                    "优先检查磁头安装高度、相位正交性、幅值平衡和细分链路线性。"
                ),
            )
        )

    if first_order and second_order and second_order.amplitude_um > 0.3 * max(first_order.amplitude_um, 1e-6):
        diagnostics.append(
            DiagnosticItem(
                code="HARMONIC_DISTORTION",
                severity="medium",
                message="二次谐波占比偏高，可能存在磁场畸变、细分非线性或安装偏摆。",
            )
        )

    dominant_pitch_peak = next(
        (p for p in peak_list if abs(p.frequency_cyc_per_mm - 0.5) < 0.05 and p.amplitude_um >= config.cyclic_alarm_um),
        None,
    )
    if dominant_pitch_peak:
        diagnostics.append(
            DiagnosticItem(
                code="FFT_PITCH_PEAK",
                severity="medium",
                message="频谱在 0.5 cycle/mm 附近存在明显峰值，符合磁极距相关误差特征。",
            )
        )

    if abs(forward_reverse_gap_um) >= config.cyclic_alarm_um:
        diagnostics.append(
            DiagnosticItem(
                code="BIDIRECTIONAL_GAP",
                severity="medium",
                message="正反向误差均值差较大，建议增加双向补偿并检查摩擦、反向死区和结构弹性。",
            )
        )

    if abs(temperature_correlation) >= 0.6:
        diagnostics.append(
            DiagnosticItem(
                code="THERMAL_SENSITIVITY",
                severity="medium",
                message="误差与温度相关性较强，建议建立温漂补偿并加强环境控制。",
            )
        )

    if repeatability_um >= config.repeatability_alarm_um:
        diagnostics.append(
            DiagnosticItem(
                code="LOW_REPEATABILITY",
                severity="high",
                message="重复性偏差较大，当前标定结果可信度下降，应先排查测量系统、振动和装配松动。",
            )
        )

    if not diagnostics:
        diagnostics.append(
            DiagnosticItem(
                code="NO_MAJOR_ISSUE",
                severity="info",
                message="未发现超过阈值的显著异常，可继续通过补偿表提升绝对定位精度。",
            )
        )

    return diagnostics

