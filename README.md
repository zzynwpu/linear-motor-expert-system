# 直线电机运动精度估算与校正原型

这个项目提供一版可运行的 Python 原型，用于分析采用磁栅尺的位置反馈系统，既支持方案阶段基于零件公差和装配公差的误差预算，也支持拿到标定 CSV 后进行周期误差识别、补偿表生成和专家诊断。

## 功能

- 基于公差链估算最坏值合成误差与 RSS 合成误差
- 分解磁栅累计节距误差、2 mm 周期误差、装配几何误差、Abbe 误差和热误差
- 输出主导误差来源和专家建议
- 支持基于 CSV 标定数据进行误差分解
- 针对 2 mm 磁极距拟合周期误差及谐波
- 生成位置查表补偿结果
- 支持本地 CLI 和网页端 FastAPI

## 目录

- `app/models.py`：数据结构
- `app/calibration.py`：核心分析流程和公差预算逻辑
- `app/rules.py`：CSV 标定模式下的专家规则
- `app/cli.py`：命令行入口
- `app/web.py`：网页端入口
- `app/sample_data.py`：示例数据生成器
- `docs/system_overall_design.md`：系统总体方案书
- `docs/render_step_by_step_deploy.md`：Render 上线逐步操作清单

## 方案阶段输入参数

首页主入口支持以下公差参数：

- `stroke_mm`：行程
- `pole_pitch_mm`：磁极距
- `scale_pitch_accuracy_um_per_m`：磁栅累计节距误差
- `scale_cyclic_um`：磁栅周期误差
- `interpolation_error_um`：细分误差
- `guide_straightness_um`：导轨直线度
- `mounting_flatness_um`：安装平面度
- `assembly_parallelism_um`：装配平行度
- `abbe_offset_mm`：Abbe 偏置
- `angular_error_arcsec`：角度误差
- `thermal_delta_c`：温差
- `thermal_expansion_ppm_c`：线膨胀系数
- `servo_following_um`：伺服跟随误差
- `measurement_uncertainty_um`：测量链不确定度

## CSV 数据格式

如果后续拿到标定 CSV，建议包含以下列：

- `position_mm`
- `sensor_position_mm`
- `reference_position_mm`
- `velocity_mm_s`：可选
- `temperature_c`：可选
- `direction`：可选，取值 `1` 或 `-1`

位置误差定义为：

`error_mm = sensor_position_mm - reference_position_mm`

## 本地运行

安装依赖：

```bash
pip install -r requirements.txt
```

启动网页端：

```bash
uvicorn app.web:app --reload
```

启动后访问：

`http://127.0.0.1:8000`

## 公网部署

如果你希望“把网址直接发给其他人使用”，当前项目最简单的做法是部署到支持 FastAPI 的云平台。

推荐优先级：

1. Render
2. Railway
3. 自己的云服务器或 Docker 主机

项目已经补好了以下部署文件：

- `.python-version`
- `Dockerfile`
- `.dockerignore`
- `render.yaml`
- `docs/render_step_by_step_deploy.md`

### Python 版本固定

项目根目录已经增加：

`/.python-version`

内容为：

`3.12`

这样可以让部署平台优先使用 Python 3.12 系列，减少默认版本变化带来的不一致风险。

### 方式一：Render

把代码推到 GitHub 后，在 Render 新建 Web Service，指向这个仓库即可。

- Build Command：`pip install -r requirements.txt`
- Start Command：`uvicorn app.web:app --host 0.0.0.0 --port $PORT`

部署完成后，Render 会给你一个公网 URL，可直接发给其他人。

如果你是第一次部署，推荐直接照着这份文档操作：

- `docs/render_step_by_step_deploy.md`

### 方式二：Railway

同样把代码推到 GitHub 后，在 Railway 从 GitHub 仓库部署。

应用启动命令可设置为：

`uvicorn app.web:app --host 0.0.0.0 --port $PORT`

部署后记得在 Railway 里生成公开域名。

如果想体验 CSV 模式，可以先生成示例数据：

```bash
python -m app.sample_data
python -m app.cli --input data/sample_measurements.csv --output reports/sample_report.json
```

## 部署建议

- 本地桌面使用：网页端优先，CLI 作为批处理工具
- 内网网页部署：FastAPI + `uvicorn`
- 容器化部署：可继续补 `Dockerfile`


## 新增方案文档

- `docs/motor_controller_agent_prd.md`：电机控制专家智能体 PRD
- `docs/motor_controller_agent_architecture.md`：电机控制专家智能体架构方案
- `docs/motor_controller_knowledge_schema.md`：知识库 Schema
- `docs/motor_controller_review_output_schema.md`：统一输出 JSON 规范
- `docs/motor_controller_eval_template.md`：评测集与评分模板
- `docs/motor_controller_simulation_integration_plan.md`：仿真接入详细方案
- `docs/motor_controller_simulation_io_schema.md`：仿真 I/O Schema 与接口草案
- `docs/motor_controller_simulation_task_templates.md`：首批仿真任务模板库
- `docs/motor_controller_web_remote_simulation_strategy.md`：Web / 远程仿真优先策略
- `GET /simulation-workbench`：浏览器版仿真工作台，可选择 provider 和 template 并提交仿真请求
- `docs/remote_ngspice_service_protocol.md`：remote_ngspice_service 的 HTTP 协议草案
