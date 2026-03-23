# Remote NGSpice Service 协议草案（V0.1）

## 1. 目标

本文档定义 `remote_ngspice_service` 作为远程 provider 时，建议采用的 HTTP 协议。

该服务的定位不是完整的 EDA 平台，而是一个被智能体调用的“受控电路级仿真执行器”，主要服务于：

1. Bootstrap 裕量验证
2. 栅极振铃 / 过冲扫描
3. 分流采样前端验证
4. OCP / UVLO 等保护链路验证
5. 参数扫描与批量角点验证

---

## 2. 设计原则

1. 异步执行，不阻塞主请求
2. 请求对象尽量复用智能体侧的 `simulation_request`
3. 原始输入、日志、结果、波形分开存储
4. 每次执行都带模板版本、工具版本和参数版本
5. 允许返回 stub / failed / partial，而不是只允许 success

---

## 3. 推荐接口

### 3.1 创建任务

`POST /v1/jobs`

请求体示例：

```json
{
  "simulation_request_id": "simreq_20260323_001",
  "template_id": "tpl_half_bridge_bootstrap_v1",
  "tool": "ngspice",
  "project_context": {
    "bus_voltage_v": 48,
    "switching_frequency_khz": 20,
    "ambient_temp_c": 25
  },
  "parameter_bindings": {
    "driver_part": "DRV8353",
    "mosfet_part": "IPB017N10N5",
    "gate_res_ohm": 5.1,
    "bootstrap_cap_nf": 100
  },
  "input_artifacts": [
    {
      "artifact_type": "schematic_pdf",
      "path": "/artifacts/project_a/schematic.pdf"
    },
    {
      "artifact_type": "bom",
      "path": "/artifacts/project_a/bom.xlsx"
    }
  ],
  "sweeps": [
    {
      "name": "bus_voltage_v",
      "type": "corner",
      "values": [36, 48, 60]
    },
    {
      "name": "temperature_c",
      "type": "corner",
      "values": [25, 85, 125]
    }
  ],
  "measurements": [
    "v_bootstrap_min",
    "switch_node_overshoot"
  ],
  "pass_criteria": [
    {
      "metric": "v_bootstrap_min",
      "operator": ">=",
      "value": 8.0,
      "unit": "V"
    },
    {
      "metric": "switch_node_overshoot",
      "operator": "<=",
      "value": 10.0,
      "unit": "V"
    }
  ],
  "callback_url": null
}
```

响应示例：

```json
{
  "job_id": "rng_001",
  "status": "queued",
  "accepted_at": "2026-03-23T18:00:00+08:00"
}
```

### 3.2 查询任务状态

`GET /v1/jobs/{job_id}`

响应示例：

```json
{
  "job_id": "rng_001",
  "status": "running",
  "template_id": "tpl_half_bridge_bootstrap_v1",
  "tool": "ngspice",
  "started_at": "2026-03-23T18:00:10+08:00",
  "progress": {
    "completed_sweeps": 3,
    "total_sweeps": 9
  }
}
```

### 3.3 获取结果

`GET /v1/jobs/{job_id}/result`

响应示例：

```json
{
  "job_id": "rng_001",
  "status": "completed",
  "summary": "Bootstrap margin passes at nominal condition but switch-node overshoot fails at high-voltage corners.",
  "metrics": [
    {
      "name": "v_bootstrap_min",
      "value": 8.4,
      "unit": "V",
      "limit": 8.0,
      "judgement": "pass"
    },
    {
      "name": "switch_node_overshoot",
      "value": 13.2,
      "unit": "V",
      "limit": 10.0,
      "judgement": "fail"
    }
  ],
  "worst_case_corner": {
    "bus_voltage_v": 60,
    "temperature_c": 125
  },
  "artifacts": {
    "log_path": "/remote_jobs/rng_001/run.log",
    "waveforms": [
      "/remote_jobs/rng_001/switch_node.csv",
      "/remote_jobs/rng_001/gate_high.csv"
    ],
    "raw_result_path": "/remote_jobs/rng_001/result.json"
  },
  "tool_version": "ngspice-xx",
  "template_version": "0.1.0"
}
```

### 3.4 取消任务

`POST /v1/jobs/{job_id}/cancel`

响应示例：

```json
{
  "job_id": "rng_001",
  "status": "cancelled"
}
```

---

## 4. 智能体侧映射关系

建议映射如下：

1. 智能体的 `simulation_request`
   对应远程服务的 `POST /v1/jobs` 请求体
2. 智能体的 `simulation_run`
   对应远程服务的任务状态对象
3. 智能体的 `simulation_result`
   对应远程服务的结果对象

这样后续替换 provider 时，上层 orchestration 基本不需要重写。

---

## 5. 模板执行约束

远程服务建议只允许执行白名单模板，不接受任意原始 netlist。

原因：

1. 降低安全风险
2. 降低模型胡乱生成网表的风险
3. 更容易做结果回归
4. 更容易做企业级治理

建议策略：

1. 服务端保存模板文件
2. 智能体只传参数绑定和扫描条件
3. 所有模板必须带版本号
4. 每个模板有负责人和适用边界

---

## 6. 安全建议

1. 使用鉴权 token 或内部网关
2. 限制可执行模板和最大 sweep 数量
3. 限制单任务运行时长
4. 记录请求人、来源任务、参数摘要和结果摘要
5. 保留日志和审计记录

---

## 7. 第一阶段实现建议

如果你们要快速落地，建议先只做：

1. 一个模板目录
2. `POST /v1/jobs`
3. `GET /v1/jobs/{job_id}`
4. `GET /v1/jobs/{job_id}/result`
5. 本地队列 + 文件落盘

先把协议跑通，再考虑：

1. 分布式队列
2. 更复杂的 artifact 上传
3. 回调通知
4. 权限体系增强

---

## 8. 与当前仓库的关系

当前仓库中的：

1. `app/simulation_models.py`
2. `app/simulation_service.py`
3. `app/simulation_api.py`
4. `app/simulation_providers/remote_ngspice_service.json`
5. `/simulation-workbench`

已经可以作为上层 orchestration 骨架。

后续只需要新增一个真正对接该协议的 adapter，就能把 stub 替换为真实执行结果。
