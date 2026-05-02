import re
import time
from typing import Optional, Dict, List, Tuple

import aiohttp
from bilibili_api import video, comment

from ErisPulse import sdk
from ErisPulse.Core.Bases import BaseModule
from ErisPulse.Core.Event import command, message


_BILI_LINK_REGEX = re.compile(
    r'(?:https?://(?:www\.)?bilibili\.com/video/((?:BV[\w]+)|(?:av\d+))'
    r'|https?://b23\.tv/([\w]+)'
    r'|(?<!\w)((?:BV[\w]{6,12})|(?:av\d+))(?!\w))',
    re.IGNORECASE
)


def _format_count(n: int) -> str:
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.1f}万"
    return str(n)


def _format_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


class BiliTemplates:
    PRIMARY_COLOR = "#fb7299"
    PRIMARY_BG = "rgba(251, 114, 153, 0.05)"
    SECONDARY_COLOR = "#666"

    @classmethod
    def build_video_card(cls, info: dict, config: dict) -> Dict[str, str]:
        comments_text = info.get("_comments_text", "")

        html = cls._build_html(info, config, comments_text)
        markdown = cls._build_markdown(info, config, comments_text)
        text = cls._build_text(info, config, comments_text)

        return {"html": html, "markdown": markdown, "text": text}

    @classmethod
    def _build_html(cls, info: dict, config: dict, comments_text: str) -> str:
        stat = info.get("stat", {})
        owner = info.get("owner", {})
        bvid = info.get("bvid", "")

        stat_items = (
            f'<span style="margin-right: 12px;">播放 {_format_count(stat.get("view", 0))}</span>'
            f'<span style="margin-right: 12px;">弹幕 {_format_count(stat.get("danmaku", 0))}</span>'
            f'<span>点赞 {_format_count(stat.get("like", 0))}</span>'
        )

        interact_items = (
            f'<span style="margin-right: 12px;">投币 {_format_count(stat.get("coin", 0))}</span>'
            f'<span style="margin-right: 12px;">收藏 {_format_count(stat.get("favorite", 0))}</span>'
            f'<span>分享 {_format_count(stat.get("share", 0))}</span>'
        )

        duration_line = ""
        if info.get("duration") and info["duration"] != "0:00":
            duration_line = f'<div style="font-size: 12px; color: {cls.SECONDARY_COLOR}; margin-bottom: 4px;">时长: {info["duration"]}</div>'

        pages_line = ""
        if info.get("videos", 1) > 1:
            pages_line = f'<div style="font-size: 12px; color: {cls.SECONDARY_COLOR}; margin-bottom: 4px;">共 {info["videos"]} P</div>'

        tags_line = ""
        if info.get("tags"):
            tags_html = " ".join(
                f'<code style="font-size: 11px; background: rgba(0,0,0,0.04); padding: 1px 5px; border-radius: 3px;">{t}</code>'
                for t in info["tags"]
            )
            tags_line = f'<div style="font-size: 12px; margin-top: 6px;">{tags_html}</div>'

        desc_section = ""
        if config.get("show_description", False) and info.get("description"):
            max_len = config.get("max_desc_length", 100)
            desc = info["description"][:max_len]
            if len(info["description"]) > max_len:
                desc += "..."
            desc_section = (
                f'<details style="margin-top: 8px;">'
                f'<summary style="cursor: pointer; font-size: 12px; color: {cls.SECONDARY_COLOR};">简介</summary>'
                f'<div style="padding: 6px; font-size: 12px; color: {cls.SECONDARY_COLOR};">{desc}</div>'
                f'</details>'
            )

        comments_section = ""
        if comments_text:
            comments_section = (
                f'<div style="margin-top: 8px; border-top: 1px solid rgba(0,0,0,0.06); padding-top: 8px;">'
                f'<div style="font-size: 13px; font-weight: bold; color: {cls.PRIMARY_COLOR}; margin-bottom: 6px;">热门评论</div>'
                f'{comments_text}'
                f'</div>'
            )

        link_line = ""
        if bvid:
            link_line = (
                f'<div style="margin-top: 8px;">'
                f'<a href="https://www.bilibili.com/video/{bvid}" style="font-size: 12px; color: {cls.PRIMARY_COLOR};">https://www.bilibili.com/video/{bvid}</a>'
                f'</div>'
            )

        return (
            f'<div style="padding: 12px; border-radius: 8px;">'
            f'<div style="color: {cls.PRIMARY_COLOR}; font-size: 15px; font-weight: bold; margin-bottom: 8px;">{info["title"]}</div>'
            f'<div style="font-size: 13px; margin-bottom: 10px;">UP主: <span style="color: {cls.PRIMARY_COLOR}; font-weight: bold;">{owner.get("name", "未知")}</span></div>'
            f'<div style="padding: 8px; background: {cls.PRIMARY_BG}; border-radius: 6px; margin-bottom: 8px;">'
            f'<div style="font-size: 13px; margin-bottom: 4px;">{stat_items}</div>'
            f'<div style="font-size: 13px;">{interact_items}</div>'
            f'{duration_line}{pages_line}'
            f'{tags_line}'
            f'</div>'
            f'{desc_section}'
            f'{comments_section}'
            f'{link_line}'
            f'</div>'
        )

    @classmethod
    def _build_markdown(cls, info: dict, config: dict, comments_text: str) -> str:
        stat = info.get("stat", {})
        owner = info.get("owner", {})
        bvid = info.get("bvid", "")

        lines = [
            f'**{info["title"]}**',
            f'UP主: {owner.get("name", "未知")}',
            '',
            f'播放: {_format_count(stat.get("view", 0))} | '
            f'弹幕: {_format_count(stat.get("danmaku", 0))} | '
            f'点赞: {_format_count(stat.get("like", 0))}',
            f'投币: {_format_count(stat.get("coin", 0))} | '
            f'收藏: {_format_count(stat.get("favorite", 0))} | '
            f'分享: {_format_count(stat.get("share", 0))}',
        ]

        if info.get("duration") and info["duration"] != "0:00":
            lines.append(f'时长: {info["duration"]}')
        if info.get("videos", 1) > 1:
            lines.append(f'共 {info["videos"]} P')
        if info.get("tags"):
            lines.append(f'标签: {" | ".join(info["tags"])}')

        if config.get("show_description", False) and info.get("description"):
            max_len = config.get("max_desc_length", 100)
            desc = info["description"][:max_len]
            if len(info["description"]) > max_len:
                desc += "..."
            lines.extend(['', f'> {desc}'])

        if comments_text:
            lines.extend(['', '**热门评论**', comments_text])

        if bvid:
            lines.extend(['', f'[查看原视频](https://www.bilibili.com/video/{bvid})'])

        return '\n'.join(lines)

    @classmethod
    def _build_text(cls, info: dict, config: dict, comments_text: str) -> str:
        stat = info.get("stat", {})
        owner = info.get("owner", {})
        bvid = info.get("bvid", "")

        lines = [
            info["title"],
            f'UP主: {owner.get("name", "未知")}',
            '----------',
            f'播放: {_format_count(stat.get("view", 0))}  '
            f'弹幕: {_format_count(stat.get("danmaku", 0))}  '
            f'点赞: {_format_count(stat.get("like", 0))}',
            f'投币: {_format_count(stat.get("coin", 0))}  '
            f'收藏: {_format_count(stat.get("favorite", 0))}  '
            f'分享: {_format_count(stat.get("share", 0))}',
        ]

        if info.get("duration") and info["duration"] != "0:00":
            lines.append(f'时长: {info["duration"]}')
        if info.get("videos", 1) > 1:
            lines.append(f'共 {info["videos"]} P')
        if info.get("tags"):
            lines.append(f'标签: {" | ".join(info["tags"])}')

        if config.get("show_description", False) and info.get("description"):
            max_len = config.get("max_desc_length", 100)
            desc = info["description"][:max_len]
            if len(info["description"]) > max_len:
                desc += "..."
            lines.extend(['', desc])

        if comments_text:
            lines.extend(['', '── 热门评论 ──', comments_text])

        if bvid:
            lines.extend(['', f'https://www.bilibili.com/video/{bvid}'])

        return '\n'.join(lines)

    @classmethod
    def build_comments_html(cls, comments: list) -> str:
        items = []
        for i, c in enumerate(comments, 1):
            content = c["content"]
            if len(content) > 80:
                content = content[:80] + "..."
            like_text = f' <span style="color: {cls.SECONDARY_COLOR};">({_format_count(c["like"])})</span>' if c["like"] > 0 else ""
            items.append(
                f'<div style="margin-bottom: 4px; font-size: 12px;">'
                f'<span style="font-weight: bold;">{i}. {c["user"]}</span>: '
                f'{content}{like_text}'
                f'</div>'
            )
        return ''.join(items)

    @classmethod
    def build_comments_markdown(cls, comments: list) -> str:
        lines = []
        for i, c in enumerate(comments, 1):
            content = c["content"]
            if len(content) > 80:
                content = content[:80] + "..."
            like_text = f' ({_format_count(c["like"])})' if c["like"] > 0 else ""
            lines.append(f'{i}. **{c["user"]}**: {content}{like_text}')
        return '\n'.join(lines)

    @classmethod
    def build_comments_text(cls, comments: list) -> str:
        lines = []
        for i, c in enumerate(comments, 1):
            content = c["content"]
            if len(content) > 80:
                content = content[:80] + "..."
            like_text = f' ({_format_count(c["like"])})' if c["like"] > 0 else ""
            lines.append(f'{i}. {c["user"]}: {content}{like_text}')
        return '\n'.join(lines)


