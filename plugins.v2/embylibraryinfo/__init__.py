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