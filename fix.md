# 项目修复进度

> 最后更新: 2026-04-22

## 已完成的修复

### 第一轮：本地环境 0% 修复率根因分析
- `src/executor/ansible_runner.py` — 新增 `save_playbook()` 方法
- `src/control/orchestrator.py` — 修复 `execute_remediation` kwargs（playbook_name/limit）
- `src/control/orchestrator.py` — `ExecutionResult` dataclass 转 dict
- `src/executor/ansible_runner.py` — `save_playbook` 返回绝对路径 + `run_playbook` 绝对路径判断
- `src/control/orchestrator.py` — `generate_remediation` 剥离 LLM markdown 围栏
- `src/executor/ansible_runner.py` — localhost 使用 `-i localhost, -c local` 替代 `--limit`
- `src/control/retry_controller.py` — convergence check 加 `current_attempts > 0` 守卫

### 第二轮：远程云服务器适配
- `src/executor/ssh_client.py` — 添加 `IdentitiesOnly=yes` SSH 选项
- `src/compliance/drift_auditor.py` — `_run_command_ssh` 加 `sudo` 前缀
- `src/executor/ansible_runner.py` — `save_playbook` 自动修复 LLM YAML 转义错误（`\s\+` → `[ \t]+`）
- `src/executor/ansible_runner.py` — 构造函数增加 `inventory` 参数
- `src/executor/ansible_runner.py` — `run_playbook` 使用 inventory 文件时跳过 localhost inline
- `src/control/orchestrator.py` — `execute_remediation` 有 inventory 时不传 `--limit`
- `src/control/orchestrator.py` — `AnsibleRunner` 初始化传入 `inventory`
- `experiments/run_experiment.py` — 支持 `--inventory`/`--ssh-key` 参数
- `experiments/run_experiment.py` — `run_single`/`run_multiple` 支持远程 SSH 审计
- `experiments/run_experiment.py` — `parse_inventory()` 解析连接信息

## 待解决问题

1. **5.2.2 (SSH Protocol)** — RHEL9/OpenSSH 较新版本 `sshd -T` 不输出 protocol 参数，导致审计总是返回空输出（non-compliant）
2. **process_rule 验证时序** — Ansible playbook 成功修复后，`verify_remediation` 可能因为 sshd 重启延迟或 SSH 连接复用问题未能检测到最新状态
3. **多规则批量成功率** — 需要验证 5 条规则完整实验的修复率

## 运行命令

```bash
# 远程实验
python3 experiments/run_experiment.py \
    --num-runs 3 --num-rules 5 \
    --inventory /home/m/inventory.ini \
    --output-dir ./thesis_experiments_remote

# Inventory 文件位置
# /home/m/inventory.ini
# [cloud]
# 47.118.30.163 ansible_user=test1 ansible_ssh_private_key_file=~/.ssh/id_rsa \
#   ansible_ssh_common_args='-o IdentitiesOnly=yes' \
#   ansible_become=yes ansible_become_method=sudo
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `src/main_agent.py` | 主 Agent，使用 Orchestrator 模式 |
| `src/control/orchestrator.py` | 三层架构协调器 |
| `src/control/retry_controller.py` | 收敛重试逻辑 |
| `src/executor/ansible_runner.py` | Ansible playbook 执行 |
| `src/executor/ssh_client.py` | SSH 客户端 |
| `src/compliance/drift_auditor.py` | 合规审计引擎 |
| `experiments/run_experiment.py` | 实验运行器 |
| `data/compliance_checks/cis_rhel9_checks.yaml` | CIS RHEL9 合规规则 |
| `/home/m/inventory.ini` | Ansible inventory（远程服务器） |
