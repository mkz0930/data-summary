import os
import subprocess
import sys
import time
import urllib.parse
from argparse import ArgumentParser
from urllib.request import urlopen
from urllib.error import URLError
import psutil
import shutil


def parse_args() -> str:
    """
    解析命令行参数，支持：
      - python main.py --key xxx
      - python main.py  直接回车交互输入
    未提供或为空时，默认使用 camping。
    """
    parser = ArgumentParser(description="SellerSpirit 抓取脚本包装器")
    parser.add_argument(
        "--key",
        "-k",
        dest="key",
        help="要抓取的关键词，例如: camping",
    )

    args, extra = parser.parse_known_args()

    # 1) 优先使用 --key / -k
    if args.key:
        return args.key.strip()

    # 2) 兼容老用法：python main.py keyword1 keyword2
    if extra:
        return " ".join(extra).strip()

    # 3) 都没提供，则走交互输入
    keyword = input("请输入要抓取的关键词（直接回车则默认使用 camping）：").strip()
    return keyword or "camping"


class SellerSpiritRunner:
    """
    可复用的运行入口，方便在其它脚本 / 服务中调用。

    示例：
        from main import SellerSpiritRunner
        runner = SellerSpiritRunner()
        runner.run("camping")
    """

    def __init__(self, node_script: str = "demo.js") -> None:
        self.node_script = node_script
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

    def build_search_url(self, keyword: str) -> str:
        encoded_kw = urllib.parse.quote_plus(keyword)
        return f"https://www.amazon.com/s?k={encoded_kw}"

    def open_browser(self, url: str, port: int = 9222) -> None:
        """通过 Chrome DevTools Protocol 在调试端口的 Chrome 中打开新标签页。"""
        try:
            import json
            from urllib.request import Request, urlopen

            # 获取第一个标签页
            tabs_url = f"http://127.0.0.1:{port}/json"
            response = urlopen(tabs_url, timeout=5)
            tabs = json.loads(response.read().decode('utf-8'))

            if tabs:
                # 使用第一个标签页的 webSocketDebuggerUrl
                tab_id = tabs[0]['id']

                # 通过 CDP 导航到新 URL
                navigate_url = f"http://127.0.0.1:{port}/json/activate/{tab_id}"
                urlopen(navigate_url, timeout=5)

                # 发送导航命令
                import websocket
                ws_url = tabs[0]['webSocketDebuggerUrl']
                ws = websocket.create_connection(ws_url, timeout=5)

                # 发送 Page.navigate 命令
                command = {
                    "id": 1,
                    "method": "Page.navigate",
                    "params": {"url": url}
                }
                ws.send(json.dumps(command))
                ws.recv()  # 接收响应
                ws.close()

                print(f"[√] 已在调试端口 Chrome 中打开: {url}")
            else:
                print(f"[!] 未找到可用的 Chrome 标签页")

        except ImportError:
            print("[!] 需要安装 websocket-client: pip install websocket-client")
            print(f"[!] 请手动在浏览器中打开: {url}")
        except Exception as e:
            print(f"[!] 通过 CDP 打开页面失败: {e}")
            print(f"[!] 请手动在浏览器中打开: {url}")

    def find_chrome_executable(self) -> str:
        """
        查找 Chrome 可执行文件的路径。
        支持常见平台的位置。
        """
        possible_paths = []

        if sys.platform == "win32":
            # Windows 常见位置
            possible_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ]
        elif sys.platform == "darwin":
            # macOS
            possible_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ]
        else:
            # Linux
            possible_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/chrome",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
            ]

        # 检查每个路径
        for path in possible_paths:
            if os.path.exists(path):
                return path

        # 尝试使用 which/where 命令查找
        try:
            if sys.platform == "win32":
                chrome_path = shutil.which("chrome")
            else:
                chrome_path = shutil.which("google-chrome") or shutil.which("chromium")
            if chrome_path:
                return chrome_path
        except Exception:
            pass

        return None

    def find_chrome_process(self) -> psutil.Process:
        """
        查找正在运行的 Chrome 进程。
        返回进程对象或 None。
        """
        for proc in psutil.process_iter(['name', 'exe', 'cmdline']):
            try:
                proc_name = proc.info.get('name', '').lower()
                proc_exe = proc.info.get('exe', '').lower()

                # 检查进程名或可执行文件路径
                if 'chrome' in proc_name or 'chrome' in proc_exe:
                    # 排除 chromium-browser 等其他变体（如果需要）
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return None

    def launch_chrome_with_debug_port(self, url: str, port: int = 9222) -> bool:
        """
        启动 Chrome 并开启远程调试端口。
        返回 True 表示成功，False 表示失败。
        """
        chrome_exe = self.find_chrome_executable()
        if not chrome_exe:
            print(f"[!] 未找到 Chrome 浏览器，请手动安装 Chrome")
            return False

        # 创建用户数据目录
        user_data_dir = os.path.join(os.path.expanduser("~"), "chrome-debug-sellerspirit")

        # 构建启动命令
        chrome_cmd = [
            chrome_exe,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            url,
        ]

        print(f"正在启动 Chrome（调试端口 {port}）...")

        try:
            # Windows 下使用 start 命令避免权限问题
            if sys.platform == "win32":
                # 使用 cmd /c start 启动 Chrome，避免权限冲突
                cmd_str = 'start "" ' + ' '.join([
                    f'"{chrome_exe}"',
                    f"--remote-debugging-port={port}",
                    f"--user-data-dir={user_data_dir}",
                    "--remote-allow-origins=*",
                    "--no-first-run",
                    "--no-default-browser-check",
                    f'"{url}"',
                ])
                os.system(cmd_str)
            else:
                subprocess.Popen(chrome_cmd, shell=False)

            # 等待 Chrome 启动并监听端口
            max_wait = 15  # 最多等待15秒
            for i in range(max_wait):
                time.sleep(1)
                if self.check_chrome_debug_port(port):
                    print(f"[√] Chrome 启动成功，调试端口 {port} 可用")
                    return True
                if i % 3 == 0:  # 每3秒打印一次
                    print(f"  等待 Chrome 启动... ({i+1}/{max_wait})")

            print(f"[!] Chrome 启动超时，请检查是否成功")
            return False

        except Exception as e:
            print(f"[!] 启动 Chrome 失败：{e}")
            return False

    def check_chrome_debug_port(self, port: int = 9222) -> bool:
        """
        检查 Chrome 调试端口是否可用。
        返回 True 表示可用，False 表示不可用。
        """
        try:
            response = urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2)
            response.read()
            return True
        except (URLError, OSError, Exception):
            return False

    def run(self, keyword: str) -> None:
        """
        核心执行逻辑：
          1. 检查/启动 Chrome（带调试端口）
          2. 打开 Amazon 搜索页面
          3. 设置环境变量 SS_KEYWORD
          4. 调用 Node 脚本进行抓取
        """
        keyword = (keyword or "camping").strip() or "camping"

        print(f"即将抓取关键词: {keyword!r}")

        # 1) 构造搜索 URL
        url = self.build_search_url(keyword)

        # 2) 检查 Chrome 调试端口是否可用
        print("正在检查 Chrome 调试端口 (9222) 是否可用...")
        chrome_ready = self.check_chrome_debug_port(9222)

        if not chrome_ready:
            print("[!] 未检测到 Chrome 调试端口，尝试自动启动 Chrome...\n")

            # 尝试自动启动 Chrome
            if not self.launch_chrome_with_debug_port(url, 9222):
                print(
                    "\n[!] 自动启动 Chrome 失败\n"
                    "请手动使用以下命令启动 Chrome：\n"
                    '  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" '
                    '--remote-debugging-port=9222 --user-data-dir="C:\\chrome-debug-sellerspirit" '
                    f'"{url}"\n'
                    "并在该 Chrome 窗口中登陆 Amazon、加载卖家精灵扩展。\n"
                    "完成后请重新运行此脚本。\n"
                )
                return
        else:
            print("[√] Chrome 调试端口连接正常")
            # 如果 Chrome 已运行，尝试打开页面
            print(f"正在打开搜索页面：{url}")
            self.open_browser(url)

        print("\n" + "="*60)
        print("✓ Chrome 已启动，正在打开 Amazon 搜索页面")
        print("="*60)
        print("\n请确保：")
        print("  1. 在该 Chrome 窗口中已登录 Amazon")
        print("  2. 已加载卖家精灵扩展")
        print("\n等待 10 秒，让页面完全加载...")
        print("="*60 + "\n")

        # 给页面足够时间加载
        time.sleep(10)

        # 3) 调用现有的 demo.js 脚本
        env = os.environ.copy()
        env["SS_KEYWORD"] = keyword

        node_cmd = ["node", self.node_script]

        print("\n即将启动 Node 脚本进行自动抓取...\n")
        time.sleep(1)

        try:
            subprocess.run(node_cmd, cwd=self.script_dir, env=env, check=True)
        except subprocess.CalledProcessError as e:
            print(f"运行 {self.node_script} 出错，退出码：{e.returncode}")
        except FileNotFoundError:
            print("未找到 node 命令，请确认已安装 Node.js 且已加入 PATH。")


