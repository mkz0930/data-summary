# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ 必读：开发规范

**在执行任何编码任务前，必须先运行 `/prules` 加载个人编码标准。**

核心要求：
- **TDD**：先写测试，再写代码
- **文档维护**：每次提交必须更新 `docs/CHANGELOG.md`
- **中文注释**：所有注释使用中文
- **4阶段工作流**：方案设计 → 编写测试 → 实现代码 → 验证提交
- **提交公式**：代码 + 测试 + 文档 + CHANGELOG = 完整提交

详细规范见 `.claude/skills/prules/SKILL.md`

---

## Project Overview

亚马逊商品数据分析系统 - 数据驱动的产品选型决策工具，用于发现市场空白机会、竞品分析和产品验证。

**核心流程**: 关键词输入 → API抓取ASIN → 卖家精灵补充数据 → AI分类校验 → 数据分析 → 生成HTML报告

## Commands

```bash
# 安装依赖
pip install -r requirements.txt

# 运行完整分析
python main.py --keyword camping

# 跳过数据采集（使用缓存数据）
python main.py --skip-collection

# 跳过AI验证（节省API调用）
python main.py --skip-validation

# 强制重新分析
python main.py --force-reanalysis

# 验证配置
python main.py --validate-config

# 运行所有测试
python tests/run_tests.py

# 运行单个测试
python -m unittest tests.test_market_analyzer

# 关键词缓存管理
python scripts/manage_keyword_cache.py --list
python scripts/manage_keyword_cache.py --clear camping
```

## Architecture

```
src/
├── core/
│   ├── config_manager.py    # 配置加载（JSON + .env）
│   └── orchestrator.py      # 主流程编排，协调所有模块
├── collectors/              # 数据采集
│   ├── asin_collector.py    # Amazon ASIN抓取（ScraperAPI）
│   ├── price_collector.py   # 价格数据（Apify API）
│   ├── sellerspirit_collector.py  # 卖家精灵市场数据
│   └── keyword_cache_manager.py   # 关键词缓存
├── validators/              # 数据验证
│   ├── category_validator.py   # Claude AI分类验证
│   └── gemini_validator.py     # Gemini AI验证（备选）
├── analyzers/               # 分析模块（10个）
│   ├── market_analyzer.py      # 市场规模、竞争强度、CR4/CR10
│   ├── blue_ocean_analyzer.py  # 蓝海产品识别
│   └── ...                     # 价格、生命周期、关键词、趋势等
├── reporters/               # 报告生成
│   ├── html_generator.py    # 交互式HTML报告
│   └── csv_exporter.py      # CSV数据导出
└── database/
    ├── db_manager.py        # SQLite操作
    └── models.py            # 数据模型
```

**输出目录结构**: `outputs/{keyword}/{timestamp}/` 包含 `exports/`（CSV）和 `reports/`（HTML）

## Configuration

- **主配置**: `config/config.json` - 关键词、阈值、并发数等
- **API密钥**: `config/.env` - SCRAPERAPI_KEY, ANTHROPIC_API_KEY, APIFY_API_TOKEN, GOOGLE_API_KEY
- **数据库**: `data/database/analysis.db` (SQLite)

## Key Metrics

| 指标           | 定义                      | 阈值           |
| -------------- | ------------------------- | -------------- |
| 市场空白指数   | 月搜索量 / 竞品数         | > 100 = 高机会 |
| 市场集中度 CR4 | Top 4 品牌市场份额        | > 60% = 高集中 |
| 新品定义       | 上架 < 6个月，评论 > 50   | 证明有销量     |
| 主力价格带     | 产品占比 > 30% 的价格区间 | 市场主战场     |

## External Dependencies

- **ScraperAPI**: Amazon产品搜索和详情抓取
- **Apify API**: 价格数据采集（25并发）
- **Claude API**: AI分类验证（5并发）
- **Gemini API**: 备选AI验证（1000并发）
- **卖家精灵**: 市场数据（需Chrome扩展）
