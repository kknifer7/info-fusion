#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import warnings
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable
from urllib.parse import urljoin

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import requests
from bs4 import BeautifulSoup


MEDIA_URL = "https://www.163.com/dy/media/T1603594732083.html"
API_URL = "http://127.0.0.1:3000/news"
CRAWL_RESULT_API_URL = "http://127.0.0.1:3000/crawl-result"
CRAWLER_ID = 1
DEFAULT_TIMEZONE = "Asia/Shanghai"
EXCLUDED_LINE_PREFIXES = (
    "365资讯简报，",
    "365资讯简报,",
    "【微语】",
    "本文标签：",
    "本文标签:",
)
_DATE_HEADER_RE = re.compile(r"^\d{4}年\d{1,2}月\d{1,2}日\s+星期[一二三四五六日]")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}


@dataclass
class MediaItem:
    title: str
    url: str
    publish_time: str


@dataclass
class Article:
    title: str
    url: str
    publish_time: str
    target_date: str
    content: str
    lines: list[str]


def fetch_html(url: str, timeout: int = 20) -> str:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def today_in_timezone(tz_name: str) -> date:
    try:
        from zoneinfo import ZoneInfo
    except ImportError as exc:
        raise RuntimeError("Python 3.9+ is required for zoneinfo timezone support.") from exc
    return datetime.now(ZoneInfo(tz_name)).date()


def clean_lines(lines: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        value = re.sub(r"\s+", " ", line).strip()
        if value:
            cleaned.append(value)
    return cleaned


def filter_article_lines(lines: Iterable[str]) -> list[str]:
    return [
        line
        for line in lines
        if not line.startswith(EXCLUDED_LINE_PREFIXES)
        and not _DATE_HEADER_RE.match(line)
    ]


def extract_time(text: str, with_seconds: bool = False) -> str:
    pattern = r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}" if with_seconds else r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}"
    match = re.search(pattern, text)
    return match.group(0) if match else ""


