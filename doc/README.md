# 安全基准文档资源索引

本文档记录了测试加固框架所需的安全基准文档资源。

## 已下载的资源

### Ubuntu 22.04 LTS 相关

| 文件名 | 大小 | 描述 |
|--------|------|------|
| `Ubuntu22-CIS-baseline.yml` | 54KB | Ansible Lockdown Ubuntu 22 CIS 基准配置 |
| `Ubuntu22-CIS-controls.yml` | 81KB | OpenSCAP/ComplianceAsCode CIS 控制定义 |
| `Ubuntu22-CIS-Level1-Server.profile` | 651B | CIS Level 1 Server 配置文件 |
| `Ubuntu22-CIS-Level2-Server.profile` | 651B | CIS Level 2 Server 配置文件 |
| `Ubuntu22-STIG.profile` | 461B | DISA STIG 配置文件 |
| `Ubuntu22-product-info.yml` | 1.4KB | Ubuntu 22.04 产品信息 |
| `Ubuntu-Hardening-Guide.adoc` | 23KB | Ubuntu 加固指南 |

### RHEL9 / Rocky Linux 9 相关

| 文件名 | 大小 | 描述 |
|--------|------|------|
| `RHEL9-CIS-baseline.yml` | 74KB | Ansible Lockdown RHEL9 CIS 基准配置 |
| `RHEL9-CIS-controls.yml` | 89KB | OpenSCAP/ComplianceAsCode CIS 控制定义 |
| `RHEL9-CIS-Server-L1.profile` | 832B | CIS Server Level 1 配置文件 |
| `RHEL9-STIG.profile` | 988B | DISA STIG 配置文件 |
| `RHEL9-product-info.yml` | 1.7KB | RHEL9 产品信息 |
| `Rocky9-Hardening-Guide.md` | 2.1KB | Rocky 9 加固指南 |

### 通用文档

| 文件名 | 大小 | 描述 |
|--------|------|------|
| `Linux-Security-Baseline.md` | 1.4KB | dev-sec Linux 安全基准 |

## 在线资源链接

### CIS 官方资源
- **CIS Benchmarks**: https://www.cisecurity.org/cis-benchmarks
  - 需要免费注册账户才能下载 PDF
  - Ubuntu 22.04 LTS Benchmark v2.0.0
  - Rocky Linux 9 Benchmark

### GitHub 开源项目
- **ansible-lockdown/UBUNTU22-CIS**: https://github.com/ansible-lockdown/UBUNTU22-CIS
- **ansible-lockdown/RHEL9-CIS**: https://github.com/ansible-lockdown/RHEL9-CIS
- **ComplianceAsCode/content**: https://github.com/ComplianceAsCode/content
- **konstruktoid/hardening**: https://github.com/konstruktoid/hardening

### DISA STIG
- **STIG Downloads**: https://public.cyber.mil/stigs/downloads/
- **Ubuntu 22.04 STIG**: 需要 DISA 网站下载
- **RHEL9 STIG**: 与 Rocky 9 兼容

## 使用建议

1. **结构化数据**: 下载的 `.yml` 和 `.profile` 文件是机器可读格式，适合自动化解析
2. **完整 PDF**: 若需完整 PDF 文档，请访问 CIS 官网注册免费账户
3. **基准映射**: RHEL9 基准可兼容 Rocky Linux 9，因二者高度兼容

## 文件格式说明

- `.yml` - YAML 格式配置文件，适合 Ansible/OpenSCAP
- `.profile` - OpenSCAP 配置文件格式
- `.adoc` - AsciiDoc 格式文档
- `.md` - Markdown 格式文档