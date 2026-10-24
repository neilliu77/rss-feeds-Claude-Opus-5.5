# 我的全文 RSS 订阅源

这个仓库每 3 小时自动抓取下面 8 个网站的最新文章，生成**带全文、标题和缩略图**的 RSS，供 Inoreader 等阅读器订阅。
全部由 GitHub Actions 自动运行，不需要电脑开机，也不需要任何操作。

## 订阅地址

把下面的地址复制到 Inoreader 里订阅即可（每个地址订阅一次）。

| 名称 | 原网页 | RSS 订阅地址 |
|---|---|---|
| VALORANT · Dev News | [playvalorant.com](https://playvalorant.com/en-us/news/dev/) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/valorant-dev.xml` |
| League of Legends · Dev News | [leagueoflegends.com](https://www.leagueoflegends.com/en-gb/news/dev/) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/lol-dev.xml` |
| GameRes 游资网 · 策划 | [gameres.com](https://www.gameres.com/list/25) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/gameres-25.xml` |
| 虎嗅 · 走进游戏世界 | [huxiu.com](https://m.huxiu.com/collection/400.html) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/huxiu-collection-400.xml` |
| 澎湃新闻 · 游戏论 | [thepaper.cn](https://www.thepaper.cn/tag/1909025) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/thepaper-tag-1909025.xml` |
| 软件技术分享 (kmhgame) | [kmhgame.com](https://www.kmhgame.com/) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/kmhgame.xml` |
| James Clear · 3-2-1 | [jamesclear.com](https://jamesclear.com/3-2-1) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/jamesclear-3-2-1.xml` |
| 游民星空 · 游戏评测 | [gamersky.com](https://www.gamersky.com/review/) | `https://raw.githubusercontent.com/neilliu77/rss-feeds-Claude-Opus-5.5/main/feeds/gamersky-review.xml` |

## 在 Inoreader 里订阅

1. 打开 Inoreader，点左上角的 **+**（或侧边栏的 **Add new / 添加** → **Feed / 订阅源**）。
2. 把上表中的一个 RSS 地址粘贴进搜索框，按回车。
3. 在出现的结果里点蓝色的 **Follow / 关注**（可以顺便放进一个文件夹，比如“游戏”）。
4. 每个地址重复一次。
5. 想看到小缩略图：在文章列表上方的视图按钮里选择 **Magazine（杂志视图）**。

## 常见问题

**多久更新一次？** 每 3 小时自动运行一次（GitHub 的定时任务有时会晚几分钟到几十分钟）。Inoreader 免费版也会定期来取，一般当天就能看到新文章。

**想马上更新一次？** 打开仓库页面上方的 **Actions** → 左边选 **Update RSS feeds** → 右边点 **Run workflow** → 再点绿色的 **Run workflow**。

**怎么知道是否正常？** 打开 [`feeds/status.json`](feeds/status.json)，每个源的 `"ok": true` 且 `"error": null` 就说明正常；`newest` 是最新一篇文章的时间。

**图片为什么来自 wsrv.nl？** 游资网、虎嗅、澎湃、游民星空和微信公众号的图片禁止在别的网站里直接显示（防盗链），所以这几个源的图片通过公共图片缓存 wsrv.nl 转一下，保证在 Inoreader 里能正常显示。

**仓库里的文件是做什么的？**
- `rssgen/`：抓取和生成 RSS 的程序（每个网站一个文件，在 `rssgen/sources/` 里）
- `feeds/`：生成好的 RSS 文件（就是你订阅的那些）
- `cache/`：已经抓过的文章，避免重复抓取
- `.github/workflows/update-feeds.yml`：定时任务的设置

> GitHub 会暂停 60 天没有任何动静的仓库里的定时任务。这个仓库每次有新文章都会自动提交，任务里也带了“保持启用”的步骤，正常情况下不会被暂停。如果哪天收到 GitHub 的相关邮件，进入 **Actions** 页面点 **Enable workflow** 即可。
