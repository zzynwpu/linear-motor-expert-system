from __future__ import annotations

import io
import json

import pandas as pd
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from .agent_api import router as agent_router
from .calibration import analyze_measurements, estimate_error_budget
from .datasheet_ingestion_api import router as datasheet_ingestion_router
from .meeting_api import router as meeting_router
from .models import SystemConfig
from .selection_api import router as selection_router
from .supplier_api import router as supplier_router


app = FastAPI(title="Engineering Workbench")
app.include_router(selection_router)
app.include_router(supplier_router)
app.include_router(datasheet_ingestion_router)
app.include_router(agent_router)
app.include_router(meeting_router)


DEFAULT_TOLERANCE_INPUTS = {
    "stroke_mm": 1000.0,
    "pole_pitch_mm": 2.0,
    "scale_pitch_accuracy_um_per_m": 10.0,
    "scale_cyclic_um": 5.0,
    "interpolation_error_um": 2.0,
    "guide_straightness_um": 8.0,
    "mounting_flatness_um": 6.0,
    "assembly_parallelism_um": 5.0,
    "abbe_offset_mm": 30.0,
    "angular_error_arcsec": 20.0,
    "thermal_delta_c": 2.0,
    "thermal_expansion_ppm_c": 11.5,
    "servo_following_um": 3.0,
    "measurement_uncertainty_um": 1.5,
    "force_ripple_percent": 3.0,
    "force_ripple_pp_n": 8.0,
    "cogging_force_pp_n": 4.0,
    "magnetic_field_uniformity_percent": 2.0,
    "thrust_constant_variation_percent": 2.0,
    "air_gap_variation_um": 12.0,
    "motor_pole_pitch_mm": 24.0,
    "magnetic_harmonic_percent": 1.5,
    "end_effect_percent": 2.0,
    "current_ripple_percent": 2.0,
    "back_emf_harmonic_percent": 1.5,
    "magnetic_temp_drift_percent_per_c": 0.2,
}


MANUAL_SECTIONS = [
    {
        "title": "如何使用这个 V2 页面",
        "items": [
            ("适用阶段", "这个页面适用于运动精度的方案估算和标定分析，重点支持直线电机系统的误差预算。"),
            ("V2 升级点", "相比旧版，V2 已正式纳入推力波动、齿槽力、磁场质量、气隙变化和端部效应。"),
            ("结果定位", "结果用于方案阶段筛查主导误差，不等同于激光干涉仪最终标定值，但更接近工程真实风险。"),
        ],
    },
    {
        "title": "如何理解 V2 结果",
        "items": [
            ("最坏值合成", "各误差按最不利方向直接叠加，结果偏保守。"),
            ("RSS 合成", "按均方根方式合成，更接近统计意义下的综合误差。"),
            ("电磁误差贡献", "反映推力波动、齿槽力、磁场均匀性和气隙变化对综合误差的影响程度。"),
            ("低速平稳性风险", "若齿槽力或推力波动较高，低速匀速、启停和小位移跟随容易恶化。"),
        ],
    },
    {
        "title": "参数填写建议",
        "items": [
            ("基础参数", "优先用规格书和图纸公差填写，用于构建几何、传感和热误差预算。"),
            ("高级电磁参数", "如果没有完整实测，可先填保守经验值；后续用样机测试再修正。"),
            ("CSV 标定模式", "拿到激光干涉仪或参考尺数据后，再进入 CSV 模式做谐波拟合和残差分析。"),
        ],
    },
]


