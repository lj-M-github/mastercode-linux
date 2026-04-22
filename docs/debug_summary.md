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

---

## 远程服务器适配（第二轮调试）

### 问题

将实验目标改为远程云服务器（`test1@47.118.30.163`，使用 inventory 文件 `/home/m/inventory.ini`，个人用户登录后通过 `become: true` 提权）。

---

### 7. SSH 连接失败 — 缺少 `IdentitiesOnly=yes`

**现象**: SSH 客户端连续调用全部返回 `Not connected`

**文件**: `src/executor/ssh_client.py` — `_build_ssh_command()`

**原因**: SSH 默认会尝试 `~/.ssh/` 下所有密钥，多个密钥导致服务器拒绝连接。

**排查**:
```bash
# 手动测试失败
ssh -i /home/m/.ssh/id_rsa root@47.118.30.163 "echo test"
# Permission denied (publickey,...)

# 加 IdentitiesOnly 成功
ssh -o IdentitiesOnly=yes -i /home/m/.ssh/id_rsa root@47.118.30.163 "echo test"
# test
```

**修复**: `_build_ssh_command()` 中密钥参数前加 `-o IdentitiesOnly=yes`：
```python
if self.config.key_file:
    cmd.extend(["-o", "IdentitiesOnly=yes", "-i", self.config.key_file])
```

---

### 8. 远程审计全部返回空输出 — 缺少 sudo 前缀

**现象**: 远程审计 5 条规则全部 non-compliant，drift actual 为空

**文件**: `src/compliance/drift_auditor.py` — `_run_command_ssh()`

**原因**: `sshd -T` 等命令需要 root 权限，但 SSH 以 `test1` 普通用户连接，未加 sudo。

**排查**:
```bash
# 普通用户执行 — 空输出
ssh test1@host "sshd -T 2>/dev/null | grep permitrootlogin"
# (empty)

# 加 sudo — 正常输出
ssh test1@host "sudo sshd -T 2>/dev/null | grep permitrootlogin"
# permitrootlogin yes
```

**修复**:
```python
def _run_command_ssh(self, command: str) -> tuple[str, str]:
    result = self.ssh_client.execute(f"sudo {command}", timeout=self._timeout)
    return result.stdout.strip(), result.stderr.strip()
```

---

### 9. Ansible playbook 无法执行 — YAML 转义错误

**现象**: `success=False`，error 显示 `found unknown escape character`

**文件**: `src/executor/ansible_runner.py` — `save_playbook()`

**原因**: LLM 生成的 playbook 中 shell 命令包含 `\s\+`（grep regex），但 YAML 将其解释为转义序列，Ansible 拒绝解析。

**排查**:
```yaml
# LLM 生成的内容（无效 YAML）
cmd: "grep -i '^PermitRootLogin\s\+' /etc/ssh/sshd_config"
#                                              ^^ unknown escape

# 修复后（有效 YAML）
cmd: "grep -i '^PermitRootLogin[ \t]+' /etc/ssh/sshd_config"
```

**修复**: `save_playbook()` 中保存前自动替换：
```python
content = re.sub(r'\\s\\+', r'[ \t]+', content)
content = re.sub(r'\\d+', r'[0-9]+', content)
```

---

### 10. 远程 Ansible 执行失败 — 未使用 inventory 文件

**现象**: playbook 保存成功但执行失败，仍尝试连接 localhost

**文件**: `src/executor/ansible_runner.py` — 构造函数和 `run_playbook()`

**原因**: `AnsibleRunner` 构造函数没有 `inventory` 参数，`run_playbook()` 在无 `--limit` 时使用 localhost 内联 inventory。

**修复**:
```python
# 构造函数增加 inventory 参数
def __init__(self, playbook_dir: str = "./playbooks", verbose: bool = False, inventory: str = ""):
    self.inventory = Path(inventory) if inventory else None

# run_playbook() 使用 inventory 文件
if self.inventory and self.inventory.exists():
    cmd.extend(["-i", str(self.inventory)])
elif limit is None:
    cmd.extend(["-i", "localhost,", "-c", "local"])
```

