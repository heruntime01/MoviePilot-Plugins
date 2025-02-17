import time
from typing import Any, List, Dict, Optional

from app.core.event import eventmanager, Event
from app.helper.mediaserver import MediaServerHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import ServiceInfo
from app.schemas.types import EventType, MediaType, MediaImageType, NotificationType
from app.utils.web import WebUtils


class MediaLibInfo(_PluginBase):
    # 插件名称
    plugin_name = "medialibinfo"
    # 插件描述
    plugin_desc = "获取媒体库服务器（Emby/Jellyfin/Plex）的媒体库名称及内容等信息。"
    # 插件图标
    plugin_icon = "medialibrary.png"
    # 插件版本
    plugin_version = "1.1"
    # 插件作者
    plugin_author = "heruntime01"
    # 作者主页
    author_url = "https://github.com/heruntime01"
    # 插件配置项ID前缀
    plugin_config_prefix = "medialibinfo_"
    # 加载顺序
    plugin_order = 15
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    mediaserver_helper = None
    _enabled = False
    _mediaservers = None

    def init_plugin(self, config: dict = None):
        self.mediaserver_helper = MediaServerHelper()
        if config:
            self._enabled = config.get("enabled")
            self._mediaservers = config.get("mediaservers") or []

    def service_infos(self, type_filter: Optional[str] = None) -> Optional[Dict[str, ServiceInfo]]:
        """
        服务信息
        """
        if not self._mediaservers:
            logger.warning("尚未配置媒体服务器，请检查配置")
            return None

        services = self.mediaserver_helper.get_services(type_filter=type_filter, name_filters=self._mediaservers)
        if not services:
            logger.warning("获取媒体服务器实例失败，请检查配置")
            return None

        active_services = {}
        for service_name, service_info in services.items():
            if service_info.instance.is_inactive():
                logger.warning(f"媒体服务器 {service_name} 未连接，请检查配置")
            else:
                active_services[service_name] = service_info

        if not active_services:
            logger.warning("没有已连接的媒体服务器，请检查配置")
            return None

        return active_services

    def service_info(self, name: str) -> Optional[ServiceInfo]:
        """
        服务信息
        """
        service_infos = self.service_infos() or {}
        return service_infos.get(name)

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

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
                                        'component': 'VSelect',
                                        'props': {
                                            'multiple': True,
                                            'chips': True,
                                            'clearable': True,
                                            'model': 'mediaservers',
                                            'label': '媒体服务器',
                                            'items': [{"title": config.name, "value": config.name}
                                                      for config in self.mediaserver_helper.get_configs().values()]
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
            "mediaservers": []
        }

    def get_page(self) -> List[dict]:
        """
        获取媒体库信息页面
        """
        if not self._enabled:
            return []

        media_libraries = []
        services = self.service_infos()
        if services:
            for service_name, service_info in services.items():
                libraries = service_info.instance.get_libraries()
                if libraries:
                    for library in libraries:
                        media_libraries.append({
                            "library_name": library.name,
                            "library_type": library.type,
                            "library_items": library.items,
                            "server_name": service_name
                        })

        return [
            {
                'component': 'VTable',
                'props': {
                    'headers': [
                        {"text": "媒体库名称", "value": "library_name"},
                        {"text": "媒体库类型", "value": "library_type"},
                        {"text": "媒体库内容", "value": "library_items"},
                        {"text": "媒体服务器", "value": "server_name"}
                    ],
                    'items': media_libraries
                }
            }
        ]

    @eventmanager.register(EventType.MediaLibraryUpdated)
    def update(self, event: Event):
        """
        媒体库更新事件处理
        """
        if not self._enabled:
            return

        logger.info("媒体库更新事件触发，正在获取媒体库信息")
        self.get_page()

    def stop_service(self):
        """
        退出插件
        """
        pass