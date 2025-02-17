import json
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.core.event import eventmanager, Event
from app.plugins import _PluginBase
from app.log import logger
from app.schemas import NotificationType
from app.schemas.types import EventType, MediaType
from .openai import OpenAiClient

class AutoSubscribe(_PluginBase):
    """
    智能订阅助手
    使用 AI 辅助识别媒体信息并返回演员表
    """
    # 插件信息
    plugin_name = "智能订阅助手"
    plugin_desc = "使用 AI 辅助识别媒体信息并返回演员表，支持自动订阅"
    plugin_version = "1.0"
    plugin_author = "heruntime01"
    author_url = "https://github.com/heruntime01"
    plugin_config_prefix = "autosubscribe_"
    plugin_order = 19
    auth_level = 1
    plugin_version_flag = "v2"

    # 私有属性
    _enabled = False
    _openai_key = None
    _proxy = None
    _auto_subscribe = False
    _client = None

    def init_plugin(self, config: Dict[str, Any] = None) -> None:
        if not config:
            return
        
        self._enabled = config.get("enabled")
        self._openai_key = config.get("openai_key")
        self._proxy = config.get("proxy")
        self._auto_subscribe = config.get("auto_subscribe", False)

        # 初始化 OpenAI 客户端
        if self._enabled and self._openai_key:
            self._client = OpenAiClient(
                api_key=self._openai_key,
                proxy=self._proxy
            )

    def get_state(self) -> bool:
        return self._enabled

    @eventmanager.register(EventType.UserMessage)
    def handle_message(self, event: Event):
        """
        处理用户消息
        """
        if not self._enabled or not self._client:
            return

        message = event.event_data.get("text")
        if not message:
            return

        # 构建提示词
        prompt = f"""
        请分析这个标题是否是电影或电视剧：{message}
        如果是，请提供以下信息：
        1. 类型（电影/电视剧）
        2. 标准名称
        3. 年份
        4. 主要演员表（至少3个）
        5. 简要剧情介绍
        
        如果不是影视作品，请回复：这不是一个影视作品。
        """

        try:
            # 调用 GPT 获取分析结果
            response = self._client.chat_completion(prompt)
            if not response:
                return
            
            # 发送结果通知
            self.post_message(
                title="媒体信息分析",
                text=response
            )

            # 如果开启了自动订阅，触发订阅事件
            if self._auto_subscribe and "这不是一个影视作品" not in response:
                self._trigger_subscribe(message, response)

        except Exception as e:
            logger.error(f"处理消息失败: {str(e)}")

    def _trigger_subscribe(self, title: str, info: str):
        """
        触发订阅事件
        """
        try:
            # 解析 GPT 返回的信息
            media_info = self._parse_media_info(info)
            if media_info:
                # 发送订阅事件
                eventmanager.send_event(
                    EventType.Subscribe,
                    {
                        "name": media_info.get("name"),
                        "year": media_info.get("year"),
                        "type": media_info.get("type"),
                        "title": title,
                    }
                )
        except Exception as e:
            logger.error(f"触发订阅失败: {str(e)}")

    def _parse_media_info(self, info: str) -> Optional[Dict]:
        """
        解析媒体信息
        """
        try:
            # 简单的信息提取
            lines = info.split('\n')
            media_info = {}
            
            for line in lines:
                if "类型：" in line:
                    media_info["type"] = "电影" if "电影" in line else "电视剧"
                elif "标准名称：" in line:
                    media_info["name"] = line.split("：")[1].strip()
                elif "年份：" in line:
                    media_info["year"] = line.split("：")[1].strip()
            
            return media_info
        except Exception as e:
            logger.error(f"解析媒体信息失败: {str(e)}")
            return None

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        插件配置页面
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'auto_subscribe',
                                            'label': '自动订阅'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'openai_key',
                                            'label': 'OpenAI API Key',
                                            'placeholder': 'sk-xxx'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'proxy',
                                            'label': '代理服务器',
                                            'placeholder': 'http://127.0.0.1:7890'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            'enabled': False,
            'openai_key': '',
            'proxy': '',
            'auto_subscribe': False
        }

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        pass 