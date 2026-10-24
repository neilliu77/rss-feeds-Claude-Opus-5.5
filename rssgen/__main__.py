"""Entry point: python -m rssgen [feed-id ...]"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time

from .feed import Cache, Item, build_rss
from .htmlclean import text_of
from .net import Http
from .sources import ALL_SOURCES
from .sources.base import Article
from .util import iso, now_utc

log = logging.getLogger("rssgen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_FAILURES_BEFORE_PARTIAL = 3


def feed_base_url() -> str:
    base = os.environ.get("FEED_BASE_URL")
    if base:
        return base.rstrip("/") + "/"
    repo = os.environ.get("GITHUB_REPOSITORY", "neilliu77/rss-feeds-Claude-Opus-5.5")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/"


def write_feed(src, cache: Cache) -> None:
    os.makedirs(os.path.join(ROOT, "feeds"), exist_ok=True)
    xml = build_rss(title=src.title, link=src.home, description=src.description, language=src.language,
                    self_url=feed_base_url() + f"feeds/{src.id}.xml", items=cache.sorted_items(),
                    image=src.icon)
    path = os.path.join(ROOT, "feeds", f"{src.id}.xml")
    old = open(path, "rb").read() if os.path.exists(path) else None
    if old != xml:
        with open(path, "wb") as f:
            f.write(xml)


def run_source(src, http: Http) -> dict:
    t0 = time.time()
    cache = Cache(os.path.join(ROOT, "cache", f"{src.id}.json"))
    status = {"id": src.id, "title": src.title, "ok": False, "error": None}
    log.info("== %s (%s)", src.id, src.title)
    try:
        entries = src.fetch_list(http)
        if not entries:
            raise RuntimeError("no articles found on the list page")
    except Exception as e:  # noqa
        log.exception("   list failed for %s", src.id)
        status["error"] = f"list: {type(e).__name__}: {str(e)[:160]}"
        write_feed(src, cache)
        status.update(items=len(cache.items), newest=_newest(cache))
        return status

    seen, unique = set(), []
    for e in entries:
        if e.link and e.link not in seen:
            seen.add(e.link)
            unique.append(e)
    entries = unique[: src.list_limit]
    log.info("   %d entries on list page", len(entries))

    now = iso(now_utc())
    added, errors, needed = 0, 0, 0
    for e in entries:
        old = cache.items.get(e.link)
        if old and not old.partial:
            continue
        needed += 1
        try:
            art = src.fetch_article(http, e)
            content, thumb = src.build_content(e, art)
            if len(text_of(content)) < 20 and "<img" not in content and "<iframe" not in content:
                raise RuntimeError("article body came back empty")
            title = (art.title or e.title or "").strip() or e.link
            cache.items[e.link] = Item(
                link=e.link, title=title, content=content,
                date=iso(art.date or e.date), first_seen=old.first_seen if old else now,
                author=(art.author or e.author or "").strip(), thumb=thumb,
                categories=art.categories or [])
            cache.failures.pop(e.link, None)
            added += 1
            log.info("   + %s", title[:80])
        except Exception as ex:  # noqa
            errors += 1
            prev = cache.failures.get(e.link)
            n = (prev.get("n", 0) if isinstance(prev, dict) else int(prev or 0)) + 1
            reason = f"{type(ex).__name__}: {str(ex)[:150]}"
            cache.failures[e.link] = {"n": n, "error": reason}
            log.warning("   ! article failed (%d): %s -> %s", n, e.link, reason)
            if not old and n >= MAX_FAILURES_BEFORE_PARTIAL and e.title:
                content, thumb = src.build_content(e, Article(content=src.partial_content(e)))
                cache.items[e.link] = Item(link=e.link, title=e.title, content=content, date=iso(e.date),
                                           first_seen=now, author=e.author, thumb=thumb, partial=True)
    current = {e.link for e in entries}
    cache.failures = {k: v for k, v in cache.failures.items() if k in current}
    cache.prune(src.keep)
    cache.save()
    write_feed(src, cache)
    status.update(ok=True, items=len(cache.items), newest=_newest(cache))
    if needed and not added:
        status["error"] = f"all {errors} new article(s) failed"
    log.info("   done: %d new, %d failed, %d in feed (%.1fs)", added, errors, len(cache.items), time.time() - t0)
    return status


def _newest(cache: Cache):
    items = cache.sorted_items()
    return (items[0].date or items[0].first_seen) if items else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate full-text RSS feeds")
    ap.add_argument("ids", nargs="*", help="feed ids to update (default: all)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    for noisy in ("urllib3", "charset_normalizer", "readability"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    selected = [s for s in ALL_SOURCES if not args.ids or s.id in args.ids]
    if not selected:
        print("unknown feed id; available:", ", ".join(s.id for s in ALL_SOURCES))
        return 2
    http = Http()
    statuses = [run_source(src, http) for src in selected]

    # status file (only stable fields, so unchanged runs produce no git diff)
    status_path = os.path.join(ROOT, "feeds", "status.json")
    previous = {}
    if os.path.exists(status_path):
        try:
            previous = {s["id"]: s for s in json.load(open(status_path, encoding="utf-8"))}
        except Exception:  # noqa
            previous = {}
    for s in statuses:
        previous[s["id"]] = s
    ordered = [previous[s.id] for s in ALL_SOURCES if s.id in previous]
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=1)
        f.write("\n")

    print("\nSummary:")
    for s in statuses:
        print(f"  {'OK ' if s['ok'] and not s['error'] else 'ERR'} {s['id']:<22} items={s.get('items')} "
              f"newest={s.get('newest')} {s['error'] or ''}")
    return 0 if any(s["ok"] for s in statuses) else 1


if __name__ == "__main__":
    sys.exit(main())