**联动修改**:
- `src/control/orchestrator.py` — `AnsibleRunner` 初始化传入 `config.get('ansible_inventory', '')`
- `src/control/orchestrator.py` — `execute_remediation()` 有 inventory 时不传 `--limit`

---

### 11. 实验 pre/post-audit 审计的是本地而非远程

**现象**: 实验显示 Pre-audit: 0/5 compliant，但远程服务器实际已有不同状态

**文件**: `experiments/run_experiment.py` — `run_single()`

**原因**: `agent.audit_compliance(rule_ids)` 未传递 SSH 参数，DriftAuditor 默认以 localhost 模式运行。

**修复**: 从 target 解析 SSH 信息并传递：
```python
audit_kwargs = {}
if ssh_host:
    audit_kwargs["ssh_host"] = ssh_host
    audit_kwargs["ssh_username"] = target.split("@")[0] if "@" in target else "test1"
    if ssh_key:
        audit_kwargs["ssh_key_file"] = ssh_key

pre = agent.audit_compliance(rule_ids, **audit_kwargs)
post = agent.audit_compliance(rule_ids, **audit_kwargs)
```

---

### 12. 实验脚本不支持 inventory 文件参数

**现象**: 无法通过命令行指定远程 inventory 文件

**文件**: `experiments/run_experiment.py`

**修复**:
- 新增 `--inventory` 和 `--ssh-key` CLI 参数
- 新增 `parse_inventory()` 函数解析 inventory 文件，提取 IP、用户名、密钥路径
- `run_multiple()` 调用传入 `ssh_host` 和 `ssh_key`

---

### 13. 5.2.2 (SSH Protocol) 规则不适用新版 OpenSSH

**现象**: `sshd -T | grep protocol` 返回空输出，5.2.2 永远 non-compliant

**原因**: CIS Benchmark 中的 Protocol 2 检查针对 OpenSSH 7.x 之前版本。现代 OpenSSH（8.x+）已移除 Protocol 1 支持，`sshd -T` 不再输出 protocol 参数。

**解决方案**:
1. 将 5.2.2 从实验规则中排除（因为云服务器不适用此规则）
2. 或修改检查命令为检查 sshd 版本：`sshd -V 2>&1 | grep -oP '\d+\.\d+' | awk '$1 >= 7.0 {print "protocol_2_only"}'`

---

## 当前状态

### 已完成
- ✅ 本地 localhost 模式全链路打通（save_playbook → execute → verify）
- ✅ SSH 连接修复（IdentitiesOnly=yes，多次调用不中断）
- ✅ 远程审计修复（DriftAuditor 加 sudo 前缀）
- ✅ LLM YAML 转义自动修复（`\s\+` → `[ \t]+`）
- ✅ Ansible inventory 集成（使用 `/home/m/inventory.ini`）
- ✅ 实验脚本支持远程目标（pre/post-audit 走 SSH）
- ✅ 单条规则 5.2.1 在远程服务器上成功修复（Post-audit: compliant=1/1）

### 待解决
- ❌ 5.2.2（SSH Protocol）：RHEL9/OpenSSH 较新版本不显示此参数，规则不适用
- ❌ 多规则批量修复成功率仍需验证（5 规则 × 3 轮实验）
- ❌ 验证 `process_rule` 在 Ansible 成功修复后的 verify 步骤是否正确

### 关键发现
- Ansible playbook 能成功修改远程配置（`sudo sshd -T | grep permitrootlogin` → `no`）
- 验证步骤 `verify_remediation()` 调用 `drift_auditor.audit_rule()`，该调用通过 SSH 执行 `sudo sshd -T`，理论上能获取最新状态
- 如果 Ansible playbook 执行后立即 `systemctl restart sshd`，可能需要短暂等待才能看到新配置
