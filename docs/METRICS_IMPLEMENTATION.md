# 可测量指标责任链

## 快速概览

| 组件 | 文件 | 职责 | 输出 |
|------|------|------|------|
| **DriftAuditor** | `src/compliance/drift_auditor.py` | 审计合规状态，生成DriftResult | `is_compliant`, `drifts[]` |
| **RetryController** | `src/control/retry_controller.py` | 记录重试、失败，计算重试统计 | `rule_attempts`, `failure_history` |
| **StateManager** | `src/control/state_manager.py` | 管理状态转换，记录历史 | `transition_history`, 状态分布 |
| **Orchestrator** | `src/control/orchestrator.py` | 协调各层，调用审计和重试 | 集成所有数据 |
| **ExperimentalEvaluator** | `src/metrics/evaluation.py` | 聚合指标，生成报告 | 6个可测量指标 + JSON报告 |

## 指标收集流程

```
user: agent.harden() or agent.audit_compliance()
    ↓
[Control Layer]
Orchestrator.process_rule(rule_id)
    ├─ audit_compliance() → [Deterministic Layer]
    │  └─ DriftAuditor.audit_rule()
    │     ├─ Execute: shell command
    │     ├─ Compare: expected vs actual
    │     └─ Return: DriftResult {is_compliant, drifts[]}
    │        ✓ 指标: is_compliant, drift_count_initial
    │
    ├─ generate_remediation() → [AI Layer] 
    │  └─ LLM生成playbook
    │
    ├─ execute_remediation() → [Executor]
    │  └─ Ansible execution
    │     └─ record_failure() if failed
    │        ✓ 指标: failure_type, attempts
    │
    ├─ verify_remediation() → [Deterministic Layer]
    │  └─ DriftAuditor.audit_rule() again
    │     └─ Return: DriftResult {is_compliant, drifts[]}
    │        ✓ 指标: drift_count_final, convergence_time
    │
    └─ StateManager记录所有状态转换
       ✓ 指标: state_transitions, final_state
    
[Metrics Layer]
ExperimentalEvaluator.collect_metrics()
    ├─ 从上述所有组件收集数据
    ├─ 创建MetricSnapshot
    └─ 计算所有6个可测量指标
       ✓ Initial Compliance Rate
       ✓ Autonomous Success Rate
       ✓ Average Retry Count
       ✓ Convergence Time
       ✓ Drift Resolution Rate
       ✓ Failure Analysis
    
[Output]
JSON Report / Print Summary
```

## 代码追踪示例

### 示例1: 获取平均重试次数

```python
# Step 1: 每次重试在 RetryController 中记录
# orchestrator.py, line ~125
if exec_result['success']:
    ...
else:
    failure_type = self.retry_controller.categorize_error(result.get('error', ''))
    self.retry_controller.record_failure(
        rule_id=rule_id,  # ← 记录 rule_id
        error_message=result.get('error', ''),
        failure_type=failure_type
    )
    # RetryController 内部:
    # self.rule_attempts[rule_id] += 1  ← 增加计数

# Step 2: 计算统计
# retry_controller.py, line ~137
def get_retry_statistics() -> Dict[str, Any]:
    total_attempts = sum(self.rule_attempts.values())
    rules_attempted = len(self.rule_attempts)
    avg_attempts = total_attempts / rules_attempted if rules_attempted > 0 else 0
    return {..., "average_attempts_per_rule": avg_attempts}

# Step 3: 聚合到指标中
# evaluation.py, line ~110
def get_average_retry_count(self) -> float:
    if not self.snapshots:
        return 0.0
    total_attempts = sum(s.attempts for s in self.snapshots)
    return total_attempts / len(self.snapshots)
```

### 示例2: 获取收敛时间

```python
# Step 1: 记录漂移和执行时间
# orchestrator.py, process_rule()
start_time = time.time()  # 开始处理

audit_results = self.audit_compliance([rule_id])
drift_result = audit_results[0]
# drift_result.drifts 包含初始漂移

# ... 执行remediation循环 ...

# Step 2: 完成后记录时间
convergence_time = time.time() - start_time

# Step 3: 在指标中记录
# evaluation.py
snapshot = MetricSnapshot(
    ...,
    convergence_time_sec=convergence_time,
    drift_count_initial=len(initial_drifts),
    drift_count_final=len(final_drifts),
    ...
)
```

