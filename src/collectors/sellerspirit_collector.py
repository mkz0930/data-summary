"""
卖家精灵采集器模块
通过调用Node.js脚本抓取卖家精灵数据，并解析Excel文件
"""

import subprocess
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.database.models import SellerSpiritData
from src.utils.logger import get_logger
from src.utils.retry import retry


class SellerSpiritCollector:
    """卖家精灵采集器"""

    def __init__(self):
        """初始化卖家精灵采集器"""
        self.logger = get_logger()

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
        max_wait: int = 300
    ) -> Optional[SellerSpiritData]:
        """
        采集卖家精灵数据

        Args:
            keyword: 搜索关键词
            wait_time: 等待Excel生成的时间（秒）
            max_wait: 最大等待时间（秒）

        Returns:
            卖家精灵数据对象
        """
        self.logger.info(f"开始采集卖家精灵数据: {keyword}")

        try:
            # 调用Python脚本
            self._run_sellerspirit_script(keyword)

            # 等待Excel文件生成
            excel_file = self._wait_for_excel(keyword, wait_time, max_wait)

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

    def _run_sellerspirit_script(self, keyword: str) -> None:
        """
        运行卖家精灵脚本

        Args:
            keyword: 搜索关键词
        """
        self.logger.info(f"正在调用卖家精灵脚本: {keyword}")

        try:
            # 构建命令
            cmd = ["python", str(self.main_script), "--key", keyword]

            # 执行命令（非阻塞）
            process = subprocess.Popen(
                cmd,
                cwd=str(self.sellerspirit_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.logger.info("卖家精灵脚本已启动，等待数据抓取...")

            # 等待一段时间让脚本执行
            time.sleep(30)

            # 检查进程状态
            if process.poll() is not None:
                # 进程已结束
                stdout, stderr = process.communicate()
                if process.returncode != 0:
                    self.logger.error(f"卖家精灵脚本执行失败: {stderr}")
                else:
                    self.logger.info("卖家精灵脚本执行完成")
            else:
                self.logger.info("卖家精灵脚本仍在运行中...")

        except Exception as e:
            self.logger.error(f"运行卖家精灵脚本失败: {e}")
            raise

    def _wait_for_excel(
        self,
        keyword: str,
        wait_time: int,
        max_wait: int
    ) -> Optional[Path]:
        """
        等待Excel文件生成

        Args:
            keyword: 搜索关键词
            wait_time: 初始等待时间
            max_wait: 最大等待时间

        Returns:
            Excel文件路径
        """
        self.logger.info(f"等待Excel文件生成（最多等待 {max_wait} 秒）...")

        # 等待初始时间
        time.sleep(wait_time)

        # 查找Excel文件
        excel_pattern = f"*{keyword}*.xlsx"
        start_time = time.time()

        while time.time() - start_time < max_wait:
            # 在卖家精灵目录查找Excel文件
            excel_files = list(self.sellerspirit_dir.glob(excel_pattern))

            if excel_files:
                # 找到最新的文件
                latest_file = max(excel_files, key=lambda p: p.stat().st_mtime)
                self.logger.info(f"找到Excel文件: {latest_file}")
                return latest_file

            # 继续等待
            self.logger.debug(f"未找到Excel文件，继续等待...")
            time.sleep(10)

        self.logger.warning(f"等待超时，未找到Excel文件")
        return None

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
            import openpyxl

            # 打开Excel文件
            workbook = openpyxl.load_workbook(excel_file)
            sheet = workbook.active

            # 提取数据（根据实际Excel结构调整）
            # 假设Excel结构：
            # 第1行：标题
            # 第2行开始：数据

            # 初始化数据
            monthly_searches = None
            cr4 = None
            keyword_extensions = []

            # 读取数据
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                if not row or all(cell is None for cell in row):
                    continue

                # 根据实际Excel列结构提取数据
                # 这里需要根据实际的Excel格式调整
                # 示例：假设列结构为 [关键词, 月搜索量, CR4, ...]

                if row_idx == 2:  # 第一行数据
                    # 提取月搜索量
                    if len(row) > 1 and row[1] is not None:
                        monthly_searches = self._parse_number(row[1])

                    # 提取CR4
                    if len(row) > 2 and row[2] is not None:
                        cr4 = self._parse_float(row[2])

                # 收集关键词扩展
                if len(row) > 0 and row[0]:
                    keyword_extensions.append(str(row[0]))

            # 创建SellerSpiritData对象
            data = SellerSpiritData(
                keyword=keyword,
                monthly_searches=monthly_searches,
                cr4=cr4,
                keyword_extensions=json.dumps(keyword_extensions, ensure_ascii=False) if keyword_extensions else None,
                collected_at=datetime.now().isoformat()
            )

            self.logger.info(
                f"Excel解析完成: 月搜索量={monthly_searches}, CR4={cr4}, "
                f"关键词扩展数={len(keyword_extensions)}"
            )

            return data

        except ImportError:
            self.logger.error("缺少openpyxl库，请安装: pip install openpyxl")
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

    def get_latest_excel(self, keyword: str) -> Optional[Path]:
        """
        获取最新的Excel文件

        Args:
            keyword: 搜索关键词

        Returns:
            Excel文件路径
        """
        excel_pattern = f"*{keyword}*.xlsx"
        excel_files = list(self.sellerspirit_dir.glob(excel_pattern))

        if excel_files:
            latest_file = max(excel_files, key=lambda p: p.stat().st_mtime)
            return latest_file

        return None