class CLI:
    """
    命令行入口类，封装参数解析和执行逻辑。

    使用示例：
        # 方式1：使用默认参数
        cli = CLI()
        cli.execute()

        # 方式2：自定义参数
        cli = CLI()
        cli.execute(keyword="camping")

        # 方式3：从命令行运行
        python main.py --key camping
        python main.py
    """

    def __init__(self, runner_class=SellerSpiritRunner):
        """
        初始化 CLI 类。

        Args:
            runner_class: 运行器类，默认为 SellerSpiritRunner，
                         可以注入自定义的运行器用于测试或扩展。
        """
        self.runner_class = runner_class

    def parse_args(self) -> str:
        """
        解析命令行参数，支持：
          - python main.py --key xxx
          - python main.py  直接回车交互输入
        未提供或为空时，默认使用 camping。
        """
        parser = ArgumentParser(description="SellerSpirit 抓取脚本包装器")
        parser.add_argument(
            "--key",
            "-k",
            dest="key",
            help="要抓取的关键词，例如: camping",
        )

        args, extra = parser.parse_known_args()

        # 1) 优先使用 --key / -k
        if args.key:
            return args.key.strip()

        # 2) 兼容老用法：python main.py keyword1 keyword2
        if extra:
            return " ".join(extra).strip()

        # 3) 都没提供，则走交互输入
        keyword = input("请输入要抓取的关键词（直接回车则默认使用 camping）：").strip()
        return keyword or "camping"

    def execute(self, keyword: str | None = None) -> None:
        """
        执行抓取任务。

        Args:
            keyword: 要抓取的关键词，如果为 None 则从命令行参数解析。
        """
        # 如果没有提供关键词，则从命令行参数解析
        if keyword is None:
            keyword = self.parse_args()

        # 创建运行器并执行
        runner = self.runner_class()
        runner.run(keyword)


# 保持向后兼容的函数接口
def run():
    """
    CLI 入口：解析参数后，委托给 SellerSpiritRunner，保持与你现在的用法兼容。
    """
    cli = CLI()
    cli.execute()


if __name__ == "__main__":
    run()