PARAMETER_GUIDE = [
    ("行程 mm", "100 ~ 3000", "机构有效行程", "行程越长，累计节距误差和热误差越明显"),
    ("磁极距 mm", "常见 2", "按磁栅尺规格填写", "决定传感器周期误差频率"),
    ("磁栅累计节距误差 um/m", "5 ~ 30", "规格书", "主导长行程绝对定位误差"),
    ("磁栅周期误差 um", "1 ~ 10", "规格书或实测", "会形成 2 mm 相关周期残差"),
    ("导轨直线度 um", "2 ~ 20", "导轨等级或实测", "几何误差主导时应优先优化"),
    ("Abbe 偏置 mm", "5 ~ 80", "按结构基准填写", "会放大角度误差影响"),
    ("推力波动率 %", "1 ~ 8", "样机测试或经验值", "影响低速平稳性和动态误差"),
    ("齿槽力峰峰值 N", "1 ~ 8", "样机测试或估算", "会引入低速周期误差"),
    ("磁场均匀性 %", "0.5 ~ 5", "磁场检测或经验值", "偏大时会放大电磁周期误差"),
    ("气隙变化 um", "5 ~ 30", "装调实测", "会导致推力不均匀和灵敏度波动"),
    ("电机极距 mm", "8 ~ 40", "电机规格", "决定电磁周期误差频率"),
    ("端部效应 %", "0.5 ~ 5", "经验值或仿真", "行程端部误差更容易放大"),
]


def _svg_polyline(points: list[tuple[float, float]], width: int = 920, height: int = 250, stroke: str = "#0f766e") -> str:
    if not points:
        return ""

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    x_span = max(max_x - min_x, 1e-9)
    y_span = max(max_y - min_y, 1e-9)

    svg_points = []
    for x, y in points:
        sx = 24 + (x - min_x) / x_span * (width - 48)
        sy = height - 24 - (y - min_y) / y_span * (height - 48)
        svg_points.append(f"{sx:.2f},{sy:.2f}")

    axis_y = height - 24 - (0 - min_y) / y_span * (height - 48) if min_y <= 0 <= max_y else height - 24
    return f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img" aria-label="误差曲线">
      <rect x="0" y="0" width="{width}" height="{height}" fill="#f8fafc" rx="12"></rect>
      <line x1="24" y1="{axis_y:.2f}" x2="{width - 24}" y2="{axis_y:.2f}" stroke="#cbd5e1" stroke-width="1"></line>
      <polyline fill="none" stroke="{stroke}" stroke-width="2" points="{' '.join(svg_points)}"></polyline>
    </svg>
    """


def _render_manual_blocks() -> str:
    blocks = []
    for section in MANUAL_SECTIONS:
        rows = "".join(f"<tr><td>{name}</td><td>{description}</td></tr>" for name, description in section["items"])
        blocks.append(
            f"""
            <section class="manual-block">
              <h3>{section['title']}</h3>
              <table>
                <tbody>{rows}</tbody>
              </table>
            </section>
            """
        )
    return "".join(blocks)


def _render_parameter_table() -> str:
    rows = "".join(
        f"<tr><td>{name}</td><td>{typical}</td><td>{source}</td><td>{risk}</td></tr>"
        for name, typical, source, risk in PARAMETER_GUIDE
    )
    return f"""
    <section class="manual-block wide">
      <h3>关键参数速查表</h3>
      <table>
        <thead><tr><th>参数</th><th>典型范围</th><th>推荐来源</th><th>偏大时的影响</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """


def _render_shell(body: str, page_title: str = "电机系统运动精度估算与校正智能体", hero_note: str = "这个 legacy 页面用于 V2 运动精度误差预算和 CSV 标定分析，当前主首页仍是选型工作台。") -> HTMLResponse:
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{page_title}</title>
      <style>
        :root {{
          --bg: #f3f4f6;
          --panel: #ffffff;
          --ink: #111827;
          --subtle: #475569;
          --accent: #0f766e;
          --line: #dbe3ea;
          --soft: #f8fafc;
        }}
        body {{
          margin: 0;
          font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
          background: radial-gradient(circle at top right, rgba(15, 118, 110, 0.16), transparent 26%), linear-gradient(180deg, #eef6f4 0%, var(--bg) 100%);
          color: var(--ink);
        }}
        main {{ max-width: 1180px; margin: 0 auto; padding: 28px 20px 48px; }}
        .hero {{ margin-bottom: 20px; }}
        .hero h1 {{ margin: 0 0 10px; font-size: 34px; }}
        .hero p {{ margin: 0; color: var(--subtle); }}
        .nav {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }}
        .nav a, .shortcut {{ display: inline-block; padding: 10px 14px; border-radius: 999px; border: 1px solid var(--line); text-decoration: none; color: var(--ink); background: rgba(255,255,255,0.85); font-size: 14px; }}
        .shortcut.primary {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
        .panel {{ background: var(--panel); border: 1px solid rgba(219, 227, 234, 0.9); border-radius: 18px; padding: 20px; box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06); margin-bottom: 18px; }}
        .panel h2 {{ margin-top: 0; margin-bottom: 8px; }}
        .muted {{ color: var(--subtle); margin: 0 0 14px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }}
        .metric {{ background: var(--soft); border-radius: 14px; padding: 14px; }}
        .metric strong {{ display: block; font-size: 24px; color: var(--accent); margin-top: 6px; }}
        form {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; align-items: end; }}
        label {{ display: block; font-size: 14px; color: var(--subtle); }}
        input {{ width: 100%; box-sizing: border-box; margin-top: 6px; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--line); background: #fff; }}
        details {{ grid-column: 1 / -1; background: var(--soft); border-radius: 14px; padding: 14px; }}
        summary {{ cursor: pointer; font-weight: 600; color: var(--ink); }}
        .subgrid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 12px; }}
        button {{ padding: 12px 16px; border: none; border-radius: 12px; background: var(--accent); color: white; font-size: 15px; cursor: pointer; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--line); font-size: 14px; vertical-align: top; }}
        .stack {{ display: grid; gap: 18px; }}
        .manual {{ background: linear-gradient(135deg, rgba(15,118,110,0.08), rgba(15,23,42,0.03)), #ffffff; }}
        .manual-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
        .manual-block {{ background: rgba(248,250,252,0.92); border: 1px solid var(--line); border-radius: 14px; padding: 14px; }}
        .manual-block h3 {{ margin: 0 0 10px; font-size: 18px; }}
        .manual-block.wide {{ grid-column: 1 / -1; }}
        .manual td:first-child {{ width: 160px; color: var(--ink); font-weight: 600; }}
        .diag-high {{ color: #b91c1c; }}
        .diag-medium {{ color: #b45309; }}
        .diag-info {{ color: #0f766e; }}
        pre {{ margin: 0; white-space: pre-wrap; word-break: break-word; background: #0f172a; color: #e2e8f0; border-radius: 14px; padding: 14px; overflow-x: auto; }}
      </style>
    </head>
    <body>
      <main>
        <section class="hero">
          <h1>{page_title}</h1>
          <p>{hero_note}</p>
          <div class="nav">
            <a href="/">返回首页</a>
            <a href="/manual">打开 User Manual</a>
            <a href="/legacy-motion-home">打开 V2 估算页面</a>
          </div>
        </section>
        {body}
      </main>
    </body>
    </html>
    """
    return HTMLResponse(html)


