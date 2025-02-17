from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.core.meta import MetaBase
from app.plugins import _PluginBase
from app.log import logger
from app.schemas import NotificationType
from app.core.types import MediaType
from app.core.context import MediaInfo


class MediaLibInfo(_PluginBase):
    """
    媒体库信息插件
    获取并展示媒体库中的电影和电视剧信息
    """
    # 插件信息
    plugin_name = "媒体库信息"
    plugin_desc = "获取并展示媒体库中的电影和电视剧信息"
    plugin_version = "1.1"
    plugin_author = "heruntime01"
    # 作者主页
    author_url = "https://github.com/yheruntime01"
    # 插件配置项ID前缀
    plugin_config_prefix = "medialibinfo_"
    # 加载顺序
    plugin_order = 20
    # 可使用的用户级别
    auth_level = 1
    # 版本标识
    plugin_version_flag = "v2"

    # 私有属性
    _enabled = False
    _movie_path = None
    _tv_path = None
    _debug = False

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
            self._movie_path = config.get("movie_path")
            self._tv_path = config.get("tv_path")
            self._debug = config.get("debug")
            self.plugin_config.update(config)

        logger.info(f"媒体库信息插件启动，调试模式：{self._debug}")

    def get_state(self) -> bool:
        return self._enabled

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面
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
                                            'model': 'movie_path',
                                            'label': '电影目录',
                                            'placeholder': '电影媒体库目录'
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
                                            'model': 'tv_path',
                                            'label': '剧集目录',
                                            'placeholder': '电视剧媒体库目录'
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
                                            'text': '本插件用于获取并展示媒体库中的电影和电视剧信息。'
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
            "movie_path": "",
            "tv_path": ""
        }

    def get_page(self) -> List[dict]:
        """
        拼装插件详情页面
        """
        if not self._enabled:
            return [
                {
                    'component': 'VAlert',
                    'props': {
                        'type': 'warning',
                        'variant': 'tonal',
                        'text': '插件未启用'
                    }
                }
            ]

        try:
            # 获取媒体库信息
            movies = self.chain.list_media_files(self._movie_path, MediaType.MOVIE)
            tvs = self.chain.list_media_files(self._tv_path, MediaType.TV)

            if self._debug:
                logger.info(f"获取到电影：{len(movies)} 部")
                logger.info(f"获取到剧集：{len(tvs)} 部")

            # 构建展示内容
            contents = []
            
            # 电影信息
            if movies:
                contents.append({
                    'component': 'VDivider',
                    'props': {
                        'class': 'my-4'
                    }
                })
                contents.append({
                    'component': 'div',
                    'props': {
                        'class': 'text-h6 mb-4'
                    },
                    'text': f'电影 ({len(movies)})'
                })

                for movie in movies:
                    mediainfo: MediaInfo = self.chain.recognize_media(meta=movie, mtype=MediaType.MOVIE)
                    if mediainfo:
                        contents.append(self.__build_media_card(mediainfo))

            # 剧集信息
            if tvs:
                contents.append({
                    'component': 'VDivider',
                    'props': {
                        'class': 'my-4'
                    }
                })
                contents.append({
                    'component': 'div',
                    'props': {
                        'class': 'text-h6 mb-4'
                    },
                    'text': f'剧集 ({len(tvs)})'
                })

                for tv in tvs:
                    mediainfo: MediaInfo = self.chain.recognize_media(meta=tv, mtype=MediaType.TV)
                    if mediainfo:
                        contents.append(self.__build_media_card(mediainfo))

            return contents

        except Exception as e:
            logger.error(f"获取媒体库信息出错：{str(e)}")
            return [{
                'component': 'VAlert',
                'props': {
                    'type': 'error',
                    'variant': 'tonal',
                    'text': f'获取媒体库信息出错：{str(e)}'
                }
            }]

    def __build_media_card(self, mediainfo: MediaInfo) -> dict:
        """
        构建媒体信息卡片
        """
        return {
            'component': 'VCard',
            'props': {
                'class': 'mb-4'
            },
            'content': [
                {
                    'component': 'div',
                    'props': {
                        'class': 'd-flex'
                    },
                    'content': [
                        {
                            'component': 'VImg',
                            'props': {
                                'src': mediainfo.get_poster_image(),
                                'height': 150,
                                'width': 100,
                                'class': 'rounded-lg'
                            }
                        },
                        {
                            'component': 'VCardText',
                            'content': [
                                {
                                    'component': 'div',
                                    'props': {
                                        'class': 'text-h6'
                                    },
                                    'text': mediainfo.title
                                },
                                {
                                    'component': 'div',
                                    'props': {
                                        'class': 'text-subtitle-1'
                                    },
                                    'text': f"年份：{mediainfo.year}"
                                },
                                {
                                    'component': 'div',
                                    'text': f"评分：{mediainfo.vote_average}"
                                },
                                {
                                    'component': 'div',
                                    'text': mediainfo.overview[:200] + '...' if len(mediainfo.overview) > 200 else mediainfo.overview
                                }
                            ]
                        }
                    ]
                }
            ]
        }

    def get_command(self) -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        return []

    def stop_service(self):
        """
        退出插件
        """
        pass 