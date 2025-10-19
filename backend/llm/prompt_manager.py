"""
LLM Prompt 管理器
从YAML配置文件读取和管理所有LLM prompt模板
"""

import yaml
import toml
import os
from typing import Dict, Any, List, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class PromptManager:
    """Prompt管理器"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # 默认配置文件路径，优先使用TOML格式
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            toml_path = os.path.join(current_dir, "config", "prompts.toml")
            yaml_path = os.path.join(current_dir, "config", "prompts.yaml")
            
            if os.path.exists(toml_path):
                config_path = toml_path
            elif os.path.exists(yaml_path):
                config_path = yaml_path
            else:
                config_path = toml_path  # 默认使用TOML
        
        self.config_path = config_path
        self.prompts = {}
        self.config = {}
        self._load_prompts()
    
    def _load_prompts(self):
        """加载prompt配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                if self.config_path.endswith('.toml'):
                    self.config = toml.load(f)
                else:
                    self.config = yaml.safe_load(f)
            
            # 提取prompts部分
            self.prompts = self.config.get('prompts', {})
            logger.info(f"成功加载prompt配置: {self.config_path}")
            
        except FileNotFoundError:
            logger.error(f"Prompt配置文件不存在: {self.config_path}")
            self.prompts = {}
            self.config = {}
        except (yaml.YAMLError, toml.TomlDecodeError) as e:
            logger.error(f"解析prompt配置文件失败: {e}")
            self.prompts = {}
            self.config = {}
        except Exception as e:
            logger.error(f"加载prompt配置失败: {e}")
            self.prompts = {}
            self.config = {}
    
    def get_prompt(self, category: str, prompt_type: str, **kwargs) -> str:
        """
        获取指定类型的prompt
        
        Args:
            category: prompt分类 (如: event_summarization, activity_merging.merge_judgment)
            prompt_type: prompt类型 (如: system_prompt, user_prompt_template)
            **kwargs: 用于格式化模板的参数
        
        Returns:
            格式化后的prompt字符串
        """
        try:
            # 处理嵌套路径，如 "activity_merging.merge_judgment"
            category_parts = category.split('.')
            category_config = self.prompts
            
            # 遍历嵌套路径
            for part in category_parts:
                if isinstance(category_config, dict) and part in category_config:
                    category_config = category_config[part]
                else:
                    logger.warning(f"未找到prompt分类: {category}")
                    return ""
            
            # 获取prompt模板
            if not isinstance(category_config, dict):
                logger.warning(f"prompt分类不是字典类型: {category}")
                return ""
                
            prompt_template = category_config.get(prompt_type, "")
            
            if not prompt_template:
                logger.warning(f"未找到prompt: {category}.{prompt_type}")
                return ""
            
            # 格式化模板
            if kwargs:
                try:
                    return prompt_template.format(**kwargs)
                except KeyError as e:
                    logger.error(f"格式化prompt失败，缺少参数: {e}")
                    return prompt_template
            else:
                return prompt_template
                
        except Exception as e:
            logger.error(f"获取prompt失败: {e}")
            return ""
    
    def get_system_prompt(self, category: str) -> str:
        """获取系统prompt"""
        return self.get_prompt(category, "system_prompt")
    
    def get_user_prompt(self, category: str, prompt_type: str = "user_prompt_template", **kwargs) -> str:
        """获取用户prompt"""
        return self.get_prompt(category, prompt_type, **kwargs)
    
    def build_messages(self, category: str, prompt_type: str = "user_prompt_template", **kwargs) -> List[Dict[str, str]]:
        """
        构建完整的消息列表
        
        Args:
            category: prompt分类
            prompt_type: 用户prompt类型
            **kwargs: 用于格式化模板的参数
        
        Returns:
            消息列表，包含system和user消息
        """
        messages = []
        
        # 添加系统消息
        system_prompt = self.get_system_prompt(category)
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # 添加用户消息
        user_prompt = self.get_user_prompt(category, prompt_type, **kwargs)
        if user_prompt:
            messages.append({
                "role": "user",
                "content": user_prompt
            })
        
        return messages
    
    def get_config_params(self, category: str, prompt_type: str = None) -> Dict[str, Any]:
        """
        获取指定功能的配置参数
        
        Args:
            category: prompt分类
            prompt_type: 特定prompt类型（可选）
        
        Returns:
            配置参数字典
        """
        try:
            config_params = self.config.get('config', {}).get('default_params', {})
            
            # 获取特定功能的参数
            if category in self.config.get('config', {}):
                category_params = self.config['config'][category]
                if isinstance(category_params, dict):
                    config_params.update(category_params)
            
            # 获取特定prompt类型的参数
            if prompt_type and category in self.config.get('config', {}):
                specific_params = self.config['config'][category].get(prompt_type, {})
                if isinstance(specific_params, dict):
                    config_params.update(specific_params)
            
            return config_params
            
        except Exception as e:
            logger.error(f"获取配置参数失败: {e}")
            return self.config.get('config', {}).get('default_params', {})
    
    def reload(self):
        """重新加载配置"""
        self._load_prompts()
        logger.info("Prompt配置已重新加载")


# 全局prompt管理器实例
_prompt_manager = None


def get_prompt_manager() -> PromptManager:
    """获取全局prompt管理器实例"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


# 便捷函数
def get_event_summarization_prompt(**kwargs) -> List[Dict[str, str]]:
    """获取事件总结prompt"""
    manager = get_prompt_manager()
    return manager.build_messages("event_summarization", **kwargs)


def get_merge_judgment_prompt(current_summary: str, new_summary: str) -> List[Dict[str, str]]:
    """获取合并判断prompt"""
    manager = get_prompt_manager()
    return manager.build_messages(
        "activity_merging.merge_judgment", 
        "user_prompt_template",
        current_summary=current_summary,
        new_summary=new_summary
    )


def get_merge_description_prompt(current_description: str, new_event_summary: str) -> List[Dict[str, str]]:
    """获取合并描述prompt"""
    manager = get_prompt_manager()
    return manager.build_messages(
        "activity_merging.merge_description",
        "user_prompt_template",
        current_description=current_description,
        new_event_summary=new_event_summary
    )


def get_general_summary_prompt(content: str) -> List[Dict[str, str]]:
    """获取通用总结prompt"""
    manager = get_prompt_manager()
    messages = manager.build_messages("general_summary")
    if messages and len(messages) > 1:
        messages[1]["content"] = content
    return messages


def get_test_prompt() -> List[Dict[str, str]]:
    """获取测试prompt"""
    manager = get_prompt_manager()
    return manager.build_messages("event_summarization", "test_user_prompt")
