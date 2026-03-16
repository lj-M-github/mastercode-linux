<<<<<<< HEAD
"""SSH Client module - SSH connection and command execution."""

import subprocess
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SSHConfig:
    """SSH 配置数据类。

    Attributes:
        host: 主机名或 IP
        port: 端口
        username: 用户名
        password: 密码
        key_file: 私钥文件
        timeout: 超时时间
    """
    host: str
    port: int = 22
    username: str = ""
    password: str = ""
    key_file: str = ""
    timeout: int = 30


@dataclass
class SSHResult:
    """SSH 执行结果数据类。

    Attributes:
        success: 是否成功
        stdout: 标准输出
        stderr: 标准错误
        return_code: 返回码
    """
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0


class SSHClient:
    """SSH 客户端。

    负责 SSH 连接和命令执行。

    Note:
        在 Windows 上，需要使用 paramiko 或 plink。
        在 Linux/macOS 上，可以使用 ssh 命令。

    Examples:
        >>> client = SSHClient(SSHConfig("192.168.1.1", username="root"))
        >>> result = client.execute("uname -a")
    """

    def __init__(self, config: SSHConfig):
        """初始化 SSH 客户端。

        Args:
            config: SSH 配置
        """
        self.config = config
        self._connected = False

    def connect(self) -> bool:
        """建立 SSH 连接。

        Returns:
            是否成功
        """
        try:
            # 使用 ssh 命令测试连接
            cmd = ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={self.config.timeout}"]

            if self.config.key_file:
                cmd.extend(["-i", self.config.key_file])

            cmd.extend([
                "-p", str(self.config.port),
                f"{self.config.username}@{self.config.host}",
                "echo 'Connection successful'"
            ])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout
            )

            self._connected = result.returncode == 0
            return self._connected

        except Exception as e:
            print(f"SSH connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """断开 SSH 连接。"""
        self._connected = False

    def execute(self, command: str, timeout: Optional[int] = None) -> SSHResult:
        """执行命令。

        Args:
            command: 命令
            timeout: 超时时间

        Returns:
            SSHResult 对象
        """
        if not self._connected:
            if not self.connect():
                return SSHResult(
                    success=False,
                    stderr="Not connected"
                )

        timeout = timeout or self.config.timeout

        try:
            cmd = ["ssh"]

            if self.config.key_file:
                cmd.extend(["-i", self.config.key_file])

            cmd.extend([
                "-p", str(self.config.port),
                f"{self.config.username}@{self.config.host}",
                command
            ])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return SSHResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )

        except subprocess.TimeoutExpired:
            return SSHResult(
                success=False,
                stderr=f"Command timed out after {timeout}s"
            )
        except Exception as e:
            return SSHResult(
                success=False,
                stderr=str(e)
            )

    def upload(self, local_path: str, remote_path: str) -> bool:
        """上传文件。

        Args:
            local_path: 本地路径
            remote_path: 远程路径

        Returns:
            是否成功
        """
        try:
            cmd = ["scp"]

            if self.config.key_file:
                cmd.extend(["-i", self.config.key_file])

            cmd.extend([
                "-P", str(self.config.port),
                local_path,
                f"{self.config.username}@{self.config.host}:{remote_path}"
            ])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            return result.returncode == 0

        except Exception as e:
            print(f"Upload failed: {e}")
            return False

    def download(self, remote_path: str, local_path: str) -> bool:
        """下载文件。

        Args:
            remote_path: 远程路径
            local_path: 本地路径

        Returns:
            是否成功
        """
        try:
            cmd = ["scp"]

            if self.config.key_file:
                cmd.extend(["-i", self.config.key_file])

            cmd.extend([
                "-P", str(self.config.port),
                f"{self.config.username}@{self.config.host}:{remote_path}",
                local_path
            ])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            return result.returncode == 0

        except Exception as e:
            print(f"Download failed: {e}")
            return False

    @property
    def is_connected(self) -> bool:
        """检查是否已连接。"""
        return self._connected

    def test_connection(self) -> Dict[str, Any]:
        """测试连接。

        Returns:
            测试结果
        """
        result = self.execute("uname -a")

        return {
            "connected": result.success,
            "host": self.config.host,
            "port": self.config.port,
            "system_info": result.stdout.strip() if result.success else None
        }
=======
"""SSH Client module - SSH connection and command execution."""

import subprocess
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SSHConfig:
    """SSH 配置数据类。

    Attributes:
        host: 主机名或 IP
        port: 端口
        username: 用户名
        password: 密码
        key_file: 私钥文件
        timeout: 超时时间
    """
    host: str
    port: int = 22
    username: str = ""
    password: str = ""
    key_file: str = ""
    timeout: int = 30


@dataclass
class SSHResult:
    """SSH 执行结果数据类。

    Attributes:
        success: 是否成功
        stdout: 标准输出
        stderr: 标准错误
        return_code: 返回码
    """
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0


class SSHClient:
    """SSH 客户端。

    负责 SSH 连接和命令执行。

    Note:
        在 Windows 上，需要使用 paramiko 或 plink。
        在 Linux/macOS 上，可以使用 ssh 命令。

    Examples:
        >>> client = SSHClient(SSHConfig("192.168.1.1", username="root"))
        >>> result = client.execute("uname -a")
    """

    def __init__(self, config: SSHConfig):
        """初始化 SSH 客户端。

        Args:
            config: SSH 配置
        """
        self.config = config
        self._connected = False

    def connect(self) -> bool:
        """建立 SSH 连接。

        Returns:
            是否成功
        """
        try:
            # 使用 ssh 命令测试连接
            cmd = ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={self.config.timeout}"]

            if self.config.key_file:
                cmd.extend(["-i", self.config.key_file])

            cmd.extend([
                "-p", str(self.config.port),
                f"{self.config.username}@{self.config.host}",
                "echo 'Connection successful'"
            ])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout
            )

            self._connected = result.returncode == 0
            return self._connected

        except Exception as e:
            print(f"SSH connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """断开 SSH 连接。"""
        self._connected = False

    def execute(self, command: str, timeout: Optional[int] = None) -> SSHResult:
        """执行命令。

        Args:
            command: 命令
            timeout: 超时时间

        Returns:
            SSHResult 对象
        """
        if not self._connected:
            if not self.connect():
                return SSHResult(
                    success=False,
                    stderr="Not connected"
                )

        timeout = timeout or self.config.timeout

        try:
            cmd = ["ssh"]

            if self.config.key_file:
                cmd.extend(["-i", self.config.key_file])

            cmd.extend([
                "-p", str(self.config.port),
                f"{self.config.username}@{self.config.host}",
                command
            ])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return SSHResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )

        except subprocess.TimeoutExpired:
            return SSHResult(
                success=False,
                stderr=f"Command timed out after {timeout}s"
            )
        except Exception as e:
            return SSHResult(
                success=False,
                stderr=str(e)
            )

    def upload(self, local_path: str, remote_path: str) -> bool:
        """上传文件。

        Args:
            local_path: 本地路径
            remote_path: 远程路径

        Returns:
            是否成功
        """
        try:
            cmd = ["scp"]

            if self.config.key_file:
                cmd.extend(["-i", self.config.key_file])

            cmd.extend([
                "-P", str(self.config.port),
                local_path,
                f"{self.config.username}@{self.config.host}:{remote_path}"
            ])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            return result.returncode == 0

        except Exception as e:
            print(f"Upload failed: {e}")
            return False

    def download(self, remote_path: str, local_path: str) -> bool:
        """下载文件。

        Args:
            remote_path: 远程路径
            local_path: 本地路径

        Returns:
            是否成功
        """
        try:
            cmd = ["scp"]

            if self.config.key_file:
                cmd.extend(["-i", self.config.key_file])

            cmd.extend([
                "-P", str(self.config.port),
                f"{self.config.username}@{self.config.host}:{remote_path}",
                local_path
            ])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            return result.returncode == 0

        except Exception as e:
            print(f"Download failed: {e}")
            return False

    @property
    def is_connected(self) -> bool:
        """检查是否已连接。"""
        return self._connected

    def test_connection(self) -> Dict[str, Any]:
        """测试连接。

        Returns:
            测试结果
        """
        result = self.execute("uname -a")

        return {
            "connected": result.success,
            "host": self.config.host,
            "port": self.config.port,
            "system_info": result.stdout.strip() if result.success else None
        }
>>>>>>> af8c867f338f63811bf4407b052c5188fe3ab43c
