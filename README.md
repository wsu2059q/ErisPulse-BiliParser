# ErisPulse-BiliParser

B站视频解析模块，自动解析消息中的B站视频链接并展示详细信息。

## 功能

- 自动检测消息中的B站视频链接（支持 BV号、AV号、完整链接、b23.tv短链接）
- 手动 `/bili` 命令解析
- 输出封面图 + 视频详情（标题、UP主、播放量、弹幕、点赞、投币、收藏、分享）
- 热门评论展示
- 多平台富文本适配（HTML > Markdown > 纯文本自动回退）
- 解析结果缓存

## 安装

```bash
epsdk install BiliParser
```

## 配置

在 `config.toml` 中添加：

```toml
[BiliParser]
auto_parse = true           # 自动解析消息中的B站链接
show_cover = true           # 发送封面图
show_comments = true        # 显示热门评论
comment_count = 3           # 显示评论数量
show_description = false    # 显示视频简介
max_desc_length = 100       # 简介最大长度
cache_ttl = 600             # 缓存过期时间（秒）
max_videos_per_message = 3  # 单条消息最多解析视频数
```

## 使用

### 自动解析

在群聊或私聊中发送包含B站链接的消息，模块会自动解析：

```
看看这个视频 https://www.bilibili.com/video/BV1xx411c7mD
```

### 手动命令

```
/bili BV1xx411c7mD
/bili av2
/bili https://b23.tv/xxxxx
```

## 支持的链接格式

| 格式 | 示例 |
|------|------|
| BV号 | `BV1xx411c7mD` |
| AV号 | `av2` |
| 完整链接 | `https://www.bilibili.com/video/BV1xx411c7mD` |
| 短链接 | `https://b23.tv/xxxxx` |
