from __future__ import annotations

import io
import json

import pandas as pd
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse

from .calibration import analyze_measurements, estimate_error_budget
from .models import SystemConfig


app = FastAPI(title="**电机精度估算与校正专家系统")


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
}


MANUAL_SECTIONS = [
    {
        "title": "如何使用本系统",
        "items": [
            ("适用阶段", "当前首页更适合方案设计阶段，在没有标定 CSV 时，先基于各零件公差和装配公差做误差预算。"),
            ("输出内容", "系统会给出最坏值合成误差、RSS 合成误差、主导误差来源、预计误差包络以及专家建议。"),
            ("结果性质", "这里的结果是公差链估算值，不等同于激光干涉仪实测标定结果，适合做前期方案比较和敏感度分析。"),
        ],
    },
    {
        "title": "参数填写说明",
        "items": [
            ("行程 mm", "直线轴的有效运动范围。行程越长，累计节距误差和热伸缩误差通常越大。"),
            ("磁极距 mm", "磁栅尺的磁极周期。你的场景默认是 2 mm，这会直接决定周期误差的基础频率。"),
            ("磁栅累计节距误差 um/m", "磁栅尺在 1 米范围内的累计位置误差指标，通常来自磁栅尺规格书。"),
            ("磁栅周期误差 um", "与磁极距同步的周期性误差幅值，常由磁头安装、磁场不均匀和读数链路引起。"),
            ("细分/插值误差 um", "读数头细分算法、A/B 或正余弦插值带来的附加误差，通常可从传感器说明书或经验值获得。"),
            ("导轨直线度 um", "导轨或运动副本身的几何直线度误差，会直接影响运动轨迹和位置精度。"),
            ("安装平面度 um", "磁栅尺安装基面或导轨安装基面的平面度误差，会传递到测量与运动精度中。"),
            ("装配平行度 um", "磁栅读头、磁栅尺、导轨、定子等关键部件之间的平行度或相对安装偏差。"),
            ("Abbe 偏置 mm", "测量轴线与实际工作点之间的距离。偏置越大，角度误差引起的位置误差越明显。"),
            ("角度误差 arcsec", "运动过程中的俯仰、偏摆或安装角误差。系统用它和 Abbe 偏置共同估算 Abbe 误差。"),
            ("温差 deltaT C", "设备工作时相对标定状态的温升或环境温差。"),
            ("线膨胀系数 ppm/C", "结构材料的热膨胀系数，钢常见约 11 到 12 ppm/C，铝更高。"),
            ("伺服跟随误差 um", "控制系统在运动过程中的跟随偏差，通常可按经验值或控制器指标填写。"),
            ("测量链不确定度 um", "参考测量系统、装调读数和估算模型本身的不确定度。"),
        ],
    },
    {
        "title": "推荐填写来源",
        "items": [
            ("规格书参数", "磁栅累计节距误差、周期误差、细分误差、导轨直线度优先填写厂商规格书数值。"),
            ("图纸公差", "安装平面度、装配平行度、Abbe 偏置优先根据结构设计图和装配要求填写。"),
            ("经验值", "伺服跟随误差、温差、测量链不确定度在没有实测时可先填写保守经验值。"),
        ],
    },
    {
        "title": "如何理解结果",
        "items": [
            ("最坏值合成", "把各项误差按最不利方向直接叠加，结果偏保守，适合做上限评估。"),
            ("RSS 合成", "按均方根方式合成，适合估计更接近统计意义下的综合误差。"),
            ("主导误差项", "误差贡献最大的环节，通常就是优先优化或优先补偿的对象。"),
            ("预计误差包络", "是根据参数合成出来的代表性趋势图，用来看长周期、周期和几何误差的相对占比。"),
        ],
    },
]


