# 电机控制专家智能体统一输出 JSON 规范（V0.1）

## 1. 设计目标

统一输出结构的目的：

1. 方便前端展示
2. 方便人工复核
3. 方便与 PLM / 缺陷单 / 测试系统集成
4. 方便做自动评测

---

## 2. 顶层 Envelope

```json
{
  "task_id": "task_20260321_001",
  "task_type": "schematic_review",
  "motor_type": "bldc",
  "project_name": "48V_750W_controller",
  "input_summary": {
    "artifacts": [
      "schematic_pdf",
      "bom",
      "datasheet_bundle"
    ],
    "constraints": {
      "bus_voltage_v": 48,
      "rated_power_w": 750,
      "control_mode": "foc"
    }
  },
  "overall_conclusion": {
    "summary": "Design is basically feasible but has 2 high-risk issues in current sense and DC bus loop.",
    "readiness": "needs_revision",
    "confidence": 0.84
  },
  "findings": [],
  "recommendations": [],
  "assumptions": [],
  "missing_information": [],
  "evidence": [],
  "risk_summary": {
    "critical": 0,
    "high": 2,
    "medium": 4,
    "low": 3
  },
  "traceability": {
    "model_version": "gpt-5.x",
    "prompt_version": "schematic_review_v0.3",
    "rule_pack_version": "rules_2026_03_21",
    "knowledge_index_version": "kb_2026_03_21"
  },
  "generated_at": "2026-03-21T16:20:00+08:00"
}
```

---

## 3. Finding Schema

```json
{
  "finding_id": "fd_001",
  "title": "Current shunt Kelvin routing intent is unclear",
  "category": "current_sense",
  "severity": "high",
  "priority_score": 88,
  "status": "open",
  "description": "The shunt sense path may share high current return path, which can distort phase current measurement during switching events.",
  "why_it_matters": "This can cause control instability, false overcurrent trigger, and current reconstruction error.",
  "conditions": [
    "applies if low-side shunt is used",
    "applies if amplifier input is directly connected to power return segment"
  ],
  "recommended_action": [
    "Verify true Kelvin pickup points on shunt resistor.",
    "Review amplifier input RC and ground return placement."
  ],
  "evidence_refs": [
    "ev_003",
    "ev_014"
  ],
  "rule_refs": [
    "rule_sch_bldc_014"
  ],
  "confidence": 0.87
}
```

---

## 4. Evidence Schema

```json
{
  "evidence_id": "ev_003",
  "source_type": "vendor_official",
  "document_id": "doc_drv8305_appnote",
  "document_title": "Three-phase motor drive layout guidelines",
  "location": {
    "page": "p7",
    "section": "Current sensing layout"
  },
  "snippet_summary": "Official guidance emphasizes Kelvin sensing and minimizing coupling with switching current return path.",
  "relevance_score": 0.92,
  "trust_level": 0.96
}
```

---

## 5. Recommendation Schema

```json
{
  "recommendation_id": "rec_001",
  "type": "design_change",
  "title": "Move ceramic bus capacitors closer to half bridge switching loop",
  "priority": "high",
  "expected_benefit": [
    "reduce overshoot",
    "reduce EMI",
    "improve switching robustness"
  ],
  "implementation_notes": [
    "Place the high-frequency decoupling capacitor across the power loop with minimum loop area.",
    "Review bulk and ceramic capacitor division."
  ],
  "linked_findings": [
    "fd_002"
  ]
}
```

---

## 6. 各任务专属补充字段

### 6.1 设计方案建议

额外字段建议：

```json
{
  "solution_options": [
    {
      "option_id": "opt_a",
      "name": "Three-phase inverter with integrated gate driver",
      "fit_score": 0.86,
      "pros": [
        "lower complexity",
        "faster bring-up"
      ],
      "cons": [
        "thermal headroom may be limited"
      ],
      "applicable_conditions": [
        "48V bus",
        "power below 1kW"
      ],
      "key_devices": [
        "MCU",
        "gate driver",
        "MOSFET",
        "current shunt"
      ]
    }
  ]
}
```

### 6.2 原理图审核

额外字段建议：

```json
{
  "review_domains": [
    {
      "domain": "gate_drive",
      "status": "risk_found",
      "summary": "Bootstrap and gate resistor design need further review."
    },
    {
      "domain": "protection",
      "status": "pass_with_notes",
      "summary": "Basic OCP and UVLO are present, but fault propagation path should be confirmed."
    }
  ]
}
```

### 6.3 Layout 审核

额外字段建议：

```json
{
  "layout_regions": [
    {
      "region_id": "power_stage_top",
      "risk_level": "high",
      "issues": [
        "switch loop too large",
        "gate return path not obvious"
      ]
    }
  ]
}
```

### 6.4 风险分析

额外字段建议：

```json
{
  "risk_register": [
    {
      "risk_id": "risk_001",
      "failure_mode": "phase current measurement distortion",
      "effect": "unstable torque control and false protection trip",
      "cause": "poor sense routing and amplifier saturation margin",
      "detection": "dynamic current waveform check and fault injection",
      "mitigation": [
        "kelvin routing",
        "gain review",
        "filter review"
      ],
      "severity": 8,
      "occurrence": 5,
      "detection_score": 4,
      "rpn": 160
    }
  ]
}
```

### 6.5 测试用例输出

额外字段建议：

```json
{
  "test_cases": [
    {
      "case_id": "tc_001",
      "category": "protection",
      "title": "Overcurrent trip threshold verification",
      "purpose": "Verify trip threshold and response time under controlled overload condition.",
      "preconditions": [
        "board assembled",
        "fault logging enabled"
      ],
      "steps": [
        "set rated operating mode",
        "increase load current to threshold",
        "record trip behavior"
      ],
      "expected_result": [
        "trip occurs within spec",
        "fault status is latched as designed"
      ],
      "priority": "high"
    }
  ]
}
```

### 6.6 测试报告审核

额外字段建议：

```json
{
  "report_review": {
    "coverage_assessment": "partial",
    "data_quality_assessment": "acceptable_with_gaps",
    "conclusion_validity": "not_yet_sufficient",
    "gaps": [
      "No clear boundary condition coverage",
      "Protection recovery behavior not demonstrated"
    ]
  }
}
```

---

## 7. 严重度枚举建议

```json
[
  "critical",
  "high",
  "medium",
  "low",
  "info"
]
```

建议含义：

1. `critical`
   - 很可能导致损坏、安全问题或重大项目风险
2. `high`
   - 很可能导致功能失败、可靠性问题或显著性能退化
3. `medium`
   - 需要修正，否则可能导致调试困难或边界失效
4. `low`
   - 优化项或一致性问题
5. `info`
   - 提醒项或待确认项

---

## 8. 置信度与人工复核建议

建议要求：

1. `critical` 和 `high` 发现必须人工复核
2. 低于 0.70 的置信度默认标为待确认
3. 未找到足够证据时可以输出“怀疑项”，但必须与明确问题分开

---

## 9. 前端展示建议

前端建议按以下方式展示：

1. 总体结论卡片
2. 高风险发现优先列表
3. 按专业域分组的审核结果
4. 证据侧栏
5. 假设与缺失信息区域
6. 专家确认与反馈按钮

---

## 10. 实施建议

第一阶段不要追求所有任务字段齐全，建议先稳定以下最小结构：

1. 顶层 Envelope
2. `findings`
3. `recommendations`
4. `evidence`
5. `traceability`

这五部分足以支撑第一版系统、前端和评测闭环。
