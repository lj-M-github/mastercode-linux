# 可测量指标实现指南

## 指标收集架构

可测量指标的收集由三层组件负责：

### 1. 数据来源层

#### `RetryController` (`src/control/retry_controller.py`)
- **`rule_attempts`**: 字典，记录每个 rule_id 的重试次数
- **`failure_history`**: 列表，存储所有 `FailureRecord`，包含：
  - 时间戳
  - 失败类型（SYNTAX_ERROR, PERMISSION_ERROR 等）
  - 错误信息
  - 尝试编号
  
- **关键方法**:
  ```python
  def get_retry_statistics() -> Dict[str, Any]
  # 返回: total_attempts, rules_attempted, average_attempts_per_rule
  
  def get_failure_pattern(rule_id) -> Dict[str, Any]
  # 返回: total_failures, most_common_failure, failure_distribution
  ```

#### `StateManager` (`src/control/state_manager.py`)
- **`transition_history`**: 列表，记录所有状态转换 `StateTransition`
- **`rule_states`**: 字典，当前每个 rule_id 的状态

- **关键方法**:
  ```python
  def get_transition_history(rule_id) -> List[StateTransition]
  # 返回: 该 rule 的所有状态转换记录
  ```

#### `DriftAuditor` (`src/compliance/drift_auditor.py`)
- **`audit_rule(rule_id)`**: 执行审计，返回 `DriftResult`
  - `is_compliant`: 布尔值
  - `drifts`: 漂移列表，每个包含 key, expected, actual, comparison_type
  - `actual_output`: 命令实际输出

### 2. 指标聚合层

#### `ExperimentalEvaluator` (`src/metrics/evaluation.py`)

负责从各层收集数据并计算可测量指标。

**核心方法**:

```python
def collect_metrics(orchestrator, rule_id, initial_drift_count, start_time) -> MetricSnapshot
# 收集单个 rule 的完整指标
# 返回: MetricSnapshot 包含所有关键指标

def get_initial_compliance_rate() -> float
# 计算: 修复前通过审计的规则百分比

def get_autonomous_success_rate() -> float
# 计算: 通过 AI 生成修复成功的漂移百分比

def get_average_retry_count() -> float
# 计算: 每个规则的平均重试次数

def get_average_convergence_time() -> float
# 计算: 漂移检测到合规达成的平均时间

def get_drift_resolution_rate() -> Dict
# 计算: 初始漂移 -> 最终漂移的解决率

def get_failure_analysis() -> Dict
# 分析: 错误类型分布

def get_state_transition_analysis() -> Dict
# 分析: 最终状态分布

def generate_summary_report() -> Dict
# 生成: 完整的实验报告
```

### 3. 指标存储与输出

```python
def save_metrics_to_file(filename="metrics_report.json")
# 保存摘要报告到 JSON

def save_detailed_metrics_to_file(filename="metrics_detailed.json")
# 保存详细的每 rule 指标到 JSON

def print_summary()
# 打印人类可读的总结
```

## 在测试中体现指标

### 方式1: 单元测试（`tests/test_metrics.py`）

```python
def test_measurable_metrics_collection():
    evaluator = ExperimentalEvaluator()
    
    # 模拟多个 rule 的 remediation
    for rule_id, success, attempts in scenarios:
        snapshot = evaluator.collect_metrics(
            orchestrator, 
            rule_id,
            initial_drift_count,
            start_time
        )
    
    # 验证指标计算正确
    assert evaluator.get_autonomous_success_rate() == expected
    assert evaluator.get_average_retry_count() == expected
```

### 方式2: 集成测试

```python
def test_end_to_end_with_metrics():
    agent = SecurityHardeningAgent(config)
    evaluator = ExperimentalEvaluator()
    
    # 执行完整工作流
    start = time.time()
    result = agent.harden("SSH configuration", target_host="localhost")
    
    # 收集指标
    for rule in result['results']:
        evaluator.collect_metrics(
            agent.orchestrator,
            rule['rule_id'],
            initial_drifts,
            start
        )
    
    # 生成报告
    report = evaluator.generate_summary_report()
    evaluator.save_detailed_metrics_to_file()
```

### 方式3: 实验脚本运行

```bash
# 创建 experiment_runner.py
source venv/bin/activate
python3 experiments/run_experiment.py \
    --rules-file data/compliance_checks/cis_rhel9_checks.yaml \
    --output-dir ./experiment_results \
    --num-runs 3
```

## 指标数据流

```
Orchestrator.process_rule(rule_id)
    ↓
RetryController.should_retry() ← 记录重试次数
RetryController.record_failure() ← 记录错误
    ↓
StateManager.transition() ← 记录状态转换
    ↓
DriftAuditor.audit_rule() ← 获取最终漂移计数
    ↓
ExperimentalEvaluator.collect_metrics()
    ↓
MetricSnapshot {
    rule_id, 
    attempts, 
    success, 
    convergence_time_sec,
    drift_count_initial/final,
    failures,
    state_transitions
}
    ↓
generate_summary_report() → JSON
```

## 论文中的使用

### 表格示例

| Metric | Value | Unit | Interpretation |
|--------|-------|------|-----------------|
| Initial Compliance Rate | 30% | % | 70% 规则初始非合规 |
| Autonomous Success Rate | 85% | % | 85% 漂移被自动修复 |
| Average Retry Count | 1.8 | attempts | 平均 1.8 次尝试 |
| Avg Convergence Time | 12.5 | seconds | 12.5秒达到收敛 |
| Drift Resolution Rate | 92% | % | 92% 漂移完全解决 |

### 分析示例

```
实验结果表明：
1. 初始合规率为30%，说明选定的规则集具有代表性的非合规情况
2. 自主成功率85%表明框架的AI修复能力提升了15%的规则
3. 平均重试次数1.8小于理论最大值3，说明收敛有效
4. 平均收敛时间12.5秒在可接受范围内
```

## 关键注意事项

1. **确定性**: 所有指标基于确定性审计，结果可重复
2. **隔离性**: 每个 rule 的指标独立收集，不相互影响
3. **完整性**: 包括成功和失败路径的所有指标
4. **可追溯性**: 每个指标都能追溯到原始 DriftResult 和状态转换
