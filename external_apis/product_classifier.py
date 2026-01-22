#!/usr/bin/env python3
"""
Product Category Validator
验证Amazon产品分类是否正确，基于产品信息和Claude API分析
"""

import csv
import os
import sys
import json
import time
import logging
from datetime import datetime
from anthropic import Anthropic, APIError, APIConnectionError, APITimeoutError, RateLimitError

# 配置
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
BASE_URL = "https://yunyi.cfd/claude"  # 代理服务器地址
INPUT_FILE = "keyword_camping_complete_20260120_172523.csv"
OUTPUT_FILE = f"validated_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
PROGRESS_FILE = "validation_progress.json"
SAMPLE_MODE = False  # 设置为True只处理前10行进行测试
SAMPLE_SIZE = 10

# API调用配置
MAX_RETRIES = 5  # 最大重试次数
RETRY_DELAY = 2.0  # 初始重试延迟（秒）
BACKOFF_FACTOR = 2.0  # 退避倍数
REQUEST_TIMEOUT = 60.0  # 请求超时时间（秒）
REQUEST_INTERVAL = 1.0  # 请求间隔（秒）
CIRCUIT_BREAKER_THRESHOLD = 10  # 熔断阈值：连续失败次数

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def validate_category(product_data):
    """
    使用Claude API验证产品分类是否正确（带重试机制）

    Args:
        product_data: 包含产品信息的字典

    Returns:
        dict: {"is_correct": bool, "suggested_category": str, "reason": str}
    """
    # 构建提示词
    prompt = f"""你是一个Amazon产品分类专家。请分析以下产品信息，判断其当前分类是否合理。

产品名称: {product_data.get('name', 'N/A')}
当前分类: {product_data.get('category', 'N/A')}
品牌: {product_data.get('brand', 'N/A')}
产品特性: {product_data.get('feature_bullets', 'N/A')[:500]}
产品描述: {product_data.get('full_description', 'N/A')[:500]}

请按照以下格式回答：
1. 当前分类是否正确？（回答：正确 或 不正确）
2. 如果不正确，建议的正确分类是什么？（使用Amazon的分类层级格式，如：Sports & Outdoors›Outdoor Recreation›Camping & Hiking›...）
3. 简要说明理由（不超过50字）

请严格按照以下格式输出（每行一个字段）：
分类状态: [正确/不正确]
建议分类: [如果正确则写"无需修改"，否则写建议的完整分类路径]
理由: [简要说明]"""

    # 带重试的API调用
    last_error = None
    current_delay = RETRY_DELAY

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"验证产品分类: {product_data.get('asin', 'Unknown')} (尝试 {attempt}/{MAX_RETRIES})")

            # 创建客户端（每次重试都创建新客户端）
            client = Anthropic(
                api_key=API_KEY,
                base_url=BASE_URL,
                timeout=REQUEST_TIMEOUT
            )

            # 调用API
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # 解析响应
            lines = response_text.strip().split('\n')
            result = {
                "is_correct": True,
                "suggested_category": "",
                "reason": ""
            }

            for line in lines:
                if line.startswith("分类状态:"):
                    status = line.split(":", 1)[1].strip()
                    result["is_correct"] = "正确" in status
                elif line.startswith("建议分类:"):
                    result["suggested_category"] = line.split(":", 1)[1].strip()
                elif line.startswith("理由:"):
                    result["reason"] = line.split(":", 1)[1].strip()

            logger.info(f"API调用成功: {product_data.get('asin', 'Unknown')}")
            return result

        except RateLimitError as e:
            last_error = e
            logger.warning(f"API速率限制 (尝试 {attempt}/{MAX_RETRIES}): {str(e)}")
            if attempt < MAX_RETRIES:
                wait_time = current_delay * 2  # 速率限制时等待更久
                logger.info(f"等待 {wait_time:.1f} 秒后重试...")
                time.sleep(wait_time)
                current_delay *= BACKOFF_FACTOR

        except APITimeoutError as e:
            last_error = e
            logger.warning(f"API请求超时 (尝试 {attempt}/{MAX_RETRIES}): {str(e)}")
            if attempt < MAX_RETRIES:
                logger.info(f"等待 {current_delay:.1f} 秒后重试...")
                time.sleep(current_delay)
                current_delay *= BACKOFF_FACTOR

        except APIConnectionError as e:
            last_error = e
            logger.warning(f"API连接错误 (尝试 {attempt}/{MAX_RETRIES}): {str(e)}")
            if attempt < MAX_RETRIES:
                logger.info(f"等待 {current_delay:.1f} 秒后重试...")
                time.sleep(current_delay)
                current_delay *= BACKOFF_FACTOR

        except APIError as e:
            last_error = e
            error_msg = str(e)
            logger.error(f"API调用失败 (尝试 {attempt}/{MAX_RETRIES}): {error_msg}")

            # 如果是500错误，继续重试
            if "500" in error_msg or "Internal Server Error" in error_msg:
                if attempt < MAX_RETRIES:
                    logger.info(f"服务器内部错误，等待 {current_delay:.1f} 秒后重试...")
                    time.sleep(current_delay)
                    current_delay *= BACKOFF_FACTOR
                    continue

            # 其他API错误，不重试
            break

        except Exception as e:
            last_error = e
            logger.error(f"未知错误 (尝试 {attempt}/{MAX_RETRIES}): {str(e)}")
            if attempt < MAX_RETRIES:
                logger.info(f"等待 {current_delay:.1f} 秒后重试...")
                time.sleep(current_delay)
                current_delay *= BACKOFF_FACTOR

    # 所有重试都失败
    error_message = f"API调用失败（已重试{MAX_RETRIES}次）: {str(last_error)}"
    logger.error(error_message)
    return {
        "is_correct": True,
        "suggested_category": "API错误",
        "reason": error_message
    }

