# 补齐环境依赖 & 重跑集成测试

## 目标
1. 检测当前 conda 环境 `master` 中相对于 `requirements-windows.txt` 缺失的 Python 包，一次性安装补齐。
2. 安装完成后，运行全部测试（单元 + 集成）确认通过。

## 操作步骤

### Step 1 — 检测并安装缺失依赖

1. 激活 conda 环境：
   ```powershell
   conda activate master
   ```
2. 以 `requirements-windows.txt` 为基准，用 pip 安装所有缺失包：
   ```powershell
   py -m pip install -r requirements-windows.txt
   ```
3. 如果某些包安装失败（例如编译依赖），记录失败包名并跳过，继续安装其余包。

### Step 2 — 运行全部测试

```powershell
py -m pytest tests/unit/ tests/integration/ -v --tb=short
```

### Step 3 — 报告结果

- 如果所有测试通过，输出 **"ALL TESTS PASSED"**。
- 如果有测试失败，输出失败的测试名称和简要错误信息。
- 如果有包安装失败导致 `ModuleNotFoundError`，列出缺失模块名称。

## 注意事项
- Python 启动命令用 `py`（Windows py launcher），不要用 `python` 或 `python3`。
- 工作目录：`D:\MasterCode`
- Conda 环境名：`master`
- 不要修改任何源代码或测试代码，只做依赖安装和测试运行。
