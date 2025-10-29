#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试JSON解析工具的功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.json_parser import parse_json_from_response, validate_json_schema


def test_json_parser():
    """测试各种JSON解析场景"""

    print("=" * 60)
    print("测试 JSON 解析工具")
    print("=" * 60)

    # 测试用例1: 代码块包裹的JSON
    print("\n[测试1] 代码块包裹的JSON:")
    response1 = """
    这是一些说明文字

    ```json
    {
        "should_merge": true,
        "reason": "相关活动",
        "merged_title": "编写代码",
        "merged_description": "在VS Code中编写Python代码"
    }
    ```

    这是后面的文字
    """
    result1 = parse_json_from_response(response1)
    print(f"输入: {response1[:100]}...")
    print(f"解析结果: {result1}")
    print(f"✓ 成功" if result1 else "✗ 失败")

    # 测试用例2: 纯JSON
    print("\n[测试2] 纯JSON字符串:")
    response2 = '{"title": "浏览网页", "description": "在Chrome中浏览技术文档"}'
    result2 = parse_json_from_response(response2)
    print(f"输入: {response2}")
    print(f"解析结果: {result2}")
    print(f"✓ 成功" if result2 else "✗ 失败")

    # 测试用例3: 混合文本中的JSON
    print("\n[测试3] 混合文本中的JSON:")
    response3 = """
    根据分析，我认为这两个活动应该合并。

    判断结果如下：
    {
        "should_merge": false,
        "reason": "完全不相关",
        "merged_title": "",
        "merged_description": ""
    }

    以上是我的分析结果。
    """
    result3 = parse_json_from_response(response3)
    print(f"输入: {response3[:100]}...")
    print(f"解析结果: {result3}")
    print(f"✓ 成功" if result3 else "✗ 失败")

    # 测试用例4: 格式不完美的JSON（有尾随逗号）
    print("\n[测试4] 带尾随逗号的JSON:")
    response4 = """{
        "title": "写文档",
        "description": "编写API文档",
    }"""
    result4 = parse_json_from_response(response4)
    print(f"输入: {response4}")
    print(f"解析结果: {result4}")
    print(f"✓ 成功" if result4 else "✗ 失败")

    # 测试用例5: 无markdown标记的代码块
    print("\n[测试5] 无markdown标记的代码块:")
    response5 = """
    ```
    {
        "should_merge": true,
        "reason": "同一项目",
        "merged_title": "开发功能",
        "merged_description": "开发新功能并测试"
    }
    ```
    """
    result5 = parse_json_from_response(response5)
    print(f"输入: {response5[:100]}...")
    print(f"解析结果: {result5}")
    print(f"✓ 成功" if result5 else "✗ 失败")

    # 测试用例6: 字段验证
    print("\n[测试6] 字段验证:")
    response6 = '{"title": "测试", "description": "这是描述"}'
    result6 = parse_json_from_response(response6)
    if result6:
        is_valid = validate_json_schema(result6, ["title", "description"])
        print(f"输入: {response6}")
        print(f"解析结果: {result6}")
        print(f"字段验证: {'✓ 通过' if is_valid else '✗ 失败（缺少必需字段）'}")

        # 测试缺少字段的情况
        is_invalid = validate_json_schema(result6, ["title", "description", "missing_field"])
        print(f"缺少字段测试: {'✗ 按预期失败' if not is_invalid else '✓ 意外通过'}")

    # 统计
    print("\n" + "=" * 60)
    print("测试总结:")
    all_results = [result1, result2, result3, result4, result5, result6]
    success_count = sum(1 for r in all_results if r is not None)
    print(f"成功: {success_count}/{len(all_results)}")
    print("=" * 60)


if __name__ == "__main__":
    test_json_parser()
