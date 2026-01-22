"""
进度跟踪工具模块
支持断点续传，用于长时间运行的任务
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
from src.utils.logger import get_logger


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, task_name: str, progress_dir: Optional[Path] = None):
        """
        初始化进度跟踪器

        Args:
            task_name: 任务名称
            progress_dir: 进度文件保存目录
        """
        self.task_name = task_name
        self.logger = get_logger()

        # 设置进度文件目录
        if progress_dir is None:
            project_root = Path(__file__).parent.parent.parent
            progress_dir = project_root / "data" / "processed"
        self.progress_dir = Path(progress_dir)
        self.progress_dir.mkdir(parents=True, exist_ok=True)

        # 进度文件路径
        self.progress_file = self.progress_dir / f"{task_name}_progress.json"

        # 进度数据
        self.progress_data: Dict[str, Any] = {
            'task_name': task_name,
            'started_at': None,
            'updated_at': None,
            'completed_at': None,
            'total': 0,
            'completed': 0,
            'failed': 0,
            'skipped': 0,
            'status': 'pending',  # pending, running, completed, failed
            'items': {},  # 存储每个项目的状态
            'metadata': {}  # 额外的元数据
        }

        # 尝试加载已有进度
        self._load_progress()

    def _load_progress(self) -> None:
        """从文件加载进度"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    self.progress_data.update(loaded_data)
                    self.logger.info(f"已加载任务 '{self.task_name}' 的进度: "
                                   f"{self.progress_data['completed']}/{self.progress_data['total']}")
            except Exception as e:
                self.logger.warning(f"加载进度文件失败: {e}，将创建新的进度文件")

    def _save_progress(self) -> None:
        """保存进度到文件"""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存进度文件失败: {e}")

    def start(self, total: int, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        开始任务

        Args:
            total: 总项目数
            metadata: 额外的元数据
        """
        if self.progress_data['status'] == 'running':
            self.logger.info(f"任务 '{self.task_name}' 正在运行，继续执行")
            return

        self.progress_data['started_at'] = datetime.now().isoformat()
        self.progress_data['updated_at'] = datetime.now().isoformat()
        self.progress_data['total'] = total
        self.progress_data['status'] = 'running'

        if metadata:
            self.progress_data['metadata'].update(metadata)

        self._save_progress()
        self.logger.info(f"任务 '{self.task_name}' 已开始，共 {total} 个项目")

    def update(self, item_id: str, status: str, result: Optional[Any] = None) -> None:
        """
        更新单个项目的进度

        Args:
            item_id: 项目ID
            status: 状态 (completed, failed, skipped)
            result: 处理结果
        """
        self.progress_data['items'][item_id] = {
            'status': status,
            'result': result,
            'updated_at': datetime.now().isoformat()
        }

        # 更新计数
        if status == 'completed':
            self.progress_data['completed'] += 1
        elif status == 'failed':
            self.progress_data['failed'] += 1
        elif status == 'skipped':
            self.progress_data['skipped'] += 1

        self.progress_data['updated_at'] = datetime.now().isoformat()
        self._save_progress()

    def is_completed(self, item_id: str) -> bool:
        """
        检查项目是否已完成

        Args:
            item_id: 项目ID

        Returns:
            是否已完成
        """
        return item_id in self.progress_data['items'] and \
               self.progress_data['items'][item_id]['status'] == 'completed'

    def get_item_result(self, item_id: str) -> Optional[Any]:
        """
        获取项目的处理结果

        Args:
            item_id: 项目ID

        Returns:
            处理结果
        """
        if item_id in self.progress_data['items']:
            return self.progress_data['items'][item_id].get('result')
        return None

    def get_pending_items(self, all_items: List[str]) -> List[str]:
        """
        获取待处理的项目列表

        Args:
            all_items: 所有项目ID列表

        Returns:
            待处理的项目ID列表
        """
        return [item_id for item_id in all_items if not self.is_completed(item_id)]

    def complete(self, success: bool = True) -> None:
        """
        完成任务

        Args:
            success: 任务是否成功完成
        """
        self.progress_data['completed_at'] = datetime.now().isoformat()
        self.progress_data['updated_at'] = datetime.now().isoformat()
        self.progress_data['status'] = 'completed' if success else 'failed'

        self._save_progress()

        if success:
            self.logger.info(
                f"任务 '{self.task_name}' 已完成。"
                f"成功: {self.progress_data['completed']}, "
                f"失败: {self.progress_data['failed']}, "
                f"跳过: {self.progress_data['skipped']}"
            )
        else:
            self.logger.error(f"任务 '{self.task_name}' 失败")

    def reset(self) -> None:
        """重置进度"""
        if self.progress_file.exists():
            self.progress_file.unlink()
            self.logger.info(f"已重置任务 '{self.task_name}' 的进度")

        self.progress_data = {
            'task_name': self.task_name,
            'started_at': None,
            'updated_at': None,
            'completed_at': None,
            'total': 0,
            'completed': 0,
            'failed': 0,
            'skipped': 0,
            'status': 'pending',
            'items': {},
            'metadata': {}
        }

    def get_progress_percentage(self) -> float:
        """
        获取进度百分比

        Returns:
            进度百分比 (0-100)
        """
        if self.progress_data['total'] == 0:
            return 0.0

        processed = self.progress_data['completed'] + \
                   self.progress_data['failed'] + \
                   self.progress_data['skipped']

        return (processed / self.progress_data['total']) * 100

    def get_summary(self) -> Dict[str, Any]:
        """
        获取进度摘要

        Returns:
            进度摘要字典
        """
        return {
            'task_name': self.progress_data['task_name'],
            'status': self.progress_data['status'],
            'total': self.progress_data['total'],
            'completed': self.progress_data['completed'],
            'failed': self.progress_data['failed'],
            'skipped': self.progress_data['skipped'],
            'percentage': self.get_progress_percentage(),
            'started_at': self.progress_data['started_at'],
            'updated_at': self.progress_data['updated_at'],
            'completed_at': self.progress_data['completed_at']
        }

    def print_progress(self) -> None:
        """打印进度信息"""
        summary = self.get_summary()
        processed = summary['completed'] + summary['failed'] + summary['skipped']

        print(f"\n{'='*60}")
        print(f"任务: {summary['task_name']}")
        print(f"状态: {summary['status']}")
        print(f"进度: {processed}/{summary['total']} ({summary['percentage']:.1f}%)")
        print(f"  - 成功: {summary['completed']}")
        print(f"  - 失败: {summary['failed']}")
        print(f"  - 跳过: {summary['skipped']}")
        if summary['started_at']:
            print(f"开始时间: {summary['started_at']}")
        if summary['updated_at']:
            print(f"更新时间: {summary['updated_at']}")
        if summary['completed_at']:
            print(f"完成时间: {summary['completed_at']}")
        print(f"{'='*60}\n")

    @property
    def is_running(self) -> bool:
        """任务是否正在运行"""
        return self.progress_data['status'] == 'running'

    @property
    def is_finished(self) -> bool:
        """任务是否已完成"""
        return self.progress_data['status'] in ['completed', 'failed']

    @property
    def total(self) -> int:
        """总项目数"""
        return self.progress_data['total']

    @property
    def completed_count(self) -> int:
        """已完成项目数"""
        return self.progress_data['completed']

    @property
    def failed_count(self) -> int:
        """失败项目数"""
        return self.progress_data['failed']

    @property
    def skipped_count(self) -> int:
        """跳过项目数"""
        return self.progress_data['skipped']
