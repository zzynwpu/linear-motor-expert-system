# 电机控制仿真 I/O Schema 与接口草案（V0.1）

## 1. 目标

本文档定义仿真能力接入智能体时推荐使用的数据结构，目的是让不同仿真工具都能通过统一接口被编排。

建议统一五类对象：

1. `simulation_request`
2. `simulation_model_manifest`
3. `simulation_run`
4. `simulation_result`
5. `simulation_finding`

---

## 2. Simulation Request

```json
{
  "simulation_request_id": "simreq_20260321_001",
  "task_id": "task_20260321_001",
  "task_type": "schematic_review",
  "motor_type": "bldc",
  "simulation_level": "circuit",
  "simulation_goal": "Validate bootstrap voltage margin and gate overshoot risk.",
  "selected_tool": "ngspice",
  "template_id": "tpl_half_bridge_bootstrap_v1",
  "project_context": {
    "bus_voltage_v": 48,
    "switching_frequency_khz": 20,
    "ambient_temp_c": 25
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
  "parameter_bindings": {
    "mosfet_part": "IPB017N10N5",
    "gate_res_ohm": 5.1,
    "bootstrap_cap_nf": 100,
    "driver_part": "DRV8353"
  },
  "sweeps": [
    {
      "name": "bus_voltage",
      "type": "corner",
      "values": [36, 48, 60]
    },
    {
      "name": "temperature",
      "type": "corner",
      "values": [25, 85, 125]
    }
  ],
  "measurements": [
    "v_bootstrap_min",
    "vgs_high_peak",
    "switch_node_overshoot",
    "gate_ringing_cycles"
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
  "priority": "high",
  "requested_by": "agent_orchestrator"
}
```

---

## 3. Simulation Model Manifest

用于声明模板能力、输入要求和局限。

```json
{
  "template_id": "tpl_half_bridge_bootstrap_v1",
  "name": "Half-bridge bootstrap transient validation",
  "simulation_level": "circuit",
  "supported_tools": ["ngspice", "ltspice"],
  "motor_types": ["bldc", "servo"],
  "task_types": ["schematic_review", "risk_analysis"],
  "required_parameters": [
    "bus_voltage_v",
    "switching_frequency_khz",
    "gate_res_ohm",
    "bootstrap_cap_nf",
    "driver_part",
    "mosfet_part"
  ],
  "outputs": [
    "v_bootstrap_min",
    "vgs_high_peak",
    "switch_node_overshoot"
  ],
  "limitations": [
    "Does not include PCB extracted parasitics by default.",
    "Requires manual parasitic estimate for layout-sensitive conclusions."
  ],
  "version": "1.0.0"
}
```

---

## 4. Simulation Run

用于跟踪一次执行实例。

```json
{
  "simulation_run_id": "simrun_001",
  "simulation_request_id": "simreq_20260321_001",
  "tool": "ngspice",
  "status": "completed",
  "started_at": "2026-03-21T14:00:00+08:00",
  "ended_at": "2026-03-21T14:02:10+08:00",
  "runtime_seconds": 130,
  "execution_mode": "batch",
  "input_bundle_path": "/sim_runs/simrun_001/input/",
  "output_bundle_path": "/sim_runs/simrun_001/output/",
  "log_path": "/sim_runs/simrun_001/logs/run.log",
  "sweep_instances": 9,
  "retry_count": 0
}
```

建议状态枚举：

1. `queued`
2. `running`
3. `completed`
4. `failed`
5. `partial`
6. `cancelled`

---

## 5. Simulation Result

```json
{
  "simulation_result_id": "simres_001",
  "simulation_run_id": "simrun_001",
  "overall_status": "risk",
  "summary": "Bootstrap margin is acceptable at nominal bus voltage, but switch-node overshoot exceeds threshold at high voltage and high temperature corner.",
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
    "bus_voltage": 60,
    "temperature": 125,
    "gate_res_ohm": 5.1
  },
  "waveform_refs": [
    {
      "signal": "switch_node",
      "path": "/sim_runs/simrun_001/output/switch_node.csv"
    },
    {
      "signal": "gate_high",
      "path": "/sim_runs/simrun_001/output/gate_high.csv"
    }
  ],
  "derived_insights": [
    "Overshoot is sensitive to estimated loop inductance.",
    "Increasing gate resistance may reduce ringing but could increase switching loss."
  ]
}
```