def _render_home(body: str, defaults: dict[str, float] | None = None) -> HTMLResponse:
    defaults = defaults or DEFAULT_TOLERANCE_INPUTS
    home_body = f"""
    <section class="panel">
      <h2>操作入口</h2>
      <p class="muted">这个 legacy 页面现在已经升级到 V2 误差模型，除几何、传感和热误差外，还纳入了推力波动、齿槽力、磁场质量和气隙变化。</p>
      <a class="shortcut primary" href="/">返回选型工作台</a>
    </section>
    <section class="panel">
      <h2>V2 公差输入参数表</h2>
      <p class="muted">基础参数用于几何、传感和热误差预算；高级电磁参数用于评估推力波动、磁场质量和低速平稳性风险。</p>
      <form action="/estimate-budget" method="post">
        <label>行程 mm<input type="number" step="1" name="stroke_mm" value="{defaults['stroke_mm']}"></label>
        <label>磁极距 mm<input type="number" step="0.1" name="pole_pitch_mm" value="{defaults['pole_pitch_mm']}"></label>
        <label>磁栅累计节距误差 um/m<input type="number" step="0.1" name="scale_pitch_accuracy_um_per_m" value="{defaults['scale_pitch_accuracy_um_per_m']}"></label>
        <label>磁栅周期误差 um<input type="number" step="0.1" name="scale_cyclic_um" value="{defaults['scale_cyclic_um']}"></label>
        <label>细分/插值误差 um<input type="number" step="0.1" name="interpolation_error_um" value="{defaults['interpolation_error_um']}"></label>
        <label>导轨直线度 um<input type="number" step="0.1" name="guide_straightness_um" value="{defaults['guide_straightness_um']}"></label>
        <label>安装平面度 um<input type="number" step="0.1" name="mounting_flatness_um" value="{defaults['mounting_flatness_um']}"></label>
        <label>装配平行度 um<input type="number" step="0.1" name="assembly_parallelism_um" value="{defaults['assembly_parallelism_um']}"></label>
        <label>Abbe 偏置 mm<input type="number" step="0.1" name="abbe_offset_mm" value="{defaults['abbe_offset_mm']}"></label>
        <label>角度误差 arcsec<input type="number" step="0.1" name="angular_error_arcsec" value="{defaults['angular_error_arcsec']}"></label>
        <label>温差 deltaT C<input type="number" step="0.1" name="thermal_delta_c" value="{defaults['thermal_delta_c']}"></label>
        <label>线膨胀系数 ppm/C<input type="number" step="0.1" name="thermal_expansion_ppm_c" value="{defaults['thermal_expansion_ppm_c']}"></label>
        <label>伺服跟随误差 um<input type="number" step="0.1" name="servo_following_um" value="{defaults['servo_following_um']}"></label>
        <label>测量链不确定度 um<input type="number" step="0.1" name="measurement_uncertainty_um" value="{defaults['measurement_uncertainty_um']}"></label>
        <details>
          <summary>高级电磁参数</summary>
          <div class="subgrid">
            <label>推力波动率 %<input type="number" step="0.1" name="force_ripple_percent" value="{defaults['force_ripple_percent']}"></label>
            <label>推力波动峰峰值 N<input type="number" step="0.1" name="force_ripple_pp_n" value="{defaults['force_ripple_pp_n']}"></label>
            <label>齿槽力峰峰值 N<input type="number" step="0.1" name="cogging_force_pp_n" value="{defaults['cogging_force_pp_n']}"></label>
            <label>磁场均匀性 %<input type="number" step="0.1" name="magnetic_field_uniformity_percent" value="{defaults['magnetic_field_uniformity_percent']}"></label>
            <label>推力常数波动 %<input type="number" step="0.1" name="thrust_constant_variation_percent" value="{defaults['thrust_constant_variation_percent']}"></label>
            <label>气隙变化 um<input type="number" step="0.1" name="air_gap_variation_um" value="{defaults['air_gap_variation_um']}"></label>
            <label>电机极距 mm<input type="number" step="0.1" name="motor_pole_pitch_mm" value="{defaults['motor_pole_pitch_mm']}"></label>
            <label>磁场谐波 %<input type="number" step="0.1" name="magnetic_harmonic_percent" value="{defaults['magnetic_harmonic_percent']}"></label>
            <label>端部效应 %<input type="number" step="0.1" name="end_effect_percent" value="{defaults['end_effect_percent']}"></label>
            <label>电流纹波 %<input type="number" step="0.1" name="current_ripple_percent" value="{defaults['current_ripple_percent']}"></label>
            <label>反电势谐波 %<input type="number" step="0.1" name="back_emf_harmonic_percent" value="{defaults['back_emf_harmonic_percent']}"></label>
            <label>磁性能温漂 %/C<input type="number" step="0.1" name="magnetic_temp_drift_percent_per_c" value="{defaults['magnetic_temp_drift_percent_per_c']}"></label>
          </div>
        </details>
        <button type="submit">开始估算</button>
      </form>
    </section>
    <section class="panel">
      <h2>CSV 标定模式</h2>
      <p class="muted">拿到激光干涉仪或高精度参考尺数据后，可在这里做谐波拟合、补偿表生成和残差分析。</p>
      <form action="/analyze" method="post" enctype="multipart/form-data">
        <label>标定 CSV<input type="file" name="file" accept=".csv" required></label>
        <label>磁极距 mm<input type="number" step="0.1" name="pole_pitch_mm" value="2.0"></label>
        <label>谐波阶数<input type="number" step="1" name="harmonic_count" value="5"></label>
        <label>补偿表间距 mm<input type="number" step="0.5" name="lookup_spacing_mm" value="5.0"></label>
        <button type="submit">分析 CSV</button>
      </form>
    </section>
    {body}
    """
    return _render_shell(home_body)


