# Rewind Backend 测试指南

## 🚀 快速开始

### 1. 测试 LLM API 配置
```bash
cd /Users/icyfeather/Projects/Rewind/backend
uv run python scripts/test_llm.py
```

**预期输出**：
- ✅ LLM API 连接成功
- ✅ 基础对话测试通过
- ✅ 图片总结功能正常

### 2. 测试总结器功能
```bash
uv run python scripts/test_summarizer.py
```

**预期输出**：
- ✅ 事件筛选正常工作
- ✅ LLM 总结功能正常
- ✅ 不同场景总结准确

### 3. 测试完整管道
```bash
uv run python scripts/test_full_pipeline.py
```

**预期输出**：
- ✅ 事件创建和活动合并
- ✅ 数据库持久化正常
- ✅ 活动合并逻辑正确

## 📊 测试结果解读

### 事件筛选
- 从大量原始记录中筛选出重要事件
- 过滤掉重复和无关的操作
- 保留有意义的用户行为

### LLM 总结
- 将键盘、鼠标、截图事件转换为自然语言描述
- 按时间顺序交错排列文本和图片信息
- 生成简洁准确的活动总结

### 活动合并
- 将相关的事件合并为连续的活动
- 使用置信度评估合并的合理性
- 避免过度分割用户行为

## 🔧 配置说明

### LLM API 配置
在 `config/config.yaml` 中：
```yaml
llm:
  qwen3vl:
    api_key: "token-abc123"
    model: "qwen3vl_30b_instruct"
    base_url: "https://console.siflow.cn/siflow/auriga/skyinfer/mzchen/vllm-qwen3vl/v1/8001/v1"
  default_provider: "qwen3vl"
```

### 处理参数
- `processing_interval`: 处理间隔（秒）
- `capture_interval`: 捕获间隔（秒）
- `window_size`: 滑动窗口大小（秒）

## 🎯 测试场景

### 场景1: 文档编写
- 键盘输入文本
- 使用快捷键（Ctrl+A, Ctrl+C, Ctrl+V）
- 鼠标点击和滚动

### 场景2: 网页浏览
- 鼠标滚动页面
- 点击链接和按钮
- 键盘快捷键操作

### 场景3: 代码编辑
- 编写代码
- 使用保存快捷键（Ctrl+S）
- 截图记录状态

## 📈 性能指标

### 处理效率
- 事件筛选率：约 5-10%（从原始记录中筛选）
- 活动合并率：约 70-100%（相关事件合并）
- LLM 响应时间：1-2 秒

### 数据质量
- 总结准确性：高（基于 qwen3vl 模型）
- 活动识别：准确识别用户意图
- 时间精度：毫秒级时间戳

## 🐛 常见问题

### 1. LLM API 连接失败
- 检查网络连接
- 验证 API Key 和 URL
- 查看日志中的错误信息

### 2. 事件筛选过多
- 调整筛选规则阈值
- 检查输入数据质量
- 优化筛选算法

### 3. 总结质量不佳
- 调整 LLM 参数（temperature, max_tokens）
- 优化提示词模板
- 检查输入数据格式

## 🔄 持续测试

### 自动化测试
```bash
# 运行所有测试
uv run python -m pytest tests/

# 运行特定测试
uv run python -m pytest tests/test_processing.py
```

### 性能监控
- 查看日志文件：`logs/rewind_backend.log`
- 监控数据库大小：`rewind.db`
- 检查内存使用情况

## 📝 开发建议

1. **添加新测试场景**：在 `test_full_pipeline.py` 中添加更多用户行为模拟
2. **优化筛选规则**：根据实际使用情况调整 `filter_rules.py`
3. **改进总结质量**：调整 LLM 提示词和参数
4. **增强活动合并**：优化 `merger.py` 中的合并逻辑

## 🎉 成功标志

当看到以下输出时，说明系统工作正常：
- ✅ 所有测试脚本运行成功
- ✅ LLM API 响应正常
- ✅ 事件和活动创建合理
- ✅ 数据库持久化正常
- ✅ 无严重错误日志
