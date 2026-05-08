# ErisPulse-BiliParser

B站视频解析模块，自动解析消息中的B站视频链接并展示详细信息。

## 功能

- 自动检测消息中的B站视频链接（支持 BV号、AV号、完整链接、b23.tv短链接）
- 手动 `/bili` 命令解析
- 输出封面图 + 视频详情（标题、UP主、播放量、弹幕、点赞、投币、收藏、分享）
- 热门评论展示
- 多平台富文本适配（HTML > Markdown > 纯文本自动回退）
- 解析结果缓存
- **直接下载视频**：消息中包含"看看/想看/播放/下载"等关键词 + 视频链接，直接发送视频文件
- **交互式下载**：解析视频信息后，30秒内回复"我要看这个"即可下载视频

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
enable_download = true      # 启用视频下载功能
download_cooldown = 60      # 下载冷却时间（秒）
max_file_size = 104857600   # 最大文件大小（字节，默认100MB）
```

## 使用

### 自动解析

发送包含B站链接的消息，模块自动解析并展示视频信息：

```
看看这个视频 https://www.bilibili.com/video/BV1xx411c7mD
```

### 直接下载视频

消息中同时包含**视频链接**和**观看关键词**（看看/想看/我要看/播放/下载等），直接发送视频文件，不显示解析信息：

```
看看这个视频 av170001
我想看 https://b23.tv/xxxxx
下载 BV1xx411c7mD
```

### 交互式下载

普通解析后会提示"想看这个视频吗？回复：`我要看这个`"，在60秒内回复即可触发下载。

### 手动命令

```
/bili BV1xx411c7mD
/bili av2
/bili https://b23.tv/xxxxx
/bili b23.tv/xxxxx
```

## 支持的链接格式

| 格式 | 示例 |
|------|------|
| BV号 | `BV1xx411c7mD` |
| AV号 | `av2` |
| 完整链接 | `https://www.bilibili.com/video/BV1xx411c7mD` |
| 短链接 | `https://b23.tv/xxxxx` |
| 无协议短链接 | `b23.tv/xxxxx` |

## 触发下载的关键词

`看看` `想看` `我要看` `我想看` `看这个` `看看这个` `看视频` `播放` `下载` `发视频` `发来` `watch` `play` `download` `video`
