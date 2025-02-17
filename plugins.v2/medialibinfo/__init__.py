from typing import Any, Dict, List
from app.core.config import settings
from app.plugins import _PluginBase
from app.log import logger
from app.schemas.types import EventType
from app.helper.service import ServiceBaseHelper
from app.db.systemconfig_oper import SystemConfigOper
from app.schemas import MediaServerConf


class MediaInfo(_PluginBase):
    plugin_name = "媒体信息"
    plugin_desc = "获取媒体库中的电视剧名称、电影名称等信息。"
    plugin_version = "1.1"
    plugin_author = "heruntime01"
    plugin_config_prefix = "mediainfo_"
    plugin_order = 20
    auth_level = 1
    plugin_version_flag = "v2"

    _enabled: bool = False
    _media_server_helper: ServiceBaseHelper[MediaServerConf]

    def init_plugin(self, config: Dict[str, Any] = None) -> None:
        if not hasattr(settings, 'VERSION_FLAG') or settings.VERSION_FLAG != "v2":
            return

        # 初始化配置
        if config:
            self._enabled = config.get("enabled", False)

        # 初始化媒体服务器帮助类
        self._media_server_helper = ServiceBaseHelper(
            config_key=SystemConfigKey.MediaServers,
            conf_type=MediaServerConf,
            module_type=ModuleType.MediaServer
        )

        logger.info(f"媒体信息服务启动")

    @eventmanager.register(EventType.MediaRecognizeConvert)
    def get_media_info(self, event):
        if not self._enabled:
            return

        mediaid = event.event_data.get("mediaid")
        convert_type = event.event_data.get("convert_type")

        if not mediaid or not convert_type:
            logger.error("缺少必要的参数：mediaid 或 convert_type")
            return

        try:
            # 解析 mediaid
            mediaid_parts = mediaid.split(":")
            if len(mediaid_parts) != 2:
                raise ValueError("无效的 mediaid 格式")

            media_source, media_id = mediaid_parts

            # 获取媒体服务器实例
            media_server = self._get_media_server(media_source)
            if not media_server:
                logger.error(f"未找到对应的媒体服务器：{media_source}")
                return

            # 调用媒体服务器API获取详细信息
            media_details = media_server.get_media_detail(media_id)
            if not media_details:
                logger.error(f"无法获取媒体详情：{mediaid}")
                return

            # 发送结果
            self._send_media_info_result(media_details)

        except Exception as e:
            logger.error(f"处理媒体信息时出错: {str(e)}")

    def _get_media_server(self, media_source: str) -> Optional[Any]:
        """
        获取指定类型的媒体服务器实例
        :param media_source: 媒体源类型（如 'plex', 'emby', 'jellyfin'）
        :return: 对应的媒体服务器实例
        """
        service_info = self._media_server_helper.get_service(name=media_source)
        if service_info and service_info.instance:
            return service_info.instance
        return None

    def _send_media_info_result(self, media_details: Dict[str, Any]):
        """
        发送媒体信息结果事件
        :param media_details: 媒体详情字典
        """
        eventmanager.send_event(
            EventType.MediaRecognizeConvert,
            {"media_dict": media_details}
        )