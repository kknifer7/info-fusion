#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import urllib3
import warnings
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urljoin

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests
from bs4 import BeautifulSoup


LIST_URL = "https://www.jetmast.com/?keyword=60秒读懂世界"
API_URL = "http://127.0.0.1:3000/news"
CRAWL_RESULT_API_URL = "http://127.0.0.1:3000/crawl-result"
CRAWLER_ID = 6
DEFAULT_TIMEZONE = "Asia/Shanghai"
KEYWORD = "60秒读懂世界"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/133.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.jetmast.com/",
}

_LINE_PREFIX_RE = re.compile(r"^\d+\.\s*")
_DATE_HEADER_RE = re.compile(r"^\*{0,2}\d{1,2}月\d{1,2}日\*{0,2}")
_DAY_OF_WEEK_RE = re.compile(r"^(星期[一二三四五六日]|周[一二三四五六日])")
_DATE_WEEK_INLINE_RE = re.compile(r"\d{1,2}月\d{1,2}日\s+(星期[一二三四五六日]|周[一二三四五六日])")


@dataclass
class Article:
    title: str
    url: str
    publish_time: str
    lines: list[str]


def today_in_timezone(tz_name: str) -> date:
    try:
        from zoneinfo import ZoneInfo
    except ImportError as exc:
        raise RuntimeError("Python 3.9+ is required for zoneinfo timezone support.") from exc
    return datetime.now(ZoneInfo(tz_name)).date()


def fetch_html(url: str, timeout: int = 20) -> str:
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=timeout,
        verify=False,
    )
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def _extract_date_from_list_title(title: str) -> date | None:
    """Extract date like '06月11日' from list page title."""
    m = re.match(r"(\d{1,2})月(\d{1,2})日", title)
    if m:
        return date(datetime.now().year, int(m.group(1)), int(m.group(2)))
    return None


def find_article_url(html: str, base_url: str) -> tuple[str, str]:
    """Find the most recent article whose title contains the keyword.
    Returns (title, full_url).
    Raises if the article date is not today.
    """
    soup = BeautifulSoup(html, "html.parser")
    for h in soup.find_all(["h2", "h3", "h4"]):
        link = h.select_one("a[href]")
        if not link:
            continue
        title = link.get_text(strip=True)
        if KEYWORD in title:
            # Check date is today
            article_date = _extract_date_from_list_title(title)
            if article_date:
                today = today_in_timezone(DEFAULT_TIMEZONE)
                if article_date != today:
                    raise ValueError(
                        f"Latest article date ({article_date}) is not today ({today}). "
                        f"Skipping crawl."
                    )
            href = link.get("href", "").strip()
            full_url = urljoin(base_url, href)
            return title, full_url
    raise ValueError(f"No article with keyword '{KEYWORD}' found on the list page.")


def _extract_publish_time(soup: BeautifulSoup) -> str:
    """Extract publish time from the '温馨提示：本文最后更新于...' text."""
    # Search for element containing '最后更新'
    for elem in soup.find_all(string=re.compile(r"最后更新")):
        parent = elem.parent
        if not parent:
            continue
        full_text = parent.get_text(strip=True)
        # e.g. "温馨提示：本文最后更新于2026年6月11日 00:30，如数据或图片失效..."
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\d{1,2}):(\d{2})", full_text)
        if m:
            return (
                f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d} "
                f"{m.group(4).zfill(2)}:{m.group(5)}:00"
            )
    return ""


def parse_article(html: str, url: str) -> Article:
    soup = BeautifulSoup(html, "html.parser")

    # Title
    og_title = soup.select_one('meta[property="og:title"]')
    title = og_title.get("content", "").strip() if og_title else ""
    if not title:
        h1 = soup.select_one("h1")
        if h1:
            title = h1.get_text(strip=True)

    # Publish time
    publish_time = _extract_publish_time(soup)

    # Body
    body = soup.select_one(".article-content")
    if not body:
        raise ValueError("Could not find article body: expected .article-content")

    for removable in body.select("script, style"):
        removable.decompose()

    lines: list[str] = []
    seen: set[str] = set()
    for elem in body.find_all(["p", "div"]):
        text = elem.get_text(" ", strip=True)
        if not text or text in seen:
            continue
        seen.add(text)

        # Skip date header lines like "06月11日 星期三"
        if _DATE_HEADER_RE.match(text):
            continue
        if _DAY_OF_WEEK_RE.match(text):
            continue
        # Skip lines that contain inline date+week (e.g. "**06月11日**  **星期三**")
        if _DATE_WEEK_INLINE_RE.search(text):
            continue
        # Skip the "60秒读懂世界" title line that appears with date header
        if "60秒读懂世界" in text and (_DATE_HEADER_RE.search(text) or _DAY_OF_WEEK_RE.search(text)):
            continue
        # Skip too-short lines
        if len(text) < 5:
            continue
        # Skip lines without meaningful Chinese/English text
        if not re.search(r"[\u4e00-\u9fff]", text) and not re.search(r"[a-zA-Z]{3,}", text):
            continue
        lines.append(text)

    if not lines:
        raise ValueError("Article body was found but no text content was extracted.")

    return Article(
        title=title,
        url=url,
        publish_time=publish_time,
        lines=lines,
    )


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
        list_html = fetch_html(LIST_URL)
        list_title, article_url = find_article_url(list_html, base_url=LIST_URL)

        article_html = fetch_html(article_url)
        article = parse_article(article_html, url=article_url)

        if not article.publish_time:
            target = today_in_timezone(DEFAULT_TIMEZONE)
            article.publish_time = f"{target.isoformat()} 00:00:00"

        ok_count = 0
        fail_count = 0
        for raw_line in article.lines:
            line = _LINE_PREFIX_RE.sub("", raw_line).strip()
            if not line:
                continue
            article_data = {
                "title": line,
                "content": line,
                "sourceUrl": article.url,
                "publishDateTime": article.publish_time,
                "remark": "JetMast-60秒读懂世界",
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
    list_html = fetch_html(LIST_URL)
    list_title, article_url = find_article_url(list_html, base_url=LIST_URL)

    article_html = fetch_html(article_url)
    article = parse_article(article_html, url=article_url)

    if not article.publish_time:
        target = today_in_timezone(DEFAULT_TIMEZONE)
        article.publish_time = f"{target.isoformat()} 00:00:00"

    lines: list[str] = []
    for raw_line in article.lines:
        line = _LINE_PREFIX_RE.sub("", raw_line).strip()
        if line:
            lines.append(line)

    if not lines:
        print("ERROR: No valid lines after filtering.", file=sys.stderr)
        raise SystemExit(1)

    print("=" * 60)
    print(f"[Test Mode] list_title={list_title}")
    print(f"article_url={article_url}")
    print(f"{len(lines)} lines would be submitted:")
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