### 示例3: 获取成功率

```python
# Step 1: 追踪每个rule的成功/失败
# orchestrator.py, verify_remediation()
if verification_result.is_compliant:
    self.state_manager.transition(
        ComplianceState.REMEDIATION_SUCCEEDED,  ← 标记成功
        ...
    )
    # compliance = True
else:
    self.state_manager.transition(
        ComplianceState.VERIFICATION_FAILED,  ← 标记失败
        ...
    )
    # compliance = False

# Step 2: 计算成功率
# evaluation.py
def get_autonomous_success_rate(self) -> float:
    non_compliant = [s for s in self.snapshots if not s.initial_compliance]
    successful = sum(1 for s in non_compliant if s.success)
    return successful / len(non_compliant) if non_compliant else 0.0
```

## 在论文中的使用

### 表格生成

```python
# 来自 evaluation.py 的输出
report = evaluator.generate_summary_report()

# 论文表格
metrics = report['metrics']
print(f"| Initial Compliance Rate | {metrics['initial_compliance_rate_pct']:.1f}% |")
print(f"| Autonomous Success Rate | {metrics['autonomous_success_rate_pct']:.1f}% |")
print(f"| Average Retry Count | {metrics['average_retry_count']:.2f} |")
print(f"| Average Convergence Time | {metrics['average_convergence_time_sec']:.2f}s |")
```

### 实验对比

```python
# 不同配置下的对比
experiment1 = run_experiment(agent_with_rag, ...)
experiment2 = run_experiment(agent_without_rag, ...)

print("RAG Impact Analysis:")
print(f"Success Rate: {experiment1['success_rate']:.1%} vs {experiment2['success_rate']:.1%}")
print(f"Avg Retries: {experiment1['avg_retries']:.2f} vs {experiment2['avg_retries']:.2f}")
```

## 测试中的体现

### 1. 单元测试 (`tests/test_metrics.py`)

```python
def test_measurable_metrics_collection():
    """验证指标正确收集"""
    evaluator = ExperimentalEvaluator()
    
    # 创建多个快照
    for ...:
        snapshot = evaluator.MetricSnapshot(...)
        evaluator.snapshots.append(snapshot)
    
    # 验证计算
    assert evaluator.get_autonomous_success_rate() == expected_value
```

### 2. 集成测试

```python
def test_end_to_end_metrics():
    agent = SecurityHardeningAgent()
    runner = ExperimentRunner()
    
    # 执行完整实验
    results = runner.run_single_experiment(agent, rule_ids)
    
    # 验证指标生成
    assert 'metrics' in results
    assert 'autonomous_success_rate_pct' in results['metrics']
```

### 3. 实验脚本

```bash
# 运行实验集
source venv/bin/activate
python3 experiments/run_experiment.py \
    --num-runs 3 \
    --num-rules 5 \
    --output-dir ./thesis_experiments
```

## 关键代码位置

| 指标 | 主要代码位置 |
|-----|----------|
| 初始合规率 | `evaluation.py:96-100` |
| 自主成功率 | `evaluation.py:102-112` |
| 平均重试次 | `evaluation.py:114-120` |
| 收敛时间 | `evaluation.py:122-128`, `orchestrator.py:280+` |
| 漂移解决率 | `evaluation.py:130-142` |
| 失败分析 | `evaluation.py:144-156`, `retry_controller.py:112-135` |

## 实时查看指标

```python
from src.main_agent import SecurityHardeningAgent
from src.metrics.evaluation import ExperimentalEvaluator

agent = SecurityHardeningAgent()
evaluator = ExperimentalEvaluator()

# 执行修复
result = agent.harden("SSH configuration", target_host="localhost")

# 收集指标
for rule in result['results']:
    evaluator.collect_metrics(agent.orchestrator, rule['rule_id'], 1, time.time())

# 实时查看
evaluator.print_summary()

# 保存报告
evaluator.save_detailed_metrics_to_file()
```
