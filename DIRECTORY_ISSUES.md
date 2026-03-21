# 项目目录结构问题记录

**记录时间**: 2026-03-21
**记录原因**: 基准测试命中率低，发现目录结构混乱导致知识库内容不完整

---

## 一、发现的问题

### 1. 文档位置错误

| 当前位置 | 正确位置 | 说明 |
|---------|---------|------|
| `doc/*.pdf` | `data/corpus/` | CIS 云厂商 PDF 应放在语料库 |
| `doc/*-controls.yml` | `data/policies/cis/` | CIS 控制规则文件 |
| `doc/*-baseline.yml` | `data/policies/cis/` | CIS 基线配置 |
| `doc/*.profile` | `data/policies/cis/` | OpenSCAP 配置文件 |

**影响**: 知识库导入时读取 `data/` 目录，但实际文档在 `doc/`，导致技术规则未被导入。

### 2. 重复目录

| 用途 | 重复目录 | 建议保留 |
|------|---------|---------|
| 报告输出 | `reports/`, `test_reports/`, `data/test_results/` | `reports/` |
| 审计日志 | `audit_logs/`, `test_audit/` | `audit_logs/` |
| 向量数据库 | `vector_db/`, `data/vectordb`(配置但未使用) | `vector_db/` |

### 3. 空目录/临时文件

| 目录/文件 | 状态 | 建议 |
|----------|------|------|
| `test_db/` | 空目录 | 删除 |
| `ansible_playbooks/` | 空目录 | 删除或补充内容 |
| `data/file-permissions-controls.yml` | 临时创建 | 删除，使用 `data/policies/cis/` 中的文件 |
| `data/firewall-controls.yml` | 临时创建 | 删除 |
| `data/kernel-controls.yml` | 临时创建 | 删除 |

### 4. 项目文档目录

| 目录 | 内容 | 状态 |
|------|------|------|
| `docs/` | api_spec.md, architecture.md | 保留，项目文档 |
| `doc/README.md` | 文档索引 | 移动后需更新路径 |

---

## 二、建议的目录结构

```
mastercode-linux/
├── data/
│   ├── corpus/                    # 原始文档 (PDF, Word)
│   │   ├── CIS_Alibaba_Cloud_*.pdf
│   │   ├── CIS_Google_Cloud_*.pdf
│   │   └── CIS_Tencent_Cloud_*.pdf
│   ├── policies/                  # 安全策略
│   │   ├── cis/
│   │   │   ├── RHEL9-CIS-controls.yml
│   │   │   ├── RHEL9-CIS-baseline.yml
│   │   │   ├── Ubuntu22-CIS-controls.yml
│   │   │   └── ...
│   │   ├── nist/
│   │   └── stig/
│   ├── raw/                       # 其他原始数据
│   └── test_results/              # 测试结果 (可保留或合并到 reports)
├── docs/                          # 项目文档
│   ├── api_spec.md
│   └── architecture.md
├── reports/                       # 报告输出 (统一)
├── audit_logs/                    # 审计日志 (统一)
├── vector_db/                     # 向量数据库
├── src/                           # 源代码
├── tests/                         # 测试
└── configs/                       # 配置文件
```

---

## 三、修复步骤

### 步骤 1: 移动文档

```bash
# PDF 到语料库
mv doc/*.pdf data/corpus/

# CIS 规则到策略目录
mv doc/*-controls.yml data/policies/cis/
mv doc/*-baseline.yml data/policies/cis/
mv doc/*.profile data/policies/cis/
mv doc/*-product-info.yml data/policies/cis/

# 其他文档
mv doc/*.md data/raw/
mv doc/*.adoc data/raw/
```

### 步骤 2: 清理重复目录

```bash
# 合并报告目录
mv test_reports/* reports/ 2>/dev/null
mv data/test_results/* reports/ 2>/dev/null
rmdir test_reports/ data/test_results/

# 合并审计目录
mv test_audit/* audit_logs/ 2>/dev/null
rmdir test_audit/

# 删除空目录
rmdir test_db/ ansible_playbooks/
```

### 步骤 3: 删除临时文件

```bash
rm data/file-permissions-controls.yml
rm data/firewall-controls.yml
rm data/kernel-controls.yml
```

### 步骤 4: 更新代码引用

检查 `src/main_agent.py` 中的 `ingest_knowledge` 默认路径，确保指向 `data/`。

### 步骤 5: 重新导入知识库

```python
from src.main_agent import SecurityHardeningAgent
agent = SecurityHardeningAgent()
agent.ingest_knowledge("./data")
```

---

## 四、根本原因分析

**为什么基准测试命中率低?**

1. 知识库主要包含云厂商 PDF 的概述性内容 (74%)
2. 具体技术规则 (RHEL9/Ubuntu22 YAML) 在 `doc/` 目录
3. 导入知识库时读取的是 `data/` 目录
4. 导致知识库缺少 `iptables`, `sysctl`, `chmod` 等技术关键词

**数据证据:**
- 总文档数: 2472
- 包含技术关键词的文档: 98 (4.0%)
- 云厂商 PDF 概述文档: 2374 (96.0%)

---

## 五、后续验证

修复后重新运行基准测试:

```bash
source venv/bin/activate && unset ALL_PROXY all_proxy && python tests/benchmark.py --live
```

预期效果:
- 知识检索准确率: 70% → 90%+
- 加固覆盖率: 70% → 80%+