"""
Security Hardening Framework - 打包脚本
用于创建 Ubuntu 部署包
"""

import os
import zipfile
import shutil
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent

# 输出目录
DIST_DIR = ROOT_DIR / "dist"

# 需要打包的文件和目录
INCLUDE_PATTERNS = [
    "src/**/*.py",
    "tests/**/*.py",
    "requirements.txt",
    "setup.sh",
    "docker-build.sh",
    "Dockerfile",
    "Dockerfile.gpu",
    ".env.example",
    ".gitignore",
    "README.md",
    "DEPLOY_UBUNTU.md",
    "TEST_REPORT.md",
    "pytest.ini",
]

# 需要排除的目录
EXCLUDE_DIRS = [
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".git",
    ".vscode",
    ".idea",
    "venv",
    "env",
    ".venv",
    "dist",
    "build",
    "vector_db",
    "reports",
    "audit_logs",
    "playbooks",
    "*.egg-info",
]

def should_exclude(path: Path) -> bool:
    """检查路径是否应该被排除。"""
    for part in path.parts:
        if part.startswith('.'):
            return True
        for exclude in EXCLUDE_DIRS:
            if part == exclude or part.endswith(exclude):
                return True
    return False

def collect_files() -> list:
    """收集所有需要打包的文件。"""
    files = []

    for pattern in INCLUDE_PATTERNS:
        if '*' in pattern:
            # Glob 模式
            for path in ROOT_DIR.glob(pattern):
                if not should_exclude(path) and path.is_file():
                    files.append(path)
        else:
            # 单个文件
            path = ROOT_DIR / pattern
            if path.exists() and path.is_file():
                files.append(path)

    return files

def create_zip_package():
    """创建 ZIP 部署包。"""
    print("收集文件...")
    files = collect_files()

    # 确保输出目录存在
    DIST_DIR.mkdir(exist_ok=True)

    # ZIP 文件名
    zip_name = "security-hardening-framework-ubuntu.zip"
    zip_path = DIST_DIR / zip_name

    print(f"创建 ZIP 包：{zip_path}")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            # 计算归档路径
            try:
                arcname = file.relative_to(ROOT_DIR)
            except ValueError:
                arcname = file.name

            # 跳过需要排除的文件
            if should_exclude(file):
                continue

            zipf.write(file, arcname)
            print(f"  添加：{arcname}")

    print(f"\n完成！ZIP 包大小：{zip_path.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"位置：{zip_path}")

    return zip_path

def create_tarball_package():
    """创建 tar.gz 部署包（需要 shell 命令）。"""
    import subprocess

    print("创建 tar.gz 包...")

    # 确保输出目录存在
    DIST_DIR.mkdir(exist_ok=True)

    tar_name = "security-hardening-framework-ubuntu.tar.gz"
    tar_path = DIST_DIR / tar_name

    # 使用 git archive 或 tar 创建
    files = collect_files()

    # 创建文件列表
    file_list = []
    for f in files:
        if not should_exclude(f):
            try:
                rel_path = f.relative_to(ROOT_DIR)
                file_list.append(str(rel_path))
            except ValueError:
                pass

    # 写入文件列表
    list_path = DIST_DIR / "files.txt"
    with open(list_path, 'w') as f:
        f.write('\n'.join(file_list))

    # 使用 tar 命令
    cmd = f"tar -czf {tar_path} -C {ROOT_DIR} -T {list_path}"
    subprocess.run(cmd, shell=True, check=True)

    # 清理临时文件
    list_path.unlink()

    print(f"完成！tar.gz 包大小：{tar_path.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"位置：{tar_path}")

    return tar_path

def main():
    """主函数。"""
    print("=" * 60)
    print("Security Hardening Framework - 打包工具")
    print("=" * 60)
    print()

    # 创建 ZIP 包
    zip_path = create_zip_package()

    # 尝试创建 tar.gz 包（仅在 Unix 系统上）
    if os.name != 'nt':
        create_tarball_package()

    print()
    print("=" * 60)
    print("部署说明:")
    print("=" * 60)
    print(f"""
1. 将 {zip_path} 上传到 Ubuntu 服务器

2. 解压:
   unzip {zip_path.name}
   cd security-hardening-framework

3. 运行部署脚本:
   chmod +x setup.sh
   ./setup.sh

4. 配置环境变量:
   cp .env.example .env
   # 编辑 .env 文件，填写 API 密钥

5. 运行测试:
   source venv/bin/activate
   python -m pytest tests/ -v
""")

if __name__ == "__main__":
    main()
