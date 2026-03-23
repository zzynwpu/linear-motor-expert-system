# 电机控制专家智能体评测集与评分模板（V0.1）

## 1. 目标

评测集用于回答一个关键问题：系统升级后，是不是“真的更像专家”，而不是“看起来更会说”。

评测目标：

1. 约束模型升级风险
2. 量化规则更新收益
3. 找出误报与漏报来源
4. 支持灰度发布与回滚

---

## 2. 评测对象

每次迭代都建议至少评测以下版本组合：

1. 模型版本
2. Prompt 版本
3. 规则包版本
4. 知识索引版本
5. 文档解析器版本

---

## 3. 评测集组成建议

第一阶段建议准备不少于 200 条样本，按任务和电机类型分层采样。

建议结构：

1. 设计方案建议：40 条
2. 原理图审核：60 条
3. 风险分析：30 条
4. 测试用例输出：30 条
5. Layout 审核预留：20 条
6. 测试报告审核预留：20 条

样本来源建议：

1. 历史优秀项目
2. 历史问题项目
3. 专家评审记录
4. 测试失效案例
5. 公开 reference design 对照样本

---

## 4. 样本标注单元

每条样本建议包含以下内容：

```json
{
  "sample_id": "eval_sch_001",
  "task_type": "schematic_review",
  "motor_type": "bldc",
  "difficulty": "medium",
  "input_artifacts": [
    "schematic_pdf",
    "bom",
    "datasheet_bundle"
  ],
  "ground_truth": {
    "must_find": [
      {
        "title": "bus capacitor placement risk",
        "severity": "high"
      },
      {
        "title": "current shunt routing risk",
        "severity": "high"
      }
    ],
    "acceptable_optional_findings": [
      "gate resistor sizing concern",
      "fault reset path unclear"
    ],
    "must_not_claim": [
      "missing isolation",
      "encoder ESD absent"
    ],
    "expected_evidence_docs": [
      "internal_review_014",
      "vendor_layout_guide_xx"
    ]
  }
}
```

---

## 5. 评分维度

### 5.1 建议主维度

1. 问题召回率
2. 严重度判断准确率
3. 误报率
4. 建议可执行性
5. 证据引用准确率
6. 结构化输出完整性

### 5.2 维度定义

1. 问题召回率
   - 是否找到了标准答案中的关键问题
2. 严重度判断准确率
   - 是否将关键问题分到了合理等级
3. 误报率
   - 是否频繁提出不存在的问题
4. 建议可执行性
   - 建议是否足够具体，是否能指导工程动作
5. 证据引用准确率
   - 证据是否真实相关，是否支持该结论
6. 结构化输出完整性
   - 是否包含结论、发现、建议、证据、假设、缺失信息

---

## 6. 评分表模板

建议每条样本评分 0 到 5 分。

```json
{
  "sample_id": "eval_sch_001",
  "scores": {
    "recall": 4,
    "severity_accuracy": 4,
    "false_positive_control": 3,
    "actionability": 5,
    "evidence_quality": 4,
    "output_completeness": 5
  },
  "reviewer_comments": [
    "Found both critical issues.",
    "One medium-level false positive on isolation."
  ],
  "pass": true
}
```

---

## 7. 自动评分与人工评分结合

建议采用“双层评分”：

1. 自动评分
   - JSON 结构是否完整
   - 关键字段是否齐全
   - 是否命中 `must_find`
   - 是否触发 `must_not_claim`
2. 人工评分
   - 建议是否专业
   - 证据是否合理
   - 严重度是否符合工程经验

---

## 8. 发布门槛建议

第一阶段可采用以下最低门槛：

1. `critical/high` 问题召回率大于等于 85%
2. 关键误报率小于等于 10%
3. 证据引用准确率大于等于 90%
4. 平均总分大于等于 4.0 / 5.0
5. 不允许新增高严重度系统性误报

---

## 9. 专家标注模板

建议专家在标注时使用统一模板：

```json
{
  "sample_id": "eval_sch_001",
  "expert_answer": {
    "summary": "Main risks are in bus loop and current sense path.",
    "findings": [
      {
        "title": "DC bus switching loop too large",
        "severity": "high",
        "why_it_matters": "May cause overshoot and EMI."
      },
      {
        "title": "Current shunt Kelvin intent unclear",
        "severity": "high",
        "why_it_matters": "May distort current measurement."
      }
    ],
    "recommended_actions": [
      "Review loop area around half bridge and ceramic bus capacitor.",
      "Review shunt routing and amplifier input network."
    ],
    "reference_basis": [
      "internal checklist v3.2",
      "vendor layout guide"
    ]
  }
}
```

---

## 10. 回归分析建议

每次版本迭代后建议输出以下分析：

1. 新增命中问题数
2. 新增误报问题数
3. 严重度偏移统计
4. 证据错误引用统计
5. 按电机类型拆分表现
6. 按任务类型拆分表现

---

## 11. 第一阶段实施建议

如果专家时间有限，建议先做 50 条高质量金标准样本，再扩展到 200 条。

优先顺序：

1. BLDC 原理图审核
2. BLDC 方案建议
3. 步进电机原理图审核
4. 风险分析
5. 测试用例生成

---

## 12. 结论

没有评测集的专家智能体很难长期可控。  
第一阶段最值得投入的资产，不是更复杂的 agent，而是：

1. 一组高质量样本
2. 一套统一评分规则
3. 一条固定回归流程

这三件事会决定系统后续能不能稳定跟随大模型升级而持续进化。
