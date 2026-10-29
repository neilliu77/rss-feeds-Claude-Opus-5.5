# 我的全文 RSS 订阅源

这个仓库自动抓取下面 7 个网站的最新文章，生成**带全文、标题和缩略图**的 RSS，在 Inoreader 里直接阅读全文。
全部由 GitHub Actions 自动运行，不需要电脑开机，也不需要任何操作。

## 订阅地址

| 名称 | 原网页 | RSS 订阅地址 |
|---|---|---|
| VALORANT · Dev News | [playvalorant.com](https://playvalorant.com/en-us/news/dev/) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/valorant-dev.xml` |
| League of Legends · Dev News | [leagueoflegends.com](https://www.leagueoflegends.com/en-gb/news/dev/) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/lol-dev.xml` |
| GameRes 游资网 · 策划 | [gameres.com](https://www.gameres.com/list/25) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/gameres-25.xml` |
| 澎湃新闻 · 游戏论 | [thepaper.cn](https://www.thepaper.cn/tag/1909025) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/thepaper-tag-1909025.xml` |
| 软件技术分享 (kmhgame) | [kmhgame.com](https://www.kmhgame.com/) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/kmhgame.xml` |
| James Clear · 3-2-1 | [jamesclear.com](https://jamesclear.com/3-2-1) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/jamesclear-3-2-1.xml` |
| 游民星空 · 游戏评测 | [gamersky.com](https://www.gamersky.com/review/) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/gamersky-review.xml` |

每个源最多保留最近 30 篇文章。几点说明：
- **VALORANT / 英雄联盟**：官方开发者栏目，很多条目是 YouTube 视频，RSS 里会直接放视频播放器和简介。
- **游资网 · 策划**：栏目里有不少转载的微信公众号文章，全文直接从微信原文抓取。
- **澎湃新闻 · 游戏论**：更新很慢，通常一个月一两篇。
- **kmhgame**：作者有时会提前写好日期、过几天才发布，所以新出现的文章日期可能比实际出现时间早。
- **James Clear · 3-2-1**：每周四一期。
- **游民星空 · 游戏评测**：用的是“全部评测”栏目，包括评测和试玩报告；评测文章开头会显示游民评分。

## 在 Inoreader 里订阅 / 取消订阅

1. 打开 Inoreader，点左上角的 **+**（或侧边栏的 **Add new / 添加** → **Feed / 订阅源**）。
2. 把上表中的一个 RSS 地址粘贴进搜索框，按回车。
3. 点蓝色的 **Follow / 关注**（可以顺便放进一个文件夹，比如“游戏”）。每个地址订阅一次。
4. 想看到小缩略图：在文章列表上方的视图按钮里选 **Magazine（杂志视图）**。
5. 不想要某个源了：在左边栏的这个源上点右键（手机上长按），选 **Unsubscribe / 取消订阅**。

## 新文章多久能出现在 Inoreader 里？

1. **检查网站**：定时任务计划每小时运行一次。但 GitHub 免费版的定时任务在它繁忙时会推迟或跳过，实际大约每天运行 4–6 次，间隔 3–8 小时不等。
2. **推送给 Inoreader**：发现新文章并保存后，程序会通过 WebSub 推送服务（Google 的公共推送中心）通知 Inoreader。为了等 GitHub 的文件缓存刷新，推送在保存后约 5–10 分钟发出。
3. **Inoreader 显示**：收到推送就把新文章加进来，不用等它自己来取。就算推送没成功，Inoreader 也会自己定时来取（订阅人少的源，最多每小时一次，有时间隔更久）。

所以网站发布的新文章，一般当天几个小时内就会出现在 Inoreader 里。

## 怎么确认一切正常？

- **仓库页面上的 “Updated X ago”**：每次自动检查都会记下检查时间，所以这里显示的就是最近一次检查。超过一天没变，说明定时任务可能停了，去 **Actions** 页面看看。
- **[`feeds/status.json`](feeds/status.json)**：每个源 `"ok": true` 且 `"error": null` 就说明正常。`newest` 是最新一篇文章的时间，`checked_at` 是最近一次检查的时间（世界标准时间 UTC，纽约夏令时要减 4 小时，冬令时减 5 小时）。
- **想马上更新一次**：仓库页面上方 **Actions** → 左边选 **Update RSS feeds** → 右边 **Run workflow** → 绿色的 **Run workflow**。

## 图片和动图

- 游资网、澎湃、游民星空和微信公众号的图片禁止在别的网站里直接显示（防盗链），所以这几个源的图片通过公共图片服务 wsrv.nl 中转，保证在 Inoreader 里能正常显示。
- 动图保持 GIF 格式，任何阅读器都能播放。游民星空用的是原版动图，不是网页上点击前显示的静止预览图。
- 个别特别大的动图如果中转服务处理不了，会自动显示成一张静止图片，而不会变成裂图。

## 仓库里的文件

```
.github/workflows/update-feeds.yml   定时任务：检查网站 → 保存 → 推送给 Inoreader
rssgen/                              抓取和生成 RSS 的程序
  sources/                           每个网站一个文件；网站列表在 sources/__init__.py
  websub.py                          有新文章时通知 Inoreader 的推送程序
feeds/                               生成好的 RSS 文件（就是你订阅的那些）和 status.json
cache/                               已经抓过的文章，避免重复抓取
requirements.txt                     程序需要的 Python 组件
```

> GitHub 会暂停 60 天没有任何动静的仓库里的定时任务。这个仓库每次检查都会自动提交，任务里也带了“保持启用”的步骤，正常情况下不会被暂停。如果哪天收到 GitHub 的相关邮件，进入 **Actions** 页面点 **Enable workflow** 即可。