---

## 6. Simulation Finding

用于与主审核输出的 `findings` 对接。

```json
{
  "simulation_finding_id": "simfd_001",
  "linked_task_finding_id": "fd_002",
  "category": "gate_drive",
  "severity": "high",
  "title": "Switch-node overshoot exceeds acceptable margin under high-voltage corner",
  "description": "The simulated switch-node overshoot exceeds the configured threshold at 60V and 125C equivalent corner, indicating potential device stress and EMI risk.",
  "root_cause_hypotheses": [
    "power loop inductance too high",
    "gate drive too aggressive",
    "snubber not sufficient"
  ],
  "recommended_actions": [
    "recheck DC bus capacitor placement and loop area",
    "evaluate gate resistor increase",
    "consider RC snubber or clamp review"
  ],
  "evidence_refs": [
    "simres_001"
  ],
  "confidence": 0.82
}
```

---

## 7. 系统级仿真请求示例

```json
{
  "simulation_request_id": "simreq_sys_001",
  "task_id": "task_20260321_010",
  "task_type": "design_advice",
  "motor_type": "bldc",
  "simulation_level": "system",
  "simulation_goal": "Compare startup, stall, regenerative braking and current-loop tracking performance under candidate topology A and B.",
  "selected_tool": "plecs",
  "template_id": "tpl_bldc_3phase_foc_drive_v1",
  "parameter_bindings": {
    "bus_voltage_v": 48,
    "rated_power_w": 750,
    "pole_pairs": 4,
    "phase_resistance_ohm": 0.18,
    "phase_inductance_mh": 0.42,
    "bemf_constant_vll_krpm": 18,
    "control_mode": "foc"
  },
  "scenarios": [
    "startup_no_load",
    "rated_load",
    "stall_event",
    "regen_braking"
  ],
  "measurements": [
    "phase_current_peak",
    "torque_ripple_pct",
    "speed_overshoot_pct",
    "dc_bus_ripple_v",
    "fault_trip_time_us"
  ]
}
```

---

## 8. 统一判定对象

建议将所有仿真结果最终归一到统一判定结构，便于前端和评测使用。

```json
{
  "judgement": {
    "status": "risk",
    "score": 0.68,
    "rationale": "Core functionality passes, but margin at high-stress corner is insufficient.",
    "must_fix": [
      "switch_node_overshoot"
    ],
    "should_review": [
      "loop_inductance_estimation",
      "snubber_selection"
    ]
  }
}
```

---

## 9. API 草案

### 9.1 创建仿真请求

`POST /api/simulations/requests`

### 9.2 查询仿真状态

`GET /api/simulations/runs/{simulation_run_id}`

### 9.3 查询仿真结果

`GET /api/simulations/results/{simulation_result_id}`

### 9.4 重新执行

`POST /api/simulations/runs/{simulation_run_id}/rerun`

### 9.5 导出与任务关联的所有仿真证据

`GET /api/tasks/{task_id}/simulation-evidence`

---

## 10. 存储建议

建议目录结构：

```text
sim_runs/
  simrun_001/
    input/
    output/
    logs/
    metrics.json
    result.json
```

数据库建议至少存：

1. 请求对象
2. 运行状态
3. 结果摘要
4. 指标明细
5. 文件路径引用
6. 与主任务的关联关系

---

## 11. 与主审核 JSON 的整合建议

建议在主任务输出里新增：

```json
{
  "simulation_summary": {
    "executed": true,
    "simulation_runs": 3,
    "tools": ["ngspice", "plecs"],
    "top_risks_confirmed_by_simulation": [
      "switch_node_overshoot",
      "ocp_trip_margin"
    ],
    "inconclusive_items": [
      "layout_parasitic_actual_value"
    ]
  }
}
```

---

## 12. 版本管理建议

每次仿真结论都必须带：

1. 模板版本
2. 工具版本
3. 模型版本
4. 参数集版本
5. 判定规则版本

否则后续无法做可靠回归。
