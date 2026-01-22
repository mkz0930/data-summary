#!/usr/bin/env python3
"""
API连接测试脚本
用于测试Claude API代理服务器的连接状态
"""

import os
import sys
import time
from anthropic import Anthropic, APIError, APIConnectionError, APITimeoutError, RateLimitError

# 配置
API_KEY = os.environ.get("ANTHROPIC_API_KEY") or "NZNJMPGF-UXXZ-CVX1-VJ1N-PWBCBTVFD73R"
BASE_URL = "https://yunyi.cfd/claude"
TIMEOUT = 60.0

def test_api_connection():
    """测试API连接"""
    print("=" * 60)
    print("Claude API 连接测试")
    print("=" * 60)
    print(f"API端点: {BASE_URL}")
    print(f"超时设置: {TIMEOUT}秒")
    print(f"API密钥: {API_KEY[:20]}..." if len(API_KEY) > 20 else f"API密钥: {API_KEY}")
    print("-" * 60)

    try:
        print("\n[1/3] 创建API客户端...")
        client = Anthropic(
            api_key=API_KEY,
            base_url=BASE_URL,
            timeout=TIMEOUT
        )
        print("✓ 客户端创建成功")

        print("\n[2/3] 发送测试请求...")
        start_time = time.time()

        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=50,
            messages=[
                {"role": "user", "content": "请用一句话回复：你好"}
            ]
        )

        elapsed_time = time.time() - start_time
        print(f"✓ 请求成功 (耗时: {elapsed_time:.2f}秒)")

        print("\n[3/3] 解析响应...")
        response_text = message.content[0].text
        print(f"✓ 响应内容: {response_text}")

        print("\n" + "=" * 60)
        print("✅ API连接测试通过！")
        print("=" * 60)
        print("\n建议:")
        print("  - API服务正常，可以继续使用")
        print(f"  - 平均响应时间: {elapsed_time:.2f}秒")

        return True

    except RateLimitError as e:
        print(f"\n❌ 速率限制错误:")
        print(f"   {str(e)}")
        print("\n建议:")
        print("  - 等待一段时间后重试")
        print("  - 检查API配额是否用完")
        return False

    except APITimeoutError as e:
        print(f"\n❌ 请求超时:")
        print(f"   {str(e)}")
        print("\n建议:")
        print("  - 增加超时时间设置")
        print("  - 检查网络连接")
        print("  - 检查代理服务器状态")
        return False

    except APIConnectionError as e:
        print(f"\n❌ 连接错误:")
        print(f"   {str(e)}")
        print("\n建议:")
        print("  - 检查网络连接")
        print("  - 检查代理服务器地址是否正确")
        print(f"  - 尝试访问: {BASE_URL}")
        print("  - 检查防火墙设置")
        return False

    except APIError as e:
        error_msg = str(e)
        print(f"\n❌ API错误:")
        print(f"   {error_msg}")

        if "500" in error_msg or "Internal Server Error" in error_msg:
            print("\n这是服务器内部错误 (500)，可能的原因:")
            print("  1. 代理服务器出现故障")
            print("  2. API密钥无效或格式错误")
            print("  3. 代理服务器配置问题")
            print("\n建议:")
            print("  - 检查API密钥是否有效")
            print("  - 联系代理服务提供商")
            print("  - 考虑使用官方Anthropic API端点")
        elif "401" in error_msg or "Unauthorized" in error_msg:
            print("\n这是认证错误 (401):")
            print("  - API密钥无效或已过期")
            print("\n建议:")
            print("  - 检查API密钥是否正确")
            print("  - 重新获取API密钥")
        elif "403" in error_msg or "Forbidden" in error_msg:
            print("\n这是权限错误 (403):")
            print("  - 没有访问权限")
            print("\n建议:")
            print("  - 检查API密钥权限")
            print("  - 联系服务提供商")
        else:
            print("\n建议:")
            print("  - 查看详细错误信息")
            print("  - 联系技术支持")

        return False

    except Exception as e:
        print(f"\n❌ 未知错误:")
        print(f"   {str(e)}")
        print(f"   类型: {type(e).__name__}")
        print("\n建议:")
        print("  - 检查所有配置")
        print("  - 查看完整错误堆栈")
        return False

def main():
    """主函数"""
    success = test_api_connection()

    if not success:
        print("\n" + "=" * 60)
        print("替代方案:")
        print("=" * 60)
        print("\n1. 使用官方Anthropic API:")
        print("   - 注册账号: https://console.anthropic.com/")
        print("   - 获取API密钥 (格式: sk-ant-...)")
        print("   - 修改代码移除 base_url 参数")
        print("\n2. 检查代理服务器:")
        print(f"   - 确认 {BASE_URL} 是否可访问")
        print("   - 联系代理服务提供商")
        print("\n3. 临时跳过API验证:")
        print("   - 在 product_classifier.py 中设置 SAMPLE_MODE = True")
        print("   - 先处理其他数据分析任务")

        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
