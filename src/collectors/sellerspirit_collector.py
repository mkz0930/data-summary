"""
卖家精灵采集器模块
通过调用Node.js脚本抓取卖家精灵数据，并解析Excel文件

缓存机制：
- 使用统一缓存管理器 (UnifiedDataCache) 存储数据
- 缓存键: keyword
- 默认TTL: 168小时 (7天)
"""

import subprocess
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

import pandas as pd

from src.database.models import SellerSpiritData
from src.utils.logger import get_logger
from src.utils.retry import retry
from src.collectors.cache_adapter import CacheAdapter, get_cache_adapter


class SellerSpiritCollector:
    """卖家精灵采集器"""

    def __init__(self, db_manager=None, cache_adapter: Optional[CacheAdapter] = None):
        """
        初始化卖家精灵采集器

        Args:
            db_manager: 数据库管理器（可选，用于检查是否已有数据）
            cache_adapter: 缓存适配器（可选，默认使用全局单例）
        """
        self.logger = get_logger()
        self.db_manager = db_manager
        self.cache_adapter = cache_adapter or get_cache_adapter()

        # 卖家精灵脚本路径
        self.sellerspirit_dir = Path(__file__).parent.parent.parent / "external_apis"
        self.main_script = self.sellerspirit_dir / "sellerspirit_main.py"

        # 检查脚本是否存在
        if not self.main_script.exists():
            raise FileNotFoundError(f"卖家精灵脚本不存在: {self.main_script}")

    @retry(max_attempts=2, delay=5.0, backoff=2.0)
    def collect_data(
        self,
        keyword: str,
        wait_time: int = 60,
        max_wait: int = 300,
        force_download: bool = False,
        output_dir: Optional[Path] = None
    ) -> Optional[SellerSpiritData]:
        """
        采集卖家精灵数据

        Args:
            keyword: 搜索关键词
            wait_time: 等待Excel生成的时间（秒）
            max_wait: 最大等待时间（秒）
            force_download: 是否强制重新下载（默认False，会先检查已有数据）
            output_dir: 输出目录（如果指定，Excel文件将保存到此目录）

        Returns:
            卖家精灵数据对象
        """
        self.logger.info(f"开始采集卖家精灵数据: {keyword}")

        try:
            # 1. 如果不是强制下载，先检查是否已有数据
            if not force_download:
                existing_data = self._check_existing_data(keyword, output_dir)
                if existing_data:
                    return existing_data

            # 2. 没有已有数据，开始下载
            self.logger.info(f"未找到已有数据，开始下载: {keyword}")

            # 调用Python脚本
            self._run_sellerspirit_script(keyword, output_dir)

            # 等待Excel文件生成
            excel_file = self._wait_for_excel(keyword, wait_time, max_wait, output_dir)

            if not excel_file:
                self.logger.error("未找到生成的Excel文件")
                return None

            # 解析Excel文件
            data = self._parse_excel(excel_file, keyword)

            self.logger.info(f"卖家精灵数据采集完成: {keyword}")

            return data

        except Exception as e:
            self.logger.error(f"采集卖家精灵数据失败: {e}")
            raise

    def _check_existing_data(self, keyword: str, output_dir: Optional[Path] = None) -> Optional[SellerSpiritData]:
        """
        检查是否已有该关键词的数据（避免重复下载）

        检查顺序：
        1. 检查统一缓存中是否已有数据
        2. 检查数据库中是否已有数据
        3. 检查本地是否已有Excel文件

        Args:
            keyword: 搜索关键词
            output_dir: 输出目录（如果指定，将在此目录查找Excel文件）

        Returns:
            如果找到已有数据，返回SellerSpiritData对象；否则返回None
        """
        self.logger.info(f"检查是否已有数据: {keyword}")

        # 1. 检查统一缓存
        cached_data = self.cache_adapter.get_sellerspirit(keyword)
        if cached_data:
            self.logger.info(f"✓ 统一缓存中已有该关键词的数据，跳过下载")
            self.logger.info(f"  - 月搜索量: {cached_data.get('monthly_searches')}")
            self.logger.info(f"  - CR4: {cached_data.get('cr4')}")
            return SellerSpiritData.from_dict(cached_data)

        # 2. 检查数据库中是否已有数据
        if self.db_manager:
            try:
                existing_data = self.db_manager.get_sellerspirit_data(keyword)
                if existing_data:
                    self.logger.info(f"✓ 数据库中已有该关键词的数据，跳过下载")
                    self.logger.info(f"  - 采集时间: {existing_data.collected_at}")
                    self.logger.info(f"  - 月搜索量: {existing_data.monthly_searches}")
                    self.logger.info(f"  - CR4: {existing_data.cr4}")
                    # 同步到统一缓存
                    self.cache_adapter.cache_sellerspirit(keyword, existing_data.to_dict())
                    return existing_data
            except Exception as e:
                self.logger.warning(f"检查数据库时出错: {e}")

        # 2. 检查本地是否已有Excel文件
        excel_file = self.get_latest_excel(keyword, output_dir)
        if excel_file:
            self.logger.info(f"✓ 本地已有该关键词的Excel文件，跳过下载")
            self.logger.info(f"  - 文件路径: {excel_file}")
            self.logger.info(f"  - 文件时间: {datetime.fromtimestamp(excel_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")

            # 解析Excel文件并返回数据
            try:
                data = self._parse_excel(excel_file, keyword)
                self.logger.info(f"✓ 已从本地Excel文件解析数据")
                return data
            except Exception as e:
                self.logger.warning(f"解析本地Excel文件失败: {e}，将重新下载")
                return None

        # 3. 没有找到已有数据
        self.logger.info(f"未找到已有数据，需要重新下载")
        return None

    def _run_sellerspirit_script(self, keyword: str, output_dir: Optional[Path] = None) -> None:
        """
        运行卖家精灵脚本

        Args:
            keyword: 搜索关键词
            output_dir: 输出目录（如果指定，Excel文件将保存到此目录）
        """
        self.logger.info(f"正在调用卖家精灵脚本: {keyword}")

        try:
            # 构建命令
            cmd = ["python", str(self.main_script), "--key", keyword]

            # 如果指定了输出目录，添加到命令参数
            if output_dir:
                cmd.extend(["--output", str(output_dir)])
                self.logger.info(f"  - 输出目录: {output_dir}")

            # 执行命令（非阻塞），实时捕获输出
            process = subprocess.Popen(
                cmd,
                cwd=str(self.sellerspirit_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
                text=True,
                encoding='utf-8',  # 明确指定UTF-8编码
                errors='replace',  # 遇到无法解码的字符时替换而不是报错
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )

            self.logger.info("卖家精灵脚本已启动，等待数据抓取...")

            # 使用线程实时读取输出
            import threading
            import queue

            output_queue = queue.Queue()

            def read_output():
                """读取子进程输出的线程函数"""
                try:
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            output_queue.put(line.rstrip())
                    process.stdout.close()
                except Exception as e:
                    output_queue.put(f"读取输出时出错: {e}")

            # 启动读取线程
            reader_thread = threading.Thread(target=read_output)
            reader_thread.daemon = True
            reader_thread.start()

            # 等待子进程完全结束，同时实时打印输出
            # 卖家精灵采集需要5-15分钟，所以需要等待足够长的时间
            self.logger.info("等待卖家精灵脚本完成（预计需要5-15分钟）...")

            while True:
                # 检查进程是否结束
                if process.poll() is not None:
                    break

                # 从队列中读取并打印输出
                try:
                    while True:
                        line = output_queue.get_nowait()
                        self.logger.info(f"[脚本输出] {line}")
                except queue.Empty:
                    pass

                time.sleep(0.5)

            # 读取剩余的输出
            try:
                while True:
                    line = output_queue.get_nowait()
                    self.logger.info(f"[脚本输出] {line}")
            except queue.Empty:
                pass

            # 等待读取线程结束
            reader_thread.join(timeout=2)

            # 检查进程状态
            if process.returncode != 0:
                self.logger.error(f"卖家精灵脚本执行失败，退出码: {process.returncode}")
                raise RuntimeError(f"卖家精灵脚本执行失败，退出码: {process.returncode}")
            else:
                self.logger.info("卖家精灵脚本执行完成")

        except Exception as e:
            self.logger.error(f"运行卖家精灵脚本失败: {e}")
            raise

    def _wait_for_excel(
        self,
        keyword: str,
        wait_time: int,
        max_wait: int,
        output_dir: Optional[Path] = None
    ) -> Optional[Path]:
        """
        等待Excel文件生成并确保文件写入完成

        Args:
            keyword: 搜索关键词
            wait_time: 初始等待时间
            max_wait: 最大等待时间
            output_dir: 输出目录（如果指定，将在此目录查找Excel文件）

        Returns:
            Excel文件路径
        """
        self.logger.info(f"等待Excel文件生成（最多等待 {max_wait} 秒）...")

        # 确定下载目录
        if output_dir:
            download_dir = output_dir
        else:
            # 默认路径：outputs/{keyword}/sellerspirit/
            project_root = Path(__file__).parent.parent.parent
            download_dir = project_root / "outputs" / keyword / "sellerspirit"

        # 查找Excel文件
        excel_pattern = "*.xlsx"
        start_time = time.time()

        while time.time() - start_time < max_wait:
            # 检查目录是否存在
            if not download_dir.exists():
                self.logger.debug(f"下载目录尚未创建: {download_dir}")
                time.sleep(10)
                continue

            # 在下载目录查找Excel文件
            excel_files = list(download_dir.glob(excel_pattern))

            if excel_files:
                # 找到最新的文件
                latest_file = max(excel_files, key=lambda p: p.stat().st_mtime)
                self.logger.info(f"找到Excel文件: {latest_file}")

                # 等待文件写入完成：检查文件大小是否稳定
                self.logger.info("等待Excel文件写入完成...")
                if self._wait_for_file_stable(latest_file, timeout=30):
                    self.logger.info("Excel文件写入完成")
                    return latest_file
                else:
                    self.logger.warning("Excel文件可能仍在写入，但已超时，尝试读取")
                    return latest_file

            # 继续等待
            self.logger.debug(f"未找到Excel文件，继续等待...")
            time.sleep(10)

        self.logger.warning(f"等待超时，未找到Excel文件")
        return None

    def _wait_for_file_stable(self, file_path: Path, timeout: int = 30) -> bool:
        """
        等待文件大小稳定（确保文件写入完成）

        Args:
            file_path: 文件路径
            timeout: 超时时间（秒）

        Returns:
            True 表示文件稳定，False 表示超时
        """
        start_time = time.time()
        last_size = -1
        stable_count = 0

        while time.time() - start_time < timeout:
            try:
                current_size = file_path.stat().st_size

                if current_size == last_size:
                    stable_count += 1
                    # 连续3次检查大小不变，认为文件写入完成
                    if stable_count >= 3:
                        return True
                else:
                    stable_count = 0
                    last_size = current_size

                time.sleep(2)  # 每2秒检查一次

            except Exception as e:
                self.logger.warning(f"检查文件大小时出错: {e}")
                time.sleep(2)

        return False

    def _parse_excel(self, excel_file: Path, keyword: str) -> SellerSpiritData:
        """
        解析Excel文件

        Args:
            excel_file: Excel文件路径
            keyword: 搜索关键词

        Returns:
            卖家精灵数据对象
        """
        self.logger.info(f"正在解析Excel文件: {excel_file}")

        try:
            # 使用pandas读取Excel文件（更好的容错处理）
            df = pd.read_excel(excel_file, engine='openpyxl')

            self.logger.info(f"成功读取Excel文件，共 {len(df)} 行，{len(df.columns)} 列")

            # 初始化数据
            monthly_searches = None
            cr4 = None
            keyword_extensions = []

            # 提取月销量总和（所有产品的月销量之和）
            if '月销量' in df.columns:
                # 直接使用pandas处理，去除NaN后求和
                monthly_sales_series = df['月销量'].dropna()
                if len(monthly_sales_series) > 0:
                    total_monthly_sales = monthly_sales_series.sum()
                    monthly_searches = int(total_monthly_sales)
                    self.logger.info(f"提取到月销量总和: {monthly_searches} (有效数据: {len(monthly_sales_series)}/{len(df)})")

            # 计算CR4（前4名的市场份额）
            if '月销量' in df.columns and len(df) >= 4:
                # 前4名的销量
                top4_sales_series = df.head(4)['月销量'].dropna()
                top4_sales = top4_sales_series.sum() if len(top4_sales_series) > 0 else 0

                # 总销量
                all_sales_series = df['月销量'].dropna()
                total_sales = all_sales_series.sum() if len(all_sales_series) > 0 else 0

                if total_sales > 0:
                    cr4 = round((top4_sales / total_sales) * 100, 2)
                    self.logger.info(f"计算得到CR4: {cr4}%")

            # 提取关键词扩展（从商品标题中提取）
            if '商品标题' in df.columns:
                # 取前10个产品的标题作为关键词扩展参考
                titles = df['商品标题'].head(10).dropna().tolist()
                keyword_extensions = [str(title)[:100] for title in titles]  # 限制长度
                self.logger.info(f"提取到 {len(keyword_extensions)} 个关键词扩展")

            # 创建SellerSpiritData对象
            data = SellerSpiritData(
                keyword=keyword,
                monthly_searches=monthly_searches,
                cr4=cr4,
                keyword_extensions=json.dumps(keyword_extensions, ensure_ascii=False) if keyword_extensions else None,
                collected_at=datetime.now().isoformat()
            )

            # 保存到统一缓存
            self.cache_adapter.cache_sellerspirit(keyword, data.to_dict())

            self.logger.info(
                f"Excel解析完成: 月销量={monthly_searches}, CR4={cr4}, "
                f"关键词扩展数={len(keyword_extensions)}"
            )

            return data

        except ImportError as e:
            self.logger.error(f"缺少必要的库: {e}，请安装: pip install pandas openpyxl")
            raise
        except Exception as e:
            self.logger.error(f"解析Excel文件失败: {e}")
            raise

    def _parse_number(self, value: Any) -> Optional[int]:
        """
        解析数字

        Args:
            value: 值

        Returns:
            整数
        """
        # 处理NaN值
        if pd.isna(value):
            return None

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        if isinstance(value, str):
            # 移除逗号和其他非数字字符
            import re
            number_str = re.sub(r'[^\d]', '', value)
            try:
                return int(number_str)
            except ValueError:
                return None

        return None

    def _parse_float(self, value: Any) -> Optional[float]:
        """
        解析浮点数

        Args:
            value: 值

        Returns:
            浮点数
        """
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            # 移除百分号等
            import re
            value_str = value.replace('%', '').strip()
            try:
                return float(value_str)
            except ValueError:
                return None

        return None

    def collect_data_manual(
        self,
        excel_file: Path,
        keyword: str
    ) -> Optional[SellerSpiritData]:
        """
        手动指定Excel文件进行解析（用于已有Excel文件的情况）

        Args:
            excel_file: Excel文件路径
            keyword: 搜索关键词

        Returns:
            卖家精灵数据对象
        """
        self.logger.info(f"手动解析Excel文件: {excel_file}")

        if not excel_file.exists():
            self.logger.error(f"Excel文件不存在: {excel_file}")
            return None

        try:
            return self._parse_excel(excel_file, keyword)
        except Exception as e:
            self.logger.error(f"手动解析Excel失败: {e}")
            return None

    def get_latest_excel(self, keyword: str, output_dir: Optional[Path] = None) -> Optional[Path]:
        """
        获取最新的Excel文件

        Args:
            keyword: 搜索关键词
            output_dir: 输出目录（如果指定，将在此目录查找Excel文件）

        Returns:
            Excel文件路径
        """
        # 确定下载目录
        if output_dir:
            download_dir = output_dir
        else:
            # 默认路径：outputs/{keyword}/sellerspirit/
            project_root = Path(__file__).parent.parent.parent
            download_dir = project_root / "outputs" / keyword / "sellerspirit"

        # 如果目录不存在，返回None
        if not download_dir.exists():
            return None

        # 在该目录下查找Excel文件
        excel_pattern = "*.xlsx"
        excel_files = list(download_dir.glob(excel_pattern))

        if excel_files:
            latest_file = max(excel_files, key=lambda p: p.stat().st_mtime)
            return latest_file

        return None