def _render_manual_page() -> HTMLResponse:
    manual_body = f"""
    <section class="panel manual">
      <h2>User Manual</h2>
      <p class="muted">这里集中说明 V2 页面里的基础参数、高级电磁参数、典型范围和结果解读方式。</p>
      <div class="manual-grid">
        {_render_parameter_table()}
        {_render_manual_blocks()}
      </div>
    </section>
    """
    return _render_shell(manual_body, page_title="User Manual", hero_note="这是一份面向运动精度 V2 误差预算场景的简明手册，重点解释新增的电磁误差参数应该如何填写。")


def _render_tolerance_result(result: dict, defaults: dict[str, float]) -> HTMLResponse:
    contributors_rows = "".join(
        f"<tr><td>{item['name']}</td><td>{item['estimate_um']:.2f}</td></tr>"
        for item in result["contributors"]
    )
    diagnostics_rows = "".join(
        f"<tr><td class='diag-{item['severity']}'>{item['severity']}</td><td>{item['message']}</td></tr>"
        for item in result["diagnostics"]
    )
    category_rows = "".join(
        f"<tr><td>{label}</td><td>{result['category_totals'][key]:.2f}</td><td>{result['category_ratios'][key.replace('_um', '_ratio_percent')]:.1f}%</td></tr>"
        for label, key in [
            ("传感误差", "sensor_um"),
            ("几何误差", "geometry_um"),
            ("电磁误差", "electromagnetic_um"),
            ("热误差", "thermal_um"),
            ("控制误差", "control_um"),
            ("测量误差", "measurement_um"),
        ]
    )
    curve = _svg_polyline(
        [(item["position_mm"], item["estimated_error_um"]) for item in result["samples"]],
        stroke="#0f766e",
    )
    body = f"""
    <section class="stack">
      <section class="panel">
        <div class="metrics">
          <div class="metric">最坏值合成<strong>{result['summary']['worst_case_um']:.2f} um</strong></div>
          <div class="metric">RSS 合成<strong>{result['summary']['rss_um']:.2f} um</strong></div>
          <div class="metric">主导误差项<strong>{result['summary']['dominant_error']}</strong></div>
          <div class="metric">电磁误差贡献<strong>{result['summary']['electromagnetic_um']:.2f} um</strong></div>
          <div class="metric">电磁误差占比<strong>{result['summary']['electromagnetic_ratio_percent']:.1f}%</strong></div>
        </div>
      </section>
      <section class="panel">
        <h2>预计误差包络</h2>
        <p class="muted">V2 曲线已经叠加几何、传感、热和电磁等效误差，用于方案阶段判断主导风险，不等同于最终实测标定曲线。</p>
        {curve}
      </section>
      <section class="panel">
        <h2>误差贡献分解</h2>
        <table>
          <thead><tr><th>误差来源</th><th>估算值 um</th></tr></thead>
          <tbody>{contributors_rows}</tbody>
        </table>
      </section>
      <section class="panel">
        <h2>分类误差占比</h2>
        <table>
          <thead><tr><th>误差类别</th><th>合成值 um</th><th>占最坏值比例</th></tr></thead>
          <tbody>{category_rows}</tbody>
        </table>
      </section>
      <section class="panel">
        <h2>专家建议</h2>
        <table>
          <thead><tr><th>等级</th><th>说明</th></tr></thead>
          <tbody>{diagnostics_rows}</tbody>
        </table>
      </section>
      <section class="panel">
        <h2>JSON 结果</h2>
        <pre>{json.dumps(result, ensure_ascii=False, indent=2)}</pre>
      </section>
    </section>
    """
    return _render_home(body, defaults)


