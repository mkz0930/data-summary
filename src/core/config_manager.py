"""
配置管理模块
负责加载和管理系统配置，包括config.json和.env文件
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None, env_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: config.json文件路径，默认为项目根目录/config/config.json
            env_path: .env文件路径，默认为项目根目录/config/.env
        """
        self.project_root = Path(__file__).parent.parent.parent

        # 设置配置文件路径
        if config_path is None:
            config_path = self.project_root / "config" / "config.json"
        self.config_path = Path(config_path)

        # 设置环境变量文件路径
        if env_path is None:
            env_path = self.project_root / "config" / ".env"
        self.env_path = Path(env_path)

        # 加载配置
        self.config: Dict[str, Any] = {}
        self.env_vars: Dict[str, str] = {}

        self._load_config()
        self._load_env()

    def _load_config(self) -> None:
        """加载config.json配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")

    def _load_env(self) -> None:
        """加载.env环境变量"""
        if self.env_path.exists():
            load_dotenv(self.env_path)

        # 读取关键的环境变量
        self.env_vars = {
            'SCRAPERAPI_KEY': os.getenv('SCRAPERAPI_KEY', ''),
            'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY', ''),
            'APIFY_API_TOKEN': os.getenv('APIFY_API_TOKEN', ''),
            'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY', ''),
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键，支持点号分隔的嵌套键，如 'api.timeout'
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_env(self, key: str, default: str = '') -> str:
        """
        获取环境变量

        Args:
            key: 环境变量名
            default: 默认值

        Returns:
            环境变量值
        """
        return self.env_vars.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self.config.copy()

    def update(self, key: str, value: Any) -> None:
        """
        更新配置值（仅在内存中，不写入文件）

        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self) -> None:
        """保存配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def validate(self) -> bool:
        """
        验证配置完整性

        Returns:
            配置是否有效
        """
        required_config_keys = [
            'keyword',
            'max_asin',
            'new_product_days',
            'sales_threshold',
        ]

        required_env_keys = [
            'SCRAPERAPI_KEY',
            'ANTHROPIC_API_KEY',
        ]

        # 检查必需的配置项
        for key in required_config_keys:
            if not self.get(key):
                print(f"缺少必需的配置项: {key}")
                return False

        # 检查必需的环境变量
        for key in required_env_keys:
            if not self.get_env(key):
                print(f"缺少必需的环境变量: {key}")
                return False

        return True

    @property
    def keyword(self) -> str:
        """获取搜索关键词"""
        return self.get('keyword', '')

    @property
    def max_asin(self) -> int:
        """获取最大ASIN数量"""
        return self.get('max_asin', 100)

    @property
    def new_product_days(self) -> int:
        """获取新品天数阈值"""
        return self.get('new_product_days', 180)

    @property
    def new_product_min_reviews(self) -> int:
        """获取新品最小评论数"""
        return self.get('new_product_min_reviews', 50)

    @property
    def new_product_max_bsr(self) -> int:
        """获取新品最大BSR排名"""
        return self.get('new_product_max_bsr', 10000)

    @property
    def api_retry(self) -> int:
        """获取API重试次数"""
        return self.get('api_retry', 3)

    @property
    def api_timeout(self) -> int:
        """获取API超时时间（秒）"""
        return self.get('api_timeout', 30)

    @property
    def sales_threshold(self) -> int:
        """获取销量阈值"""
        return self.get('sales_threshold', 10)

    @property
    def price_ranges(self) -> list:
        """获取价格区间"""
        return self.get('price_ranges', [0, 20, 50, 100, 999999])

    @property
    def main_price_band_threshold(self) -> float:
        """获取主流价格带阈值"""
        return self.get('main_price_band_threshold', 0.3)

    @property
    def scraperapi_key(self) -> str:
        """获取ScraperAPI密钥"""
        return self.get_env('SCRAPERAPI_KEY')

    @property
    def anthropic_api_key(self) -> str:
        """获取Anthropic API密钥"""
        return self.get_env('ANTHROPIC_API_KEY')

    @property
    def apify_api_token(self) -> str:
        """获取Apify API令牌"""
        return self.get_env('APIFY_API_TOKEN')

    @property
    def google_api_key(self) -> str:
        """获取Google API密钥"""
        return self.get_env('GOOGLE_API_KEY')

    @property
    def database_path(self) -> Path:
        """获取数据库路径"""
        return self.project_root / "data" / "database" / "analysis.db"

    @property
    def raw_data_dir(self) -> Path:
        """获取原始数据目录"""
        return self.project_root / "data" / "raw"

    @property
    def processed_data_dir(self) -> Path:
        """获取处理后数据目录"""
        return self.project_root / "data" / "processed"

    @property
    def reports_dir(self) -> Path:
        """获取报告输出目录"""
        return self.project_root / "outputs" / "reports"

    @property
    def exports_dir(self) -> Path:
        """获取导出文件目录"""
        return self.project_root / "outputs" / "exports"

    @property
    def logs_dir(self) -> Path:
        """获取日志目录"""
        return self.project_root / "logs"


# 全局配置实例
_config_instance: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """
    获取全局配置实例（单例模式）

    Returns:
        ConfigManager实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance


def init_config(config_path: Optional[str] = None, env_path: Optional[str] = None) -> ConfigManager:
    """
    初始化全局配置实例

    Args:
        config_path: config.json文件路径
        env_path: .env文件路径

    Returns:
        ConfigManager实例
    """
    global _config_instance
    _config_instance = ConfigManager(config_path, env_path)
    return _config_instance
