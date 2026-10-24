"""The list of feeds this repository builds. Feed files are written to feeds/<id>.xml."""
from .gameres import GameResList
from .gamersky import GamerskyReviews
from .huxiu import HuxiuCollection
from .jamesclear import JamesClear321
from .riot import RiotNews
from .thepaper import ThePaperTag
from .wordpress import WordPressSite

ALL_SOURCES = [
    RiotNews("valorant-dev", "VALORANT · Dev News", "https://playvalorant.com/en-us/news/dev/",
             "Developer updates and dev diaries from the VALORANT team.",
             icon="https://playvalorant.com/favicon.ico"),
    RiotNews("lol-dev", "League of Legends · Dev News", "https://www.leagueoflegends.com/en-gb/news/dev/",
             "/dev blogs and developer updates from the League of Legends team.",
             icon="https://www.leagueoflegends.com/favicon.ico", accept_language="en-GB,en;q=0.9"),
    GameResList("gameres-25", "25", "GameRes 游资网 · 策划", "GameRes 游资网「策划」栏目（含站外微信文章）全文"),
    HuxiuCollection("huxiu-collection-400", "400", "虎嗅 · 走进游戏世界", "虎嗅合集「走进游戏世界」全文"),
    ThePaperTag("thepaper-tag-1909025", "1909025", "澎湃新闻 · 游戏论", "澎湃新闻·思想市场「游戏论」专栏全文"),
    WordPressSite("kmhgame", "https://www.kmhgame.com/", "软件技术分享 (kmhgame)", "关于电子游戏的方方面面"),
    JamesClear321(),
    GamerskyReviews(),
]
