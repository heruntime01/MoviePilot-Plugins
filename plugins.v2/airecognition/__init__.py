from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.core.event import eventmanager, EventType
from app.plugins import _PluginBase
from app.log import logger
from app.schemas import NotificationType


class AiRecognition(_PluginBase):
    """
    AI辅助识别插件
    插件目录名必须与插件类名一致(区分大小写)
    """
    # 插件信息
    plugin_name = "AI辅助识别"
    plugin_desc = "使用AI技术辅助识别影视信息"
    plugin_version = "1.0"
    plugin_author = "heruntime01"
    # 作者主页
    author_url = "https://github.com/heruntime01"
    # 插件配置项ID前缀
    plugin_config_prefix = "airecognition_"
    # 加载顺序
    plugin_order = 18
    # 可使用的用户级别
    auth_level = 1
    # 版本标识
    plugin_version_flag = "v2"

    # 私有属性
    _enabled = False
    _debug = False
    _name_format = None

    def init_plugin(self, config: Dict[str, Any] = None) -> None:
        """
        插件初始化
        """
        # 检查版本
        if not hasattr(settings, 'VERSION_FLAG') or settings.VERSION_FLAG != "v2":
            return

        # 初始化配置
        if config:
            self._enabled = config.get("enabled")
            self._debug = config.get("debug")
            self._name_format = config.get("name_format")
            self.plugin_config.update(config)

        logger.info(f"AI辅助识别服务启动，调试模式：{self._debug}")

    @eventmanager.register(EventType.NameRecognizeMediaInfo)
    def recognize(self, event):
        """
        对接收到的识别事件进行处理
        """
        if not self._enabled:
            return
            
        # 获取需要识别的标题
        title = event.event_data.get("title")
        if not title:
            self._send_empty_result(title)
            return

        try:
            if self._debug:
                logger.info(f"开始识别标题: {title}")

            # AI识别逻辑
            import re
            
            # 识别年份
            year_match = re.search(r'[12][0-9]{3}', title)
            year = year_match.group() if year_match else None
            
            # 识别季数
            season_match = re.search(r'S(\d{1,2})', title, re.IGNORECASE)
            season = int(season_match.group(1)) if season_match else None
            
            # 识别集数
            episode_match = re.search(r'E(\d{1,3})', title, re.IGNORECASE)
            episode = int(episode_match.group(1)) if episode_match else None
            
            # 清理标题
            name = re.sub(r'[sS]\d{1,2}.*$', '', title)
            name = re.sub(r'\([12][0-9]{3}\)', '', name)
            name = name.strip()

            # 应用自定义格式
            if self._name_format and name:
                try:
                    name = self._name_format.format(name=name)
                except Exception as e:
                    logger.error(f"应用自定义格式失败: {str(e)}")

            if self._debug:
                logger.info(f"识别结果: 名称={name}, 年份={year}, 季={season}, 集={episode}")

            # 发送结果
            self._send_recognize_result(
                title=title,
                name=name,
                year=year,
                season=season,
                episode=episode
            )

        except Exception as e:
            logger.error(f"识别出错: {str(e)}")
            self._send_empty_result(title)

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        """
        return []

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
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
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
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
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'debug',
                                            'label': '调试日志',
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
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'name_format',
                                            'label': '标题格式化',
                                            'placeholder': '使用{name}作为标题占位符，例如：[AI]{name}'
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
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '本插件提供基于正则表达式的标题识别功能，可以识别年份、季数和集数。开启调试日志可查看详细识别过程。'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "debug": False,
            "name_format": ""
        }

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        """
        退出插件
        """
        pass

    def _send_recognize_result(self, **kwargs):
        """
        发送识别结果事件
        """
        eventmanager.send_event(
            EventType.NameRecognizeResult,
            kwargs
        )

    def _send_empty_result(self, title):
        """
        发送空识别结果
        """
        eventmanager.send_event(
            EventType.NameRecognizeResult,
            {"title": title}
        ) 