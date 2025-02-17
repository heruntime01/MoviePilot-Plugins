import time
from typing import Any, List, Dict, Optional, Tuple
from datetime import datetime

from app.core.event import eventmanager, Event
from app.helper.mediaserver import MediaServerHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import ServiceInfo, Notification
from app.schemas.types import EventType, MediaType, NotificationType
from app.utils.web import WebUtils


class MediaLibInfo(_PluginBase):
    """
    媒体库信息插件
    获取媒体服务器中的媒体库信息并展示
    """
    # 插件信息
    plugin_name = "媒体库信息"
    plugin_desc = "获取媒体库服务器（Emby/Jellyfin/Plex）的媒体库名称及内容等信息。"
    plugin_icon = "medialibrary.png"
    plugin_version = "1.1"
    plugin_author = "heruntime01"
    author_url = "https://github.com/heruntime01"
    plugin_config_prefix = "medialibinfo_"
    plugin_order = 15
    auth_level = 1
    plugin_version_flag = "v2"

    # 私有属性
    _enabled = False
    _debug = False
    _notify = False
    _mediaservers = None
    _last_update_time = None

    def init_plugin(self, config: dict = None):
        """
        插件初始化
        """
        self.mediaserver_helper = MediaServerHelper()
        
        if config:
            self._enabled = config.get("enabled", False)
            self._debug = config.get("debug", False)
            self._notify = config.get("notify", False)
            self._mediaservers = config.get("mediaservers", [])
            self.plugin_config.update(config)

        logger.info(f"媒体库信息插件启动，调试模式：{self._debug}")

    def get_service_info(self, name: str = None) -> Optional[Dict[str, ServiceInfo]]:
        """
        获取媒体服务器信息
        """
        if not self._mediaservers:
            if self._debug:
                logger.warning("尚未配置媒体服务器")
            return None

        try:
            if name:
                service = self.mediaserver_helper.get_service(name=name)
                return {name: service} if service and not service.instance.is_inactive() else None
            else:
                services = self.mediaserver_helper.get_services(name_filters=self._mediaservers)
                return {name: service for name, service in services.items() 
                       if service and not service.instance.is_inactive()}
        except Exception as e:
            logger.error(f"获取媒体服务器信息出错: {str(e)}")
            return None

    def get_libraries_info(self) -> List[Dict]:
        """
        获取所有媒体库信息
        """
        libraries = []
        services = self.get_service_info()
        
        if not services:
            return libraries

        for service_name, service_info in services.items():
            try:
                service_libs = service_info.instance.get_libraries()
                if service_libs:
                    for lib in service_libs:
                        libraries.append({
                            "library_name": lib.name,
                            "library_type": lib.type,
                            "library_items": lib.items,
                            "server_name": service_name,
                            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    if self._debug:
                        logger.info(f"获取到 {service_name} 的 {len(service_libs)} 个媒体库")
            except Exception as e:
                logger.error(f"获取 {service_name} 媒体库信息出错: {str(e)}")

        self._last_update_time = datetime.now()
        return libraries

    def get_state(self) -> bool:
        return self._enabled

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
                                            'model': 'debug',
                                            'label': '调试日志'
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
                                            'model': 'notify',
                                            'label': '更新通知'
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
            "debug": False,
            "notify": False,
            "mediaservers": []
        }

    def get_page(self) -> List[dict]:
        """
        插件详情页面
        """
        if not self._enabled:
            return []

        try:
            libraries = self.get_libraries_info()
            
            if not libraries:
                return [{
                    'component': 'VAlert',
                    'props': {
                        'type': 'warning',
                        'variant': 'tonal',
                        'text': '未获取到媒体库信息，请检查配置'
                    }
                }]

            return [
                {
                    'component': 'VTable',
                    'props': {
                        'headers': [
                            {"text": "媒体库名称", "value": "library_name"},
                            {"text": "媒体库类型", "value": "library_type"},
                            {"text": "媒体数量", "value": "library_items"},
                            {"text": "媒体服务器", "value": "server_name"},
                            {"text": "更新时间", "value": "update_time"}
                        ],
                        'items': libraries
                    }
                }
            ]
        except Exception as e:
            logger.error(f"生成页面数据出错: {str(e)}")
            return [{
                'component': 'VAlert',
                'props': {
                    'type': 'error',
                    'variant': 'tonal',
                    'text': f'获取媒体库信息出错: {str(e)}'
                }
            }]

    @eventmanager.register(EventType.TransferComplete)
    def update(self, event: Event):
        """
        媒体库更新事件处理
        当有新的媒体入库时触发
        """
        if not self._enabled:
            return

        if self._debug:
            logger.info("检测到新媒体入库，正在更新媒体库信息")

        libraries = self.get_libraries_info()
        
        if self._notify and libraries:
            self.chain.post_message(Notification(
                mtype=NotificationType.MediaServer,
                title="媒体库信息已更新",
                text=f"共获取到 {len(libraries)} 个媒体库的信息"
            ))

    def stop_service(self):
        """
        退出插件
        """
        pass