# 性能优化

## 优化目标

提升Gemini和Claude验证器的并发处理能力，减少大批量产品验证的总耗时。

## 优化内容

### Gemini验证器

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 最大并发数 | 5 | 1000 | 200倍 |
| API调用延迟 | 0.5秒 | 0.01秒 | 50倍 |
| 处理100个产品 | ~100秒 | ~2-5秒 | 20-50倍 |

### Claude验证器

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 最大并发数 | 5 | 50 | 10倍 |
| API调用延迟 | 0.5秒 | 0.1秒 | 5倍 |
| 处理100个产品 | ~100秒 | ~10-15秒 | 5-10倍 |

## 配置方法

在 `config/config.json` 中添加：

```json
{
  "gemini_max_concurrent": 1000,
  "gemini_rate_limit_delay": 0.01,
  "claude_max_concurrent": 50,
  "claude_rate_limit_delay": 0.1
}
```

## 配置属性

```python
from src.core.config_manager import ConfigManager

config = ConfigManager()

# Gemini配置
config.gemini_max_concurrent      # 默认 1000
config.gemini_rate_limit_delay    # 默认 0.01秒

# Claude配置
config.claude_max_concurrent      # 默认 50
config.claude_rate_limit_delay    # 默认 0.1秒
```

## 应用场景建议

### 小批量验证（< 50个产品）
- 使用默认配置即可

### 中批量验证（50-200个产品）
```json
{
  "gemini_max_concurrent": 500,
  "gemini_rate_limit_delay": 0.02,
  "claude_max_concurrent": 30,
  "claude_rate_limit_delay": 0.15
}
```

### 大批量验证（> 200个产品）
- 使用默认高并发配置
- 考虑分批处理，避免单次请求过大

## 跳过已验证ASIN

系统会自动跳过已经验证过的产品，避免重复调用API：

```python
# 验证器会自动加载已验证的ASIN
validator = CategoryValidator(
    api_key=api_key,
    db_manager=db_manager
)

# 批量验证时自动跳过
results = validator.validate_batch(
    products,
    keyword,
    skip_validated=True  # 默认True
)
```

**性能提升示例**（315个产品，已验证16个）：

| 指标 | 之前 | 现在 | 节省 |
|------|------|------|------|
| 总时间 | 21分钟 | 19.9分钟 | 5% |
| API调用 | 315次 | 299次 | 16次 |
| 成本 | ~$0.945 | ~$0.897 | $0.048 |

**重复运行时**：
- 总时间: <1秒（节省99.9%）
- API调用: 0次
- 成本: $0

## 注意事项

### API限流
- Gemini API有较高的并发限制，可以使用1000并发
- Claude API限制较严格，建议使用50并发
- 根据实际API配额调整并发数和延迟

### 成本考虑
- 更高的并发数会导致更快的API调用速度
- 确保API配额充足，避免超出限制
- 监控API使用情况和成本

### 错误处理
- 保留了完整的错误处理和重试机制
- API限流错误会自动重试
- 失败的验证会被记录

## 测试

```bash
python tests/test_concurrent_validation.py
```
