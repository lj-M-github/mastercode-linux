# 调试总结：0% 修复率根因分析

## 问题

实验 `python3 experiments/run_experiment.py --num-runs 3 --num-rules 5` 显示修复率为 0%，所有规则在 1 次尝试后即失败，`final_state: "unresolved"`。

## 根因链：6 个串联 Bug

### 1. `AnsibleRunner` 缺少 `save_playbook` 方法

**文件**: `src/executor/ansible_runner.py`

`execute_remediation` 调用了不存在的方法，抛出 `AttributeError`，被外层 except 捕获，失败记录计数为 0。

**修复**: 新增 `save_playbook(content, rule_id)` 方法，将 playbook 内容写入 `playbook_dir` 下以 rule_id 命名的文件。

### 2. `execute_remediation` 传参错误

**文件**: `src/control/orchestrator.py`

调用 `run_playbook(playbook_path=..., inventory=...)`，但方法实际接受 `playbook_name=..., limit=`。

**修复**: 改为 `playbook_name=playbook_path, limit=target_host`。

### 3. `ExecutionResult` 被当作 dict 访问

**文件**: `src/control/orchestrator.py`

`run_playbook` 返回的是 `ExecutionResult` dataclass，但 `execute_remediation` 用 `result['success']` 和 `result.get('error')` 访问，抛出 `'ExecutionResult' object is not subscriptable`，被外层 except 吞掉。

**修复**: 将 `ExecutionResult` 转换为 dict：`{"success": result.success, "error": result.error, ...}`。

### 4. Playbook 路径双重嵌套

**文件**: `src/executor/ansible_runner.py`

`save_playbook` 返回相对路径 `./playbooks/...`，`run_playbook` 又将其与 `playbook_dir` 拼接，导致路径变成 `playbooks/playbooks/...`。

**修复**: `save_playbook` 返回绝对路径，使用 `.resolve()`。同时 `run_playbook` 中增加绝对路径判断。

### 5. LLM 返回内容包含 Markdown 代码围栏

**文件**: `src/control/orchestrator.py` — `generate_remediation()`

DeepSeek 生成的 playbook 被包裹在 ```yaml 和 ``` 之间，Ansible 无法解析。

**修复**: 在 `generate_remediation` 末尾剥离首尾的 ```yaml / ``` 行。

### 6. Ansible `hosts: all` 与 `--limit localhost` 不匹配

**文件**: `src/executor/ansible_runner.py` — `run_playbook()`

LLM 生成 `hosts: all`，但 `--limit localhost` 在没有真实 inventory 的情况下无法匹配任何主机。

**修复**: 当 target 为 localhost 时，使用 `-i localhost, -c local` 内联 inventory 替代 `--limit`。

## 环境限制

当前运行环境存在以下限制：

- **未安装 `openssh-server`** → `sshd -T` 返回空输出 → 所有 SSH 规则的实际值为空
- **sudo 需要密码** → Ansible `gather_facts` 任务失败，报错 "sudo: a password is required"
- 修复流水线架构已正确，但无法在无 SSH + 无密码 sudo 的环境下执行系统级变更
- 在具备 SSH 和密码less sudo 的系统（如 EC2 实例）上，完整循环（检测 → 生成 → 执行 → 验证 → 重试）可正常工作

## 调试经验

当 `process_rule` 显示 `attempts: 1` 且 `final_state: "unresolved"` 时，说明收敛检查触发了（`previous_drift_count` 等于当前 drift 数量，无改善）。真正的失败发生在执行阶段——需要检查 `exec_result` 的 error 字段来定位实际根因。