def _render_csv_result(result, defaults: dict[str, float]) -> HTMLResponse:
    curve = _svg_polyline(
        [(item["position_mm"], item["original_error_um"]) for item in result.samples],
        stroke="#0f766e",
    )
    residual_curve = _svg_polyline(
        [(item["position_mm"], item["residual_um"]) for item in result.samples],
        stroke="#1d4ed8",
    )
    diagnostics_rows = "".join(
        f"<tr><td>{item.code}</td><td class='diag-{item.severity}'>{item.severity}</td><td>{item.message}</td></tr>"
        for item in result.diagnostics
    )
    harmonic_rows = "".join(
        f"<tr><td>{item.order}</td><td>{item.sin_coeff_um:.3f}</td><td>{item.cos_coeff_um:.3f}</td><td>{item.amplitude_um:.3f}</td></tr>"
        for item in result.harmonic_terms
    )
    body = f"""
    <section class="stack">
      <section class="panel">
        <div class="metrics">
          <div class="metric">峰峰值<strong>{result.summary.peak_to_peak_um:.2f} um</strong></div>
          <div class="metric">残差 RMSE<strong>{result.summary.residual_rmse_um:.2f} um</strong></div>
          <div class="metric">重复性<strong>{result.summary.repeatability_um:.2f} um</strong></div>
          <div class="metric">扩展不确定度<strong>{result.summary.expanded_uncertainty_um:.2f} um</strong></div>
        </div>
      </section>
      <section class="panel">
        <h2>原始误差曲线</h2>
        {curve}
      </section>
      <section class="panel">
        <h2>补偿后残差曲线</h2>
        {residual_curve}
      </section>
      <section class="panel">
        <h2>专家诊断</h2>
        <table>
          <thead><tr><th>编码</th><th>等级</th><th>说明</th></tr></thead>
          <tbody>{diagnostics_rows}</tbody>
        </table>
      </section>
      <section class="panel">
        <h2>2 mm 周期谐波拟合</h2>
        <table>
          <thead><tr><th>阶次</th><th>Sin 系数 um</th><th>Cos 系数 um</th><th>幅值 um</th></tr></thead>
          <tbody>{harmonic_rows}</tbody>
        </table>
      </section>
      <section class="panel">
        <h2>JSON 结果</h2>
        <pre>{json.dumps(result.to_dict(), ensure_ascii=False, indent=2)}</pre>
      </section>
    </section>
    """
    return _render_home(body, defaults)