class BiliVideoParser:
    def __init__(self, logger, config: dict):
        self.logger = logger
        self.config = config
        self._cache: Dict[str, Tuple[dict, float]] = {}
        self._cache_ttl = config.get("cache_ttl", 600)

    async def resolve_short_url(self, short_code: str) -> Optional[str]:
        url = f"https://b23.tv/{short_code}"
        try:
            async with aiohttp.ClientSession(
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as session:
                async with session.get(url) as resp:
                    if resp.status in (301, 302):
                        redirect_url = resp.headers.get("Location", "")
                        match = re.search(
                            r'(?:BV[\w]+|av\d+)', redirect_url
                        )
                        if match:
                            return match.group(0)
            return None
        except Exception as e:
            self.logger.warning(f"解析短链接失败: {url} - {e}")
            return None

    def extract_ids(self, text: str) -> List:
        results = []
        seen = set()
        for match in _BILI_LINK_REGEX.finditer(text):
            bv_or_av = match.group(1) or match.group(3)
            short_code = match.group(2)
            if bv_or_av:
                if bv_or_av[:2].lower() == "bv":
                    key = "BV" + bv_or_av[2:]
                else:
                    key = bv_or_av
                if key not in seen:
                    seen.add(key)
                    results.append(key)
            elif short_code and short_code not in seen:
                seen.add(short_code)
                results.append(("short", short_code))
        return results

    def _get_cache(self, key: str) -> Optional[dict]:
        if key in self._cache:
            data, ts = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return data
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: dict):
        self._cache[key] = (data, time.time())
        now = time.time()
        expired = [k for k, (_, ts) in self._cache.items() if now - ts > self._cache_ttl]
        for k in expired:
            del self._cache[k]

    async def parse_video(self, video_id: str) -> Optional[dict]:
        cached = self._get_cache(video_id)
        if cached:
            return cached

        try:
            if video_id[:2].upper() == "BV":
                v = video.Video(bvid="BV" + video_id[2:])
            elif video_id.startswith("av"):
                v = video.Video(aid=int(video_id[2:]))
            else:
                return None

            info = await v.get_info()
            stat = info.get("stat", {})

            result = {
                "bvid": info.get("bvid", ""),
                "aid": info.get("aid", 0),
                "title": info.get("title", "未知标题"),
                "cover": info.get("pic", ""),
                "duration": _format_duration(info.get("duration", 0)),
                "description": info.get("desc", ""),
                "pubdate": info.get("pubdate", 0),
                "owner": {
                    "name": info.get("owner", {}).get("name", "未知UP主"),
                    "face": info.get("owner", {}).get("face", ""),
                    "mid": info.get("owner", {}).get("mid", 0),
                },
                "stat": {
                    "view": stat.get("view", 0),
                    "danmaku": stat.get("danmaku", 0),
                    "like": stat.get("like", 0),
                    "coin": stat.get("coin", 0),
                    "favorite": stat.get("favorite", 0),
                    "share": stat.get("share", 0),
                    "reply": stat.get("reply", 0),
                },
                "tid": info.get("tid", 0),
                "videos": info.get("videos", 1),
            }

            try:
                tag_result = await v.get_tags()
                if isinstance(tag_result, list):
                    result["tags"] = [t.get("tag_name", "") for t in tag_result[:5]]
                else:
                    result["tags"] = []
            except Exception:
                result["tags"] = []

            self._set_cache(video_id, result)
            return result

        except Exception as e:
            self.logger.error(f"解析视频 {video_id} 失败: {e}")
            return None

    async def get_hot_comments(
        self, aid: int, count: int = 3
    ) -> List[dict]:
        cache_key = f"comments_{aid}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached[:count]

        try:
            comments_data = await comment.get_comments(
                oid=aid,
                type_=comment.CommentResourceType.VIDEO,
                order=comment.OrderType.LIKE,
            )

            comments = []
            for c in comments_data.get("replies", []) or []:
                member = c.get("member", {})
                content = c.get("content", {})
                comments.append({
                    "user": member.get("uname", "匿名"),
                    "content": content.get("message", ""),
                    "like": c.get("like", 0),
                })
                if len(comments) >= 10:
                    break

            self._set_cache(cache_key, comments)
            return comments[:count]

        except Exception as e:
            self.logger.warning(f"获取视频 av{aid} 评论失败: {e}")
            return []


