# 电机控制仿真任务模板库（首批 20 项）（V0.1）

## 1. 目标

本文档给出首批建议纳入智能体的自动仿真任务模板，目标是优先覆盖高价值、高复用、最能体现工程专家价值的场景。

建议首批模板分三组：

1. 电路级模板
2. 系统级模板
3. 测试映射模板

---

## 2. 电路级模板

### 2.1 Bootstrap 裕量验证

- `template_id`: `tpl_half_bridge_bootstrap_v1`
- 适用：BLDC / 伺服三相逆变器
- 目标：验证高侧 bootstrap 在最低占空、最高温度、最大电压下是否有足够裕量
- 关键输入：母线电压、开关频率、占空比、驱动器参数、bootstrap 电容、MOSFET 参数
- 输出指标：`v_bootstrap_min`、`uvlo_margin`
- 典型结论：`pass` / `risk` / `fail`

### 2.2 栅极振铃与过冲验证

- `template_id`: `tpl_gate_ringing_v1`
- 适用：BLDC / 伺服 / 步进功率级
- 目标：识别过冲、振铃、误导通风险
- 关键输入：栅阻、回路寄生、驱动能力、MOSFET Qg / Cgd
- 输出指标：`vgs_peak`、`vds_overshoot`、`ringing_cycles`

### 2.3 栅阻敏感性扫描

- `template_id`: `tpl_gate_resistor_sweep_v1`
- 目标：找到开关损耗、过冲、EMI 风险之间的平衡点
- 扫描建议：2R、5R、10R、20R
- 输出指标：`switching_loss`、`overshoot`、`dvdt_estimate`

### 2.4 DC Bus 高频回路敏感性分析

- `template_id`: `tpl_bus_loop_parasitic_v1`
- 目标：验证母线电容位置变化或寄生电感变化对过冲的影响
- 输出指标：`switch_node_overshoot`、`bus_ripple_peak`

### 2.5 分流采样恢复时间验证

- `template_id`: `tpl_shunt_recovery_v1`
- 适用：低边采样 / 相电流采样前端
- 目标：验证开关瞬态后采样前端是否在有效采样窗口内恢复
- 输出指标：`settling_time_ns`、`sample_error_pct`

### 2.6 运放饱和恢复风险验证

- `template_id`: `tpl_amp_saturation_recovery_v1`
- 目标：验证过流或共模扰动后运放恢复时间
- 输出指标：`recovery_time_us`、`output_clamp_margin`

### 2.7 OCP 阈值与响应时间验证

- `template_id`: `tpl_ocp_chain_v1`
- 目标：验证比较器、门极驱动器、MCU fault path 响应是否满足规格
- 输出指标：`trip_threshold_a`、`trip_delay_us`

### 2.8 UVLO / 上电时序验证

- `template_id`: `tpl_powerup_uvlo_v1`
- 目标：验证上电、掉电、欠压恢复时系统不会误触发功率级
- 输出指标：`safe_enable_window`、`fault_latch_behavior`

### 2.9 编码器 / 霍尔接口抗扰度前端验证

- `template_id`: `tpl_sensor_frontend_noise_v1`
- 适用：伺服 / BLDC 带反馈方案
- 目标：验证接口前端对共模 / 差模扰动的稳健性
- 输出指标：`false_toggle_count`、`noise_margin`

### 2.10 步进双 H 桥电流斩波验证

- `template_id`: `tpl_stepper_chopper_v1`
- 适用：步进电机
- 目标：验证电流斩波阈值、衰减模式、纹波和发热风险
- 输出指标：`coil_current_ripple_pct`、`current_regulation_error`

---

## 3. 系统级模板

### 3.1 BLDC / PMSM 启动工况验证

- `template_id`: `tpl_bldc_startup_v1`
- 目标：验证空载、带载启动成功率和电流冲击
- 输出指标：`startup_time_ms`、`phase_current_peak`、`startup_success`

### 3.2 堵转工况验证

- `template_id`: `tpl_stall_event_v1`
- 目标：验证堵转时保护动作与器件应力
- 输出指标：`trip_time_us`、`current_peak_a`、`thermal_stress_index`

### 3.3 再生制动工况验证

- `template_id`: `tpl_regen_braking_v1`
- 目标：验证母线电压抬升、制动能量处理与保护
- 输出指标：`bus_voltage_peak`、`regen_duration_ms`

### 3.4 电流环跟踪与稳定性验证

- `template_id`: `tpl_current_loop_tracking_v1`
- 目标：验证参考电流变化时的超调和稳定时间
- 输出指标：`tracking_error_pct`、`settling_time_ms`

### 3.5 速度环阶跃响应验证