def _coerce_budget_defaults(form_data: dict[str, str]) -> dict[str, float]:
    defaults = DEFAULT_TOLERANCE_INPUTS.copy()
    for key in defaults:
        raw = form_data.get(key)
        if raw in (None, ""):
            continue
        defaults[key] = float(raw)
    return defaults


@app.get("/", include_in_schema=False)
async def index() -> RedirectResponse:
    return RedirectResponse(url="/selection-workbench", status_code=307)


@app.get("/legacy-motion-home", response_class=HTMLResponse)
async def legacy_motion_home() -> HTMLResponse:
    return _render_home("")


@app.get("/manual", response_class=HTMLResponse)
async def manual() -> HTMLResponse:
    return _render_manual_page()


@app.post("/estimate-budget", response_class=HTMLResponse)
async def estimate_budget(request: Request) -> HTMLResponse:
    form = await request.form()
    defaults = _coerce_budget_defaults(dict(form))
    result = estimate_error_budget(defaults)
    return _render_tolerance_result(result, defaults)


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    file: UploadFile = File(...),
    pole_pitch_mm: float = Form(2.0),
    harmonic_count: int = Form(5),
    lookup_spacing_mm: float = Form(5.0),
) -> HTMLResponse:
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))
    config = SystemConfig(
        pole_pitch_mm=pole_pitch_mm,
        harmonic_count=harmonic_count,
        lookup_spacing_mm=lookup_spacing_mm,
    )
    result = analyze_measurements(df, config=config)
    return _render_csv_result(result, DEFAULT_TOLERANCE_INPUTS)