PARAMETER_GUIDE = [
    ("行程 mm", "100 到 3000", "由轴的有效工作行程决定", "越长时累计节距误差和热误差通常更快放大"),
    ("磁极距 mm", "本项目默认 2", "由磁栅尺规格确定", "决定周期误差基础频率，填写错误会直接影响误差形态判断"),
    ("磁栅累计节距误差 um/m", "5 到 30", "优先查磁栅尺规格书", "主导长行程绝对定位误差"),
    ("磁栅周期误差 um", "1 到 10", "优先查磁栅尺或读头规格", "偏大时应优先考虑周期补偿与安装优化"),
    ("细分/插值误差 um", "0.5 到 5", "来自读头细分链路或经验值", "偏大时会放大 2 mm 及其谐波误差"),
    ("导轨直线度 um", "2 到 20", "优先查导轨等级或安装要求", "偏大时几何误差往往成为主导项"),
    ("安装平面度 um", "2 到 20", "来自基面加工与装配图纸", "偏大时会把结构误差传递到整机"),
    ("装配平行度 um", "2 到 15", "由装调工艺和装配精度决定", "偏大时常引起读头间隙变化和附加周期误差"),
    ("Abbe 偏置 mm", "5 到 80", "由测量轴与工作点距离决定", "偏大时角度误差会被明显放大"),
    ("角度误差 arcsec", "2 到 30", "来自俯仰/偏摆/装配角误差", "与 Abbe 偏置组合后可能迅速抬高定位误差"),
    ("温差 deltaT C", "0.5 到 8", "按工作环境或温升估算", "温差越大，热伸缩误差越需要重点控制"),
    ("线膨胀系数 ppm/C", "钢约 11.5，铝约 23", "按材料确定", "材料选择会直接影响热误差灵敏度"),
    ("伺服跟随误差 um", "1 到 10", "按控制器性能或经验值填写", "高速场景下容易成为动态误差来源"),
    ("测量链不确定度 um", "0.5 到 5", "按参考测量和估算保守值填写", "该值越大，预算结果可信边界越宽"),
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
    section_html = []
    for section in MANUAL_SECTIONS:
        rows = "".join(
            f"<tr><td>{name}</td><td>{description}</td></tr>"
            for name, description in section["items"]
        )
        section_html.append(
            f"""
            <section class="manual-block">
              <h3>{section['title']}</h3>
              <table>
                <tbody>{rows}</tbody>
              </table>
            </section>
            """
        )
    return "".join(section_html)


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


def _render_shell(body: str, page_title: str = "**电机精度估算与校正", hero_note: str = "优先支持基于零件公差和装配公差的误差预算；有实测数据时，也可以再切换到 CSV 标定模式。") -> HTMLResponse:
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
          background:
            radial-gradient(circle at top right, rgba(15, 118, 110, 0.16), transparent 26%),
            linear-gradient(180deg, #eef6f4 0%, var(--bg) 100%);
          color: var(--ink);
        }}
        main {{
          max-width: 1180px;
          margin: 0 auto;
          padding: 28px 20px 48px;
        }}
        .hero {{
          margin-bottom: 20px;
        }}
        .hero h1 {{
          margin: 0 0 10px;
          font-size: 34px;
        }}
        .hero p {{
          margin: 0;
          color: var(--subtle);
        }}
        .nav {{
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          margin-top: 16px;
        }}
        .nav a, .shortcut {{
          display: inline-block;
          padding: 10px 14px;
          border-radius: 999px;
          border: 1px solid var(--line);
          text-decoration: none;
          color: var(--ink);
          background: rgba(255, 255, 255, 0.8);
          font-size: 14px;
        }}
        .shortcut.primary {{
          background: var(--accent);
          color: #fff;
          border-color: var(--accent);
        }}
        .panel {{
          background: var(--panel);
          border: 1px solid rgba(219, 227, 234, 0.9);
          border-radius: 18px;
          padding: 20px;
          box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
          margin-bottom: 18px;
        }}
        .panel h2 {{
          margin-top: 0;
          margin-bottom: 8px;
        }}
        .muted {{
          color: var(--subtle);
          margin: 0 0 14px;
        }}
        .metrics {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 14px;
        }}
        .metric {{
          background: var(--soft);
          border-radius: 14px;
          padding: 14px;
        }}
        .metric strong {{
          display: block;
          font-size: 24px;
          color: var(--accent);
          margin-top: 6px;
        }}
        form {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 12px;
          align-items: end;
        }}
        label {{
          display: block;
          font-size: 14px;
          color: var(--subtle);
        }}
        input {{
          width: 100%;
          box-sizing: border-box;
          margin-top: 6px;
          padding: 10px 12px;
          border-radius: 10px;
          border: 1px solid var(--line);
          background: #fff;
        }}
        button {{
          padding: 12px 16px;
          border: none;
          border-radius: 12px;
          background: var(--accent);
          color: white;
          font-size: 15px;
          cursor: pointer;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
        }}
        th, td {{
          text-align: left;
          padding: 10px 8px;
          border-bottom: 1px solid var(--line);
          font-size: 14px;
          vertical-align: top;
        }}
        .stack {{
          display: grid;
          gap: 18px;
        }}
        .manual {{
          background:
            linear-gradient(135deg, rgba(15, 118, 110, 0.08), rgba(15, 23, 42, 0.03)),
            #ffffff;
        }}
        .manual-grid {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
          gap: 16px;
        }}
        .manual-block {{
          background: rgba(248, 250, 252, 0.92);
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 14px;
        }}
        .manual-block h3 {{
          margin: 0 0 10px;
          font-size: 18px;
        }}
        .manual-block.wide {{
          grid-column: 1 / -1;
        }}
        .manual td:first-child {{
          width: 150px;
          color: var(--ink);
          font-weight: 600;
        }}
        .diag-high {{ color: #b91c1c; }}
        .diag-medium {{ color: #b45309; }}
        .diag-info {{ color: #0f766e; }}
        pre {{
          margin: 0;
          white-space: pre-wrap;
          word-break: break-word;
          background: #0f172a;
          color: #e2e8f0;
          border-radius: 14px;
          padding: 14px;
          overflow-x: auto;
        }}
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
      <p class="muted">首页专注于输入与结果。如果你需要查看参数解释、典型范围和结果判读，请打开单独的 User Manual 页面。</p>
      <a class="shortcut primary" href="/manual">查看 User Manual</a>
    </section>
    <section class="panel">
      <h2>公差输入参数表</h2>
      <p class="muted">适用于方案设计阶段。系统会根据公差链估算最坏值、RSS 合成误差和主导误差来源。</p>
      <form action="/estimate-budget" method="post">
        <label>行程 mm
          <input type="number" step="1" name="stroke_mm" value="{defaults['stroke_mm']}">
        </label>
        <label>磁极距 mm
          <input type="number" step="0.1" name="pole_pitch_mm" value="{defaults['pole_pitch_mm']}">
        </label>
        <label>磁栅累计节距误差 um/m
          <input type="number" step="0.1" name="scale_pitch_accuracy_um_per_m" value="{defaults['scale_pitch_accuracy_um_per_m']}">
        </label>
        <label>磁栅周期误差 um
          <input type="number" step="0.1" name="scale_cyclic_um" value="{defaults['scale_cyclic_um']}">
        </label>
        <label>细分/插值误差 um
          <input type="number" step="0.1" name="interpolation_error_um" value="{defaults['interpolation_error_um']}">
        </label>
        <label>导轨直线度 um
          <input type="number" step="0.1" name="guide_straightness_um" value="{defaults['guide_straightness_um']}">
        </label>
        <label>安装平面度 um
          <input type="number" step="0.1" name="mounting_flatness_um" value="{defaults['mounting_flatness_um']}">
        </label>
        <label>装配平行度 um
          <input type="number" step="0.1" name="assembly_parallelism_um" value="{defaults['assembly_parallelism_um']}">
        </label>
        <label>Abbe 偏置 mm
          <input type="number" step="0.1" name="abbe_offset_mm" value="{defaults['abbe_offset_mm']}">
        </label>
        <label>角度误差 arcsec
          <input type="number" step="0.1" name="angular_error_arcsec" value="{defaults['angular_error_arcsec']}">
        </label>
        <label>温差 deltaT C
          <input type="number" step="0.1" name="thermal_delta_c" value="{defaults['thermal_delta_c']}">
        </label>
        <label>线膨胀系数 ppm/C
          <input type="number" step="0.1" name="thermal_expansion_ppm_c" value="{defaults['thermal_expansion_ppm_c']}">
        </label>
        <label>伺服跟随误差 um
          <input type="number" step="0.1" name="servo_following_um" value="{defaults['servo_following_um']}">
        </label>
        <label>测量链不确定度 um
          <input type="number" step="0.1" name="measurement_uncertainty_um" value="{defaults['measurement_uncertainty_um']}">
        </label>
        <button type="submit">开始估算</button>
      </form>
    </section>
    <section class="panel">
      <h2>CSV 标定模式</h2>
      <p class="muted">拿到激光干涉仪或高精度参考尺数据后，再用这个入口做谐波拟合、补偿表生成和残差分析。</p>
      <form action="/analyze" method="post" enctype="multipart/form-data">
        <label>标定 CSV
          <input type="file" name="file" accept=".csv" required>
        </label>
        <label>磁极距 mm
          <input type="number" step="0.1" name="pole_pitch_mm" value="2.0">
        </label>
        <label>谐波阶数
          <input type="number" step="1" name="harmonic_count" value="5">
        </label>
        <label>补偿表间距 mm
          <input type="number" step="0.5" name="lookup_spacing_mm" value="5.0">
        </label>
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
      <p class="muted">这里集中说明首页各参数的工程含义、典型范围、推荐来源和结果判读方法，适合单独翻阅。</p>
      <div class="manual-grid">
        {_render_parameter_table()}
        {_render_manual_blocks()}
      </div>
    </section>
    """
    return _render_shell(manual_body, page_title="User Manual", hero_note="这是一份面向方案设计阶段的使用手册，帮助你更快理解公差参数应该怎么填、结果应该怎么看。")


def _render_tolerance_result(result: dict, defaults: dict[str, float]) -> HTMLResponse:
    contributors_rows = "".join(
        f"<tr><td>{item['name']}</td><td>{item['estimate_um']:.2f}</td></tr>"
        for item in result["contributors"]
    )
    diagnostics_rows = "".join(
        f"<tr><td class='diag-{item['severity']}'>{item['severity']}</td><td>{item['message']}</td></tr>"
        for item in result["diagnostics"]
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
        </div>
      </section>
      <section class="panel">
        <h2>预计误差包络</h2>
        <p class="muted">这是根据公差链合成的预估误差曲线，用于方案阶段判断主导误差，不等同于实测标定曲线。</p>
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


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return _render_home("")


@app.get("/manual", response_class=HTMLResponse)
async def manual() -> HTMLResponse:
    return _render_manual_page()


@app.post("/estimate-budget", response_class=HTMLResponse)
async def estimate_budget(
    stroke_mm: float = Form(DEFAULT_TOLERANCE_INPUTS["stroke_mm"]),
    pole_pitch_mm: float = Form(DEFAULT_TOLERANCE_INPUTS["pole_pitch_mm"]),
    scale_pitch_accuracy_um_per_m: float = Form(DEFAULT_TOLERANCE_INPUTS["scale_pitch_accuracy_um_per_m"]),
    scale_cyclic_um: float = Form(DEFAULT_TOLERANCE_INPUTS["scale_cyclic_um"]),
    interpolation_error_um: float = Form(DEFAULT_TOLERANCE_INPUTS["interpolation_error_um"]),
    guide_straightness_um: float = Form(DEFAULT_TOLERANCE_INPUTS["guide_straightness_um"]),
    mounting_flatness_um: float = Form(DEFAULT_TOLERANCE_INPUTS["mounting_flatness_um"]),
    assembly_parallelism_um: float = Form(DEFAULT_TOLERANCE_INPUTS["assembly_parallelism_um"]),
    abbe_offset_mm: float = Form(DEFAULT_TOLERANCE_INPUTS["abbe_offset_mm"]),
    angular_error_arcsec: float = Form(DEFAULT_TOLERANCE_INPUTS["angular_error_arcsec"]),
    thermal_delta_c: float = Form(DEFAULT_TOLERANCE_INPUTS["thermal_delta_c"]),
    thermal_expansion_ppm_c: float = Form(DEFAULT_TOLERANCE_INPUTS["thermal_expansion_ppm_c"]),
    servo_following_um: float = Form(DEFAULT_TOLERANCE_INPUTS["servo_following_um"]),
    measurement_uncertainty_um: float = Form(DEFAULT_TOLERANCE_INPUTS["measurement_uncertainty_um"]),
) -> HTMLResponse:
    defaults = {
        "stroke_mm": stroke_mm,
        "pole_pitch_mm": pole_pitch_mm,
        "scale_pitch_accuracy_um_per_m": scale_pitch_accuracy_um_per_m,
        "scale_cyclic_um": scale_cyclic_um,
        "interpolation_error_um": interpolation_error_um,
        "guide_straightness_um": guide_straightness_um,
        "mounting_flatness_um": mounting_flatness_um,
        "assembly_parallelism_um": assembly_parallelism_um,
        "abbe_offset_mm": abbe_offset_mm,
        "angular_error_arcsec": angular_error_arcsec,
        "thermal_delta_c": thermal_delta_c,
        "thermal_expansion_ppm_c": thermal_expansion_ppm_c,
        "servo_following_um": servo_following_um,
        "measurement_uncertainty_um": measurement_uncertainty_um,
    }
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
