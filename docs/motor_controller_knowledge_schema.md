# 电机控制专家智能体知识库 Schema（V0.1）

## 1. 设计目标

知识库不是简单的向量库，而是一套“文档 + 元数据 + 规则 + 案例 + 结构化实体”的组合模型。

设计目标：

1. 支持多来源知识统一治理
2. 支持权限控制
3. 支持按电机类型和任务类型过滤
4. 支持证据追溯
5. 支持版本管理

---

## 2. 核心对象

建议至少设计以下对象：

1. `document`
2. `document_chunk`
3. `rule`
4. `case_record`
5. `component`
6. `topology`
7. `review_pattern`
8. `test_template`

---

## 3. Document Schema

```json
{
  "document_id": "doc_001",
  "title": "DRV8305 BLDC inverter design review checklist",
  "source_type": "internal_feishu",
  "source_uri": "feishu://wiki/space/node",
  "source_domain": "internal",
  "publisher": "motor_hw_team",
  "author": ["alice", "bob"],
  "language": "zh-CN",
  "doc_type": "design_review_note",
  "publish_date": "2026-03-01",
  "version": "v3.2",
  "confidentiality": "internal",
  "quality_grade": "A",
  "trust_level": 0.95,
  "motor_types": ["bldc", "servo"],
  "task_types": ["design_advice", "schematic_review"],
  "topology_tags": ["3phase_inverter", "current_shunt_low_side"],
  "voltage_range_v": [24, 72],
  "power_range_w": [100, 1500],
  "controller_tags": ["foc", "sensorless", "hall"],
  "component_tags": ["mosfet", "gate_driver", "current_sense_amp"],
  "keywords": ["bootstrap", "deadtime", "overcurrent"],
  "status": "active",
  "checksum": "sha256:xxxx",
  "ingested_at": "2026-03-21T10:00:00Z"
}
```

字段说明：

1. `source_type`
   - `internal_feishu`
   - `internal_file`
   - `vendor_official`
   - `paper`
   - `web_curated`
2. `quality_grade`
   - `A` 表示优先参考
   - `B` 表示可参考
   - `C` 表示仅作补充
3. `trust_level`
   - 取值 0 到 1，用于排序和证据权重

---

## 4. Document Chunk Schema

```json
{
  "chunk_id": "chunk_001",
  "document_id": "doc_001",
  "section_title": "Bootstrap supply constraints",
  "chunk_index": 12,
  "page_ref": "p8",
  "heading_path": ["Power Stage", "Gate Driver", "Bootstrap"],
  "content": "Bootstrap capacitor should be placed close to HB and HS pins...",
  "token_count": 182,
  "embedding_model": "text-embedding-3-large",
  "has_formula": false,
  "has_table": true,
  "retrieval_tags": ["bootstrap", "gate_driver", "layout"],
  "applicability": {
    "motor_types": ["bldc", "servo"],
    "task_types": ["schematic_review", "layout_review"]
  }
}
```

---

## 5. Rule Schema

规则应显式化，不应仅存在于 prompt 中。

```json
{
  "rule_id": "rule_sch_bldc_001",
  "name": "DC bus capacitor too far from half bridge",
  "task_type": "schematic_review",
  "motor_types": ["bldc", "servo"],
  "domain": "power_stage",
  "severity": "high",
  "priority": 90,
  "preconditions": [
    "three_phase_inverter=true"
  ],
  "signals_or_objects": [
    "dc_bus_cap",
    "half_bridge",
    "switch_node"
  ],
  "trigger_logic": "distance(dc_bus_cap, half_bridge) > threshold",
  "risk": "Switching current loop inductance increases, causing overshoot and EMI risk.",
  "recommendation": "Place ceramic and bulk bus capacitors close to MOSFET half bridge current loop.",
  "references": [
    "doc_ti_xxx",
    "internal_review_2025_014"
  ],
  "version": "1.0.0",
  "status": "active",
  "owner": "hw_rule_team"
}
```

---

## 6. Case Record Schema

案例库是让系统“更像公司专家”的关键资产。

```json
{
  "case_id": "case_2025_021",
  "project_name": "48V servo controller A",
  "motor_types": ["servo"],
  "task_types": ["schematic_review", "risk_analysis"],
  "summary": "Overcurrent false trigger caused by poor shunt routing and amplifier saturation.",
  "problem_tags": ["current_sense", "layout", "false_trip"],
  "root_cause": "Kelvin routing not preserved and RC filter corner frequency too low.",
  "fix_actions": [
    "reroute shunt Kelvin traces",
    "adjust amplifier input filter",
    "update trip threshold validation"
  ],
  "evidence_docs": ["doc_123", "doc_124"],
  "review_outcome": "fixed",
  "quality_grade": "A",
  "lessons_learned": [
    "Current sense path should be reviewed with power return path together."
  ]
}
```