class Main(BaseModule):
    def __init__(self):
        self.sdk = sdk
        self.logger = sdk.logger.get_child("BiliParser")
        self.config = self._load_config()
        self.parser = BiliVideoParser(self.logger, self.config)

    @staticmethod
    def get_load_strategy():
        from ErisPulse.loaders import ModuleLoadStrategy
        return ModuleLoadStrategy(
            lazy_load=False,
            priority=0,
        )

    def _load_config(self) -> dict:
        config = sdk.config.getConfig("BiliParser")
        if not config:
            default_config = {
                "auto_parse": True,
                "show_cover": True,
                "show_comments": True,
                "comment_count": 3,
                "show_description": False,
                "max_desc_length": 100,
                "cache_ttl": 600,
                "max_videos_per_message": 3,
            }
            sdk.config.setConfig("BiliParser", default_config, immediate=True)
            self.logger.info("已创建默认配置")
            return default_config
        return config

    async def on_load(self, event):
        self._register_commands()

        if self.config.get("auto_parse", True):
            self._register_auto_parse()

        self.logger.info("BiliParser 模块已加载")

    async def on_unload(self, event):
        self.logger.info("BiliParser 模块已卸载")

    def _register_commands(self):
        @command("bili", help="解析B站视频链接")
        async def bili_cmd(event):
            args = event.get_command_args()
            if not args:
                await event.reply("用法: /bili <BV号/AV号/链接>")
                return

            text = " ".join(args)
            ids = self.parser.extract_ids(text)

            resolved_ids = await self._resolve_all_ids(ids)
            if not resolved_ids:
                await event.reply("未找到有效的B站视频链接")
                return

            await self._send_video_info(event, resolved_ids[0])

    def _register_auto_parse(self):
        @message.on_message(priority=50)
        async def auto_parse_handler(event):
            if event.is_command():
                return

            text = event.get_text()
            if not text:
                return

            ids = self.parser.extract_ids(text)
            if not ids:
                return

            resolved_ids = await self._resolve_all_ids(ids)
            max_count = self.config.get("max_videos_per_message", 3)

            for vid in resolved_ids[:max_count]:
                await self._send_video_info(event, vid)

    async def _resolve_all_ids(self, ids: list) -> List[str]:
        resolved = []
        for item in ids:
            if isinstance(item, tuple) and item[0] == "short":
                real_id = await self.parser.resolve_short_url(item[1])
                if real_id:
                    resolved.append(real_id)
            else:
                resolved.append(item)
        return resolved

    def _select_best_format(self, platform: str, templates: Dict[str, str]) -> tuple:
        try:
            supported_methods = sdk.adapter.list_sends(platform)
            if "Html" in supported_methods:
                return ("Html", templates["html"])
            elif "Markdown" in supported_methods:
                return ("Markdown", templates["markdown"])
            else:
                return ("Text", templates["text"])
        except Exception:
            return ("Text", templates["text"])

    async def _send_video_info(self, event, video_id: str):
        info = await self.parser.parse_video(video_id)
        if not info:
            return

        cover_url = info.get("cover", "")
        show_cover = self.config.get("show_cover", True)

        if show_cover and cover_url:
            try:
                await event.reply(cover_url, method="Image")
            except Exception as e:
                self.logger.debug(f"发送封面图失败: {e}")

        comments = []
        show_comments = self.config.get("show_comments", True)
        comment_count = self.config.get("comment_count", 3)

        if show_comments and info.get("aid"):
            comments = await self.parser.get_hot_comments(
                info["aid"], comment_count
            )

        comments_html = BiliTemplates.build_comments_html(comments) if comments else ""
        comments_md = BiliTemplates.build_comments_markdown(comments) if comments else ""
        comments_text = BiliTemplates.build_comments_text(comments) if comments else ""

        templates_set = {
            "html": BiliTemplates._build_html(info, self.config, comments_html),
            "markdown": BiliTemplates._build_markdown(info, self.config, comments_md),
            "text": BiliTemplates._build_text(info, self.config, comments_text),
        }

        platform = event.get_platform()
        fmt_name, content = self._select_best_format(platform, templates_set)

        try:
            await event.reply(content, method=fmt_name)
        except Exception:
            await event.reply(templates_set["text"])