def load_progress():
    """加载处理进度"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"processed_rows": 0, "output_file": OUTPUT_FILE}

def save_progress(processed_rows, output_file):
    """保存处理进度"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"processed_rows": processed_rows, "output_file": output_file}, f)

def process_csv():
    """处理CSV文件，验证每个产品的分类"""

    if not API_KEY:
        logger.error("未找到ANTHROPIC_API_KEY环境变量")
        print("错误: 未找到ANTHROPIC_API_KEY环境变量")
        print("请设置环境变量: export ANTHROPIC_API_KEY='your-api-key'")
        print("\nWindows设置方法:")
        print("  set ANTHROPIC_API_KEY=your-api-key")
        print("\nLinux/Mac设置方法:")
        print("  export ANTHROPIC_API_KEY='your-api-key'")
        sys.exit(1)

    if not os.path.exists(INPUT_FILE):
        logger.error(f"找不到输入文件 {INPUT_FILE}")
        print(f"错误: 找不到输入文件 {INPUT_FILE}")
        sys.exit(1)

    # 检查是否有未完成的进度
    progress = load_progress()
    start_from = progress.get("processed_rows", 0)

    if start_from > 0:
        logger.info(f"发现未完成的处理进度，从第 {start_from + 1} 行继续...")
        print(f"发现未完成的处理进度，从第 {start_from + 1} 行继续...")
        output_file = progress.get("output_file", OUTPUT_FILE)
    else:
        output_file = OUTPUT_FILE

    logger.info(f"开始处理文件: {INPUT_FILE}")
    logger.info(f"输出文件: {output_file}")
    logger.info(f"API配置: BASE_URL={BASE_URL}, TIMEOUT={REQUEST_TIMEOUT}s, MAX_RETRIES={MAX_RETRIES}")

    print(f"开始处理文件: {INPUT_FILE}")
    print(f"输出文件: {output_file}")
    print(f"API配置: 最大重试={MAX_RETRIES}次, 超时={REQUEST_TIMEOUT}秒, 请求间隔={REQUEST_INTERVAL}秒")
    if SAMPLE_MODE:
        print(f"⚠️  测试模式：只处理前 {SAMPLE_SIZE} 行")
    print("-" * 60)

    # 熔断器状态
    consecutive_failures = 0

    # 加载已验证的ASIN（从输出文件中读取）
    validated_asins = set()
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if '分类验证结果' in row and row['分类验证结果']:
                        validated_asins.add(row.get('asin', ''))
            logger.info(f"已加载 {len(validated_asins)} 个已验证的ASIN")
            print(f"✓ 已加载 {len(validated_asins)} 个已验证的ASIN，将自动跳过")
        except Exception as e:
            logger.warning(f"加载已验证ASIN失败: {e}")

    # 读取CSV
    with open(INPUT_FILE, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ['分类验证结果', '建议分类', '验证理由']

        rows = list(reader)

        # 如果是测试模式，只处理前N行
        if SAMPLE_MODE:
            rows = rows[:SAMPLE_SIZE]

        total_rows = len(rows)

        print(f"总共需要处理 {total_rows} 个产品")
        print("-" * 60)

        # 准备输出文件（添加UTF-8 BOM以支持Windows中文显示）
        file_mode = 'a' if start_from > 0 else 'w'
        with open(output_file, file_mode, encoding='utf-8-sig', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)

            # 只在新文件时写入表头
            if start_from == 0:
                writer.writeheader()

            # 处理每一行
            skipped_count = 0
            for idx, row in enumerate(rows, 1):
                # 跳过已处理的行
                if idx <= start_from:
                    continue

                # 检查是否已验证（跳过已验证的ASIN）
                current_asin = row.get('asin', '')
                if current_asin in validated_asins:
                    skipped_count += 1
                    logger.info(f"跳过已验证的ASIN: {current_asin}")
                    print(f"[{idx}/{total_rows}] ⏭️  跳过已验证: {current_asin} - {row.get('name', 'Unknown')[:40]}...")
                    continue

                # 检查熔断器
                if consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
                    logger.error(f"连续失败 {consecutive_failures} 次，触发熔断器，暂停处理")
                    print(f"\n❌ 连续失败 {consecutive_failures} 次，触发熔断器")
                    print(f"建议检查:")
                    print(f"  1. API服务是否正常: {BASE_URL}")
                    print(f"  2. API密钥是否有效")
                    print(f"  3. 网络连接是否稳定")
                    print(f"\n进度已保存，已处理 {idx - 1} 行")
                    print(f"修复问题后重新运行将从第 {idx} 行继续")
                    break

                print(f"[{idx}/{total_rows}] 处理: {row.get('name', 'Unknown')[:50]}...")

                try:
                    # 调用API验证分类
                    validation_result = validate_category(row)

                    # 检查是否是API错误
                    if validation_result['suggested_category'] == 'API错误':
                        consecutive_failures += 1
                        logger.warning(f"连续失败次数: {consecutive_failures}/{CIRCUIT_BREAKER_THRESHOLD}")
                    else:
                        consecutive_failures = 0  # 成功后重置计数器

                    # 添加验证结果到行数据
                    row['分类验证结果'] = '正确' if validation_result['is_correct'] else '需要修改'
                    row['建议分类'] = validation_result['suggested_category']
                    row['验证理由'] = validation_result['reason']

                    # 写入输出文件
                    writer.writerow(row)
                    outfile.flush()  # 立即写入磁盘

                    # 保存进度
                    save_progress(idx, output_file)

                    # 显示结果
                    if validation_result['suggested_category'] == 'API错误':
                        print(f"  ⚠️  API调用失败，已记录错误")
                    elif not validation_result['is_correct']:
                        print(f"  ⚠️  分类需要修改")
                        print(f"  当前: {row.get('category', 'N/A')[:60]}")
                        print(f"  建议: {validation_result['suggested_category'][:60]}")
                    else:
                        print(f"  ✓ 分类正确")

                    # 添加请求间隔避免API限流
                    if idx < total_rows:  # 最后一个不需要等待
                        time.sleep(REQUEST_INTERVAL)

                except KeyboardInterrupt:
                    logger.warning("用户中断处理")
                    print("\n\n⚠️  用户中断处理")
                    print(f"进度已保存，已处理 {idx} 行")
                    print(f"下次运行将从第 {idx + 1} 行继续")
                    sys.exit(0)
                except Exception as e:
                    logger.error(f"处理出错: {str(e)}", exc_info=True)
                    print(f"  ❌ 处理出错: {str(e)}")
                    consecutive_failures += 1

                    # 出错时也记录，但标记为错误
                    row['分类验证结果'] = '处理错误'
                    row['建议分类'] = 'N/A'
                    row['验证理由'] = f"错误: {str(e)}"
                    writer.writerow(row)
                    outfile.flush()
                    save_progress(idx, output_file)

                print()

            # 显示跳过统计
            if skipped_count > 0:
                print(f"\n✓ 跳过了 {skipped_count} 个已验证的产品")
                logger.info(f"跳过了 {skipped_count} 个已验证的产品")

    # 清除进度文件
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

    print("-" * 60)
    print(f"✅ 处理完成！结果已保存到: {output_file}")
    logger.info(f"处理完成！结果已保存到: {output_file}")

    # 统计信息
    with open(output_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        needs_change = sum(1 for row in rows if row['分类验证结果'] == '需要修改')
        correct = sum(1 for row in rows if row['分类验证结果'] == '正确')
        errors = sum(1 for row in rows if row['分类验证结果'] == '处理错误')

    print(f"\n统计信息:")
    print(f"  总产品数: {len(rows)}")
    print(f"  分类正确: {correct}")
    print(f"  需要修改: {needs_change}")
    print(f"  处理错误: {errors}")
    if correct + needs_change > 0:
        accuracy = (correct / (correct + needs_change) * 100)
        print(f"  准确率: {accuracy:.1f}%")
        logger.info(f"统计: 总数={len(rows)}, 正确={correct}, 需修改={needs_change}, 错误={errors}, 准确率={accuracy:.1f}%")

if __name__ == "__main__":
    process_csv()