---

## 7. Component Schema

```json
{
  "component_id": "cmp_drv8305",
  "manufacturer": "TI",
  "part_number": "DRV8305",
  "category": "gate_driver",
  "supported_motor_types": ["bldc", "servo"],
  "key_features": [
    "3phase gate driver",
    "protection integration",
    "SPI diagnostics"
  ],
  "voltage_limit_v": [6, 45],
  "related_documents": ["doc_drv8305_ds", "doc_drv8305_appnote"],
  "common_risks": [
    "bootstrap sizing",
    "fault pin handling",
    "SPI configuration mismatch"
  ]
}
```

---

## 8. Topology Schema

```json
{
  "topology_id": "topo_3phase_inverter_low_side_shunt",
  "name": "Three-phase inverter with low-side shunt",
  "motor_types": ["bldc", "servo"],
  "domains": [
    "power_stage",
    "current_sense",
    "gate_drive",
    "protection"
  ],
  "key_review_points": [
    "deadtime",
    "bootstrap",
    "current reconstruction limits",
    "short-circuit protection"
  ],
  "related_rules": [
    "rule_sch_bldc_001",
    "rule_sch_bldc_002"
  ]
}
```

---

## 9. Review Pattern Schema

用于沉淀常见评审问题模式。

```json
{
  "pattern_id": "pat_layout_gate_loop_001",
  "task_type": "layout_review",
  "domain": "gate_drive",
  "title": "Gate loop too large",
  "symptoms": [
    "gate trace too long",
    "return path discontinuity",
    "switch node coupling"
  ],
  "risks": [
    "ringing",
    "EMI",
    "false turn-on"
  ],
  "recommended_checks": [
    "verify gate resistor placement",
    "verify driver-to-fet loop area",
    "verify Kelvin source handling"
  ],
  "related_rules": [
    "rule_layout_gate_001"
  ]
}
```

---

## 10. Test Template Schema

```json
{
  "template_id": "test_tpl_ocp_001",
  "motor_types": ["bldc", "servo", "stepper"],
  "task_type": "test_case_generation",
  "category": "protection",
  "title": "Overcurrent protection trigger and recovery",
  "preconditions": [
    "rated_bus_voltage configured",
    "current limit configured"
  ],
  "stimulus": [
    "inject controlled overload current",
    "record trigger threshold and response time"
  ],
  "expected_result": [
    "trip within threshold",
    "fault latch behavior matches spec",
    "no component damage"
  ],
  "applicable_topologies": [
    "3phase_inverter",
    "hbridge"
  ]
}
```

---

## 11. 推荐标签体系

### 11.1 电机类型标签

1. `stepper`
2. `bldc`
3. `servo`
4. `linear_motor`

### 11.2 任务类型标签

1. `design_advice`
2. `schematic_review`
3. `layout_review`
4. `risk_analysis`
5. `test_case_generation`
6. `test_report_review`

### 11.3 专业域标签

1. `power_stage`
2. `gate_drive`
3. `current_sense`
4. `voltage_sense`
5. `protection`
6. `control_interface`
7. `feedback_sensor`
8. `isolation`
9. `emc`
10. `thermal`
11. `firmware_config`
12. `safety`

---

## 12. 飞书接入建议

飞书文档接入建议采用“同步到内部知识层”的方式，而不是每次请求时实时抓取全文。

建议流程：

1. 使用飞书 OpenAPI 枚举 Wiki space 与 node
2. 拉取文档内容与元数据
3. 保存源文档 ID、更新时间、权限范围
4. 增量同步变更
5. 入库前做清洗和质量打标

建议额外保留字段：

1. `feishu_space_id`
2. `feishu_node_token`
3. `feishu_obj_type`
4. `feishu_owner`
5. `last_synced_at`
6. `permission_scope`

---

## 13. 知识治理建议

1. 所有文档入库时自动打来源级别
2. 所有案例进入案例库前必须有人工确认
3. 所有规则变更必须有版本号和责任人
4. 外部文档默认不高于内部正式结论的权重
5. 过期文档不删除，但要标记 `deprecated`

---

## 14. 最小可落地建表建议

第一阶段至少落四张核心表：

1. `documents`
2. `document_chunks`
3. `rules`
4. `case_records`

这四张表足以支撑第一版的检索、审核、证据引用和专家反馈闭环。
