import json
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Any, List, Dict, Tuple

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.event import eventmanager, Event
from app.helper.mediaserver import MediaServerHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType
from app.utils.http import RequestUtils

lock = threading.Lock()


class EmbyLibraryInfo(_PluginBase):
    # 插件名称
    plugin_name = "Emby媒体库信息获取"
    # 插件描述
    plugin_desc = "获取Emby媒体库的基本信息并输出。"
    # 插件图标
    plugin_icon = "Element_A.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "thsrite"
    # 作者主页
    author_url = "https://github.com/thsrite"
    # 插件配置项ID前缀
    plugin_config_prefix = "embylibraryinfo_"
    # 加载顺序
    plugin_order = 15
    # 可使用的用户级别
    auth_level = 1
    # 版本标识
    plugin_version_flag = "v2"

    # ... 其他代码保持不变 ... 

    # 私有属性
    _enabled = False
    _onlyonce = False
    _cron = None
    _library_id = None
    _mediaservers = None

    mediaserver_helper = None
    _EMBY_HOST = None
    _EMBY_USER = None
    _EMBY_APIKEY = None
    _scheduler: Optional[BackgroundScheduler] = None

    def init_plugin(self, config: dict = None):
        # 停止现有任务
        self.stop_service()
        self.mediaserver_helper = MediaServerHelper()

        if config:
            self._enabled = config.get("enabled")
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")
            self._library_id = config.get("library_id")
            self._mediaservers = config.get("mediaservers") or []

            # 加载模块
            if self._enabled or self._onlyonce:
                # 定时服务
                self._scheduler = BackgroundScheduler(timezone=settings.TZ)

                # 立即运行一次
                if self._onlyonce:
                    logger.info(f"Emby媒体库信息获取服务启动，立即运行一次")
                    self._scheduler.add_job(self.get_library_info, 'date',
                                            run_date=datetime.now(
                                                tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                                            name="Emby媒体库信息获取")

                    # 关闭一次性开关
                    self._onlyonce = False

                    # 保存配置
                    self.__update_config()
                # 周期运行
                if self._cron:
                    try:
                        self._scheduler.add_job(func=self.get_library_info,
                                                trigger=CronTrigger.from_crontab(self._cron),
                                                name="Emby媒体库信息获取")
                    except Exception as err:
                        logger.error(f"定时任务配置错误：{str(err)}")
                        # 推送实时消息
                        self.systemmessage.put(f"执行周期配置错误：{err}")

                # 启动任务
                if self._scheduler.get_jobs():
                    self._scheduler.print_jobs()
                    self._scheduler.start()

    def get_state(self) -> bool:
        return self._enabled

    def __update_config(self):
        self.update_config(
            {
                "onlyonce": self._onlyonce,
                "cron": self._cron,
                "enabled": self._enabled,
                "library_id": self._library_id,
                "mediaservers": self._mediaservers,
            }
        )

    def get_library_info(self):
        """
        获取Emby媒体库信息
        """
        if not self._library_id:
            logger.error("未配置媒体库ID")
            return

        emby_servers = self.mediaserver_helper.get_services(name_filters=self._mediaservers, type_filter="emby")
        if not emby_servers:
            logger.error("未配置Emby媒体服务器")
            return

        for emby_name, emby_server in emby_servers.items():
            logger.info(f"开始处理媒体服务器 {emby_name}")
            self._EMBY_USER = emby_server.instance.get_user()
            self._EMBY_APIKEY = emby_server.config.config.get("apikey")
            self._EMBY_HOST = emby_server.config.config.get("host")
            if not self._EMBY_HOST.endswith("/"):
                self._EMBY_HOST += "/"
            if not self._EMBY_HOST.startswith("http"):
                self._EMBY_HOST = "http://" + self._EMBY_HOST

            # 获取媒体库信息
            library_info = self.__get_library_info(self._library_id)
            if library_info:
                logger.info(f"媒体库信息: {library_info}")
            else:
                logger.error(f"未能获取媒体库信息")

    def __get_library_info(self, library_id):
        """
        获取指定媒体库的信息
        """
        res = RequestUtils().get_res(
            f"{self._EMBY_HOST}/emby/Users/{self._EMBY_USER}/Items?ParentId={library_id}&api_key={self._EMBY_APIKEY}")
        if res and res.status_code == 200:
            results = res.json().get("Items") or []
            library_info = {
                "LibraryID": library_id,
                "ItemCount": len(results),
                "Items": [{"Name": item.get("Name"), "Type": item.get("Type"), "Id": item.get("Id")} for item in results]
            }
            return library_info
        return None

    @eventmanager.register(EventType.PluginAction)
    def remote_sync(self, event: Event):
        """
        远程获取媒体库信息
        """
        if event:
            event_data = event.event_data
            if not event_data or event_data.get("action") != "get_library_info":
                return
            self.post_message(channel=event.event_data.get("channel"),
                              title="开始获取Emby媒体库信息 ...",
                              userid=event.event_data.get("user"))
        self.get_library_info()
        if event:
            self.post_message(channel=event.event_data.get("channel"),
                              title="获取Emby媒体库信息完成！", userid=event.event_data.get("user"))

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return [ {
            "cmd": "/get_library_info",
            "event": EventType.PluginAction,
            "desc": "获取Emby媒体库信息",
            "category": "",
            "data": {
                "action": "get_library_info"
            }
        } ]

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return [
            {
                "component": "VForm",
                "content": [
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
                                            'label': '启用插件',
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
                                            'model': 'onlyonce',
                                            'label': '立即运行一次',
                                        }
                                    }
                                ]
                            },
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VCronField',
                                        'props': {
                                            'model': 'cron',
                                            'label': '执行周期',
                                            'placeholder': '5位cron表达式，留空自动'
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
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'library_id',
                                            'label': '媒体库ID'
                                        }
                                    }
                                ]
                            },
                        ],
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
                                                      for config in self.mediaserver_helper.get_configs().values() if
                                                      config.type == "emby"]
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
                                            'text': '获取Emby媒体库的基本信息并输出。'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ],
            }
        ], {
            "enabled": False,
            "onlyonce": False,
            "cron": "5 1 * * *",
            "library_id": "",
            "mediaservers": [],
        }

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        """
        退出插件
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            logger.error("退出插件失败：%s" % str(e))