#!/usr/bin/env python3
"""
验证活动合并逻辑的修改
检查prompt和代码是否正确更新
"""

import sys
import os
import re

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_prompts_toml():
    """检查prompts.toml是否正确更新"""
    print("✅ 检查prompts.toml...")

    prompts_path = os.path.join(os.path.dirname(__file__), "..", "config", "prompts.toml")
    with open(prompts_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否包含新的宽松合并策略描述
    if "请采用较宽松的合并策略" in content:
        print("  ✓ System prompt已更新为宽松策略")
    else:
        print("  ✗ System prompt未更新")
        return False

    if "满足任一即可考虑合并" in content:
        print("  ✓ User prompt包含宽松合并因素")
    else:
        print("  ✗ User prompt未包含宽松合并因素")
        return False

    # 检查是否删除了confidence字段
    merge_judgment_section = content[content.find("[prompts.activity_merging.merge_judgment]"):]
    merge_judgment_section = merge_judgment_section[:merge_judgment_section.find("\n\n[")]

    if '"confidence"' not in merge_judgment_section:
        print("  ✓ Confidence字段已从prompt中删除")
    else:
        print("  ✗ Confidence字段仍存在于prompt中")
        return False

    return True

def check_merger_py():
    """检查merger.py是否正确更新"""
    print("\n✅ 检查merger.py...")

    merger_path = os.path.join(os.path.dirname(__file__), "..", "processing", "merger.py")
    with open(merger_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查_llm_judge_merge的返回类型
    if "Tuple[bool, str]:" in content and "_llm_judge_merge" in content:
        print("  ✓ _llm_judge_merge返回类型已更新（删除confidence）")
    else:
        print("  ✗ _llm_judge_merge返回类型未正确更新")
        return False

    # 检查_parse_merge_judgment的返回类型
    if "def _parse_merge_judgment(self, content: str) -> Tuple[bool, str]:" in content:
        print("  ✓ _parse_merge_judgment返回类型已更新")
    else:
        print("  ✗ _parse_merge_judgment返回类型未正确更新")
        return False

    # 检查解析代码中是否还在获取confidence
    parse_section = content[content.find("def _parse_merge_judgment"):]
    parse_section = parse_section[:parse_section.find("\n    async def") if "\n    async def" in parse_section else len(parse_section)]

    if 'result.get("confidence"' not in parse_section:
        print("  ✓ 解析代码中已删除confidence字段处理")
    else:
        print("  ✗ 解析代码中仍在处理confidence字段")
        return False

    return True

def check_pipeline_py():
    """检查pipeline.py是否正确更新"""
    print("\n✅ 检查pipeline.py...")

    pipeline_path = os.path.join(os.path.dirname(__file__), "..", "processing", "pipeline.py")
    with open(pipeline_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查调用_llm_judge_merge时是否还在接收confidence
    if "should_merge, merged_description = await self.merger._llm_judge_merge" in content:
        print("  ✓ 调用_llm_judge_merge时已删除confidence变量")
    else:
        print("  ✗ 调用_llm_judge_merge时仍在使用confidence变量")
        return False

    # 检查日志中是否还在打印confidence
    if "置信度: {confidence" not in content or "logger.info(f\"事件已合并到当前活动\")" in content:
        print("  ✓ 日志输出已更新（删除confidence）")
    else:
        print("  ✗ 日志输出仍在打印confidence")
        return False

    return True

def main():
    print("🔍 验证活动合并逻辑修改")
    print("=" * 60)

    all_passed = True

    # 检查所有文件
    all_passed &= check_prompts_toml()
    all_passed &= check_merger_py()
    all_passed &= check_pipeline_py()

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有检查通过！修改正确。")
        print("\n📝 修改摘要:")
        print("1. ✓ Prompt已更新为更宽松的合并策略")
        print("2. ✓ Confidence字段已从所有代码中删除")
        print("3. ✓ 相关代码逻辑已相应更新")
        return 0
    else:
        print("❌ 部分检查未通过，请检查修改。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