def parse_media_items(html: str, base_url: str = MEDIA_URL) -> list[MediaItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[MediaItem] = []
    seen_urls: set[str] = set()

    selectors = ["li.js-item.item", "li.item", ".js-item.item"]
    nodes = []
    for selector in selectors:
        nodes = soup.select(selector)
        if nodes:
            break

    if not nodes:
        nodes = soup.select("a[href*='/dy/article/']")

    for node in nodes:
        link = None
        if getattr(node, "name", None) == "a":
            link = node
            container = node.parent
        else:
            link = node.select_one("a.title[href*='/dy/article/']") or node.select_one("a[href*='/dy/article/']")
            container = node
        if not link or not link.get("href"):
            continue

        url = urljoin(base_url, link["href"])
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title = link.get_text(" ", strip=True) or link.get("title", "").strip()
        if not title:
            img = link.select_one("img[alt]")
            title = img["alt"].strip() if img else ""

        text = container.get_text("\n", strip=True) if container else link.get_text("\n", strip=True)
        publish_time = extract_time(text)
        items.append(MediaItem(title=title, url=url, publish_time=publish_time))

    return items


def parse_article(html: str, url: str, target: date) -> Article:
    soup = BeautifulSoup(html, "html.parser")

    title_node = soup.select_one("h1.post_title") or soup.select_one("h1")
    title = title_node.get_text(" ", strip=True) if title_node else ""

    info_node = soup.select_one(".post_info")
    publish_time = extract_time(info_node.get_text(" ", strip=True), with_seconds=True) if info_node else ""

    body = soup.select_one(".post_body")
    if not body:
        body = soup.select_one("#content")
    if not body:
        raise ValueError("Could not find article body: expected .post_body or #content")

    for removable in body.select("script, style, iframe, video, .post_top, .post_statement"):
        removable.decompose()

    lines = filter_article_lines(clean_lines(body.get_text("\n", strip=True).splitlines()))
    content = "\n".join(lines)
    if not content:
        raise ValueError("Article body was found but no text content was extracted.")

    return Article(
        title=title,
        url=url,
        publish_time=publish_time,
        target_date=target.isoformat(),
        content=content,
        lines=lines,
    )


def find_item_for_date(items: list[MediaItem], target: date) -> MediaItem:
    target_prefix = target.isoformat()
    for item in items:
        if item.publish_time.startswith(target_prefix):
            return item

    if items:
        latest = items[0]
        latest_date = latest.publish_time[:10] if latest.publish_time else "unknown"
        raise ValueError(
            f"No article for {target_prefix}. Latest listed article is {latest_date}: {latest.title}"
        )
    raise ValueError("No article items were found on the media page.")


def report_crawl_result(success: bool, message: str) -> None:
    try:
        payload = {
            "successFlag": success,
            "crawlerId": CRAWLER_ID,
            "message": message,
        }
        response = requests.post(CRAWL_RESULT_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        print(f"Crawl result reported: {response.status_code}")
    except Exception as exc:
        print(f"Failed to report crawl result: {exc}", file=sys.stderr)


def main() -> int:
    success = False
    message = ""

    try:
        target = today_in_timezone(DEFAULT_TIMEZONE)

        media_html = fetch_html(MEDIA_URL)
        items = parse_media_items(media_html, base_url=MEDIA_URL)
        item = find_item_for_date(items, target)
        article_html = fetch_html(item.url)
        article = parse_article(article_html, item.url, target)

        if not article.publish_time:
            article.publish_time = item.publish_time

        if not article.lines:
            raise ValueError("Article was found but no lines were extracted.")

        _line_prefix_re = re.compile(r"^\d+\.\s*")
        ok_count = 0
        fail_count = 0
        for raw_line in article.lines:
            line = _line_prefix_re.sub("", raw_line).strip()
            if not line:
                continue
            article_data = {
                "title": line,
                "content": line,
                "sourceUrl": article.url,
                "publishDateTime": article.publish_time,
                "remark": "网易号-每天一分钟知晓天下事",
            }
            try:
                response = requests.post(API_URL, json=article_data, timeout=30)
                response.raise_for_status()
                ok_count += 1
                print(f"[OK] {line}")
            except Exception as exc:
                fail_count += 1
                print(f"[FAIL] {line} | {exc}", file=sys.stderr)

        message = (
            f"[Crawl OK] title={article.title} | "
            f"sourceUrl={article.url} | "
            f"publishDateTime={article.publish_time} | "
            f"submitted={ok_count} failed={fail_count}"
        )
        success = fail_count == 0
    except Exception as exc:
        message = f"[Crawl Failed] {exc}"
        print(f"ERROR: {exc}", file=sys.stderr)

    report_crawl_result(success, message)
    return 0 if success else 1


def test_print() -> None:
    """测试模式：抓取并打印最终数据，不提交 API。"""
    target = today_in_timezone(DEFAULT_TIMEZONE)
    media_html = fetch_html(MEDIA_URL)
    items = parse_media_items(media_html, base_url=MEDIA_URL)
    item = find_item_for_date(items, target)
    article_html = fetch_html(item.url)
    article = parse_article(article_html, item.url, target)

    if not article.publish_time:
        article.publish_time = item.publish_time

    if not article.lines:
        print("ERROR: Article was found but no lines were extracted.", file=sys.stderr)
        raise SystemExit(1)

    _line_prefix_re = re.compile(r"^\d+\.\s*")
    lines: list[str] = []
    for raw_line in article.lines:
        line = _line_prefix_re.sub("", raw_line).strip()
        if line:
            lines.append(line)

    if not lines:
        print("ERROR: No valid lines after filtering.", file=sys.stderr)
        raise SystemExit(1)

    print("=" * 60)
    print(f"[Test Mode] {len(lines)} lines would be submitted:")
    print("=" * 60)
    for line in lines:
        print(f"title: {line}")
        print(f"sourceUrl: {article.url}")
        print(f"publishDateTime: {article.publish_time}")
        print("-" * 40)
    print("=" * 60)


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_print()
    else:
        raise SystemExit(main())