- `template_id`: `tpl_speed_loop_step_v1`
- 适用：BLDC / 伺服 / 直线电机
- 目标：验证速度超调、响应时间、扰动恢复
- 输出指标：`overshoot_pct`、`rise_time_ms`、`recovery_time_ms`

### 3.6 位置环精度与跟随误差验证

- `template_id`: `tpl_position_following_v1`
- 适用：伺服 / 直线电机
- 目标：验证位置跟随误差、微小位移稳定性、抖动风险
- 输出指标：`position_error_um`、`jitter_um_rms`

### 3.7 弱磁 / 高速区工况验证

- `template_id`: `tpl_field_weakening_v1`
- 适用：BLDC / PMSM
- 目标：验证弱磁区域电流、电压利用率和热风险
- 输出指标：`iq_id_margin`、`bus_utilization_pct`

### 3.8 参数漂移敏感性分析

- `template_id`: `tpl_param_drift_sensitivity_v1`
- 目标：分析相电阻、相电感、反电势常数、温度偏差对控制性能的影响
- 输出指标：`performance_degradation_score`

### 3.9 伺服编码器失步 / 掉脉冲鲁棒性验证

- `template_id`: `tpl_encoder_fault_v1`
- 适用：伺服 / 直线电机
- 目标：验证反馈异常时的故障检测与降级策略
- 输出指标：`fault_detect_latency_ms`、`safe_state_entry`

### 3.10 直线电机定位重复性验证

- `template_id`: `tpl_linear_repeatability_v1`
- 适用：直线电机
- 目标：验证重复定位、往返一致性和跟随误差
- 输出指标：`repeatability_um`、`bidirectional_error_um`

---

## 4. 测试映射模板

### 4.1 仿真到测试点映射

- `template_id`: `tpl_sim_to_lab_measurement_v1`
- 目标：把仿真重点波形映射成台架测试项
- 输出：通道建议、探头建议、触发条件、判据

### 4.2 仿真到边界工况测试矩阵

- `template_id`: `tpl_boundary_case_matrix_v1`
- 目标：把敏感参数组合转成测试优先级矩阵
- 输出：P1 / P2 / P3 测试项

### 4.3 仿真到故障注入测试模板

- `template_id`: `tpl_fault_injection_from_sim_v1`
- 目标：从故障仿真结果生成实测故障注入项
- 输出：触发方式、保护期望、记录字段

### 4.4 仿真到测试报告审核模板

- `template_id`: `tpl_report_gap_check_v1`
- 目标：识别报告是否遗漏仿真已暴露的高风险工况
- 输出：遗漏项清单、建议补测项

---

## 5. 推荐最先上线的 8 个模板

如果资源有限，建议优先做：

1. `tpl_half_bridge_bootstrap_v1`
2. `tpl_gate_ringing_v1`
3. `tpl_shunt_recovery_v1`
4. `tpl_ocp_chain_v1`
5. `tpl_bldc_startup_v1`
6. `tpl_stall_event_v1`
7. `tpl_regen_braking_v1`
8. `tpl_sim_to_lab_measurement_v1`

原因：

1. 与原理图审核和方案建议结合最紧
2. 最容易体现“专家经验 + 仿真证据”的价值
3. 对 BLDC / PMSM 项目覆盖率最高

---

## 6. 模板最小字段建议

每个模板都建议至少包含：

```json
{
  "template_id": "tpl_xxx",
  "name": "xxx",
  "simulation_level": "circuit",
  "applicable_motor_types": ["bldc"],
  "applicable_task_types": ["schematic_review"],
  "required_inputs": ["bus_voltage_v", "gate_res_ohm"],
  "default_sweeps": [
    {
      "name": "temperature",
      "values": [25, 85, 125]
    }
  ],
  "key_measurements": ["switch_node_overshoot"],
  "pass_criteria": [
    {
      "metric": "switch_node_overshoot",
      "operator": "<=",
      "value": 10,
      "unit": "V"
    }
  ],
  "known_limitations": [
    "layout parasitics are estimated unless extraction data is provided"
  ]
}
```

---

## 7. 工程建议

1. 首批模板一定要专家参与定义，不要完全由 AI 自生成
2. 每个模板都要有“适用边界”和“已知局限”
3. 每个模板至少配一个金标准样例
4. 模板升级前要跑回归评测
5. 不要追求模板数量，先追求模板稳定和复用率

---

## 8. 结论

仿真模板库会决定你的智能体到底是“会调用仿真器”，还是“真正会用仿真器解决问题”。

第一阶段最关键的是先把少量高价值模板做扎实，再逐步扩到更多电机类型和更多审核场景。
