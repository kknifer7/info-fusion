#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import urllib3
import warnings
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests
from bs4 import BeautifulSoup


LIST_URL = (
    "https://i.news.qq.com/getSubNewsMixedList"
    "?offset_info=&guestSuid=8QMd2H9V6YAdvz7a&tabId=om_index"
)
DETAIL_URL_TEMPLATE = "https://news.qq.com/rain/a/{news_id}"
API_URL = "http://127.0.0.1:3000/news"
CRAWL_RESULT_API_URL = "http://127.0.0.1:3000/crawl-result"
CRAWLER_ID = 4
DEFAULT_TIMEZONE = "Asia/Shanghai"
KEYWORD = "三分钟新闻早知道"

EXCLUDED_LINE_PREFIXES = (
    "每天3分钟",
    "今天是",
    "新闻早知道",
    "【微语】",
)
_DATE_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}$")
_DATE_GREETING_RE = re.compile(r"^\d{1,2}月\d{1,2}日星期[一二三四五六日]")
_LINE_PREFIX_RE = re.compile(r"^\d+[、.]\s*")
_SECTION_HEADER_RE = re.compile(r"^(硬新闻|热点速览|国际新闻|国内新闻|社会新闻|财经新闻)")
_NOISE_RE = re.compile(r"^(PARAGRAPH_\d+|EOP_\d+|IMG_\d+|VERTICAL_CARD_(BEGIN|END)_\d+)$")
_NOISE_INLINE_RE = re.compile(r"\s*(PARAGRAPH_\d+|EOP_\d+|IMG_\d+|VERTICAL_CARD_(BEGIN|END)_\d+)\s*")
_SOURCE_CITATION_RE = re.compile(r"[（(][^）)]+[）)]\s*$")

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
class NewsListItem:
    news_id: str
    title: str
    url: str
    publish_time: str


@dataclass
class Article:
    title: str
    url: str
    publish_time: str
    content: str
    lines: list[str]


def today_in_timezone(tz_name: str) -> date:
    try:
        from zoneinfo import ZoneInfo
    except ImportError as exc:
        raise RuntimeError("Python 3.9+ is required for zoneinfo timezone support.") from exc
    return datetime.now(ZoneInfo(tz_name)).date()


def fetch_json(url: str, timeout: int = 20) -> dict:
    response = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
    response.raise_for_status()
    return response.json()


def fetch_html(url: str, timeout: int = 20) -> str:
    response = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def clean_lines(lines: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        value = re.sub(r"\s+", " ", line).strip()
        if value:
            cleaned.append(value)
    return cleaned


def filter_article_lines(lines: Iterable[str], article_title: str, article_source: str) -> list[str]:
    result: list[str] = []
    # Strip suffix like "_腾讯新闻" from title for comparison
    clean_title = article_title
    if "_" in clean_title:
        clean_title = clean_title.rsplit("_", 1)[0]

    for line in lines:
        # Skip article title itself (with or without suffix)
        if line == article_title or line == clean_title:
            continue
        # Skip date/time lines
        if _DATE_TIME_RE.match(line):
            continue
        # Skip date greeting lines like "6月5日星期五..."
        if _DATE_GREETING_RE.match(line):
            continue
        # Skip excluded prefixes
        if line.startswith(EXCLUDED_LINE_PREFIXES):
            continue
        # Skip pure source name
        if line == article_source:
            continue
        # Skip section headers
        if _SECTION_HEADER_RE.match(line):
            continue
        # Skip editor noise markers (PARAGRAPH_0, EOP_1, IMG_2, etc.)
        if _NOISE_RE.match(line):
            continue
        # Skip common noise
        if line in ("举报", "关注", "用AI"):
            continue
        # Strip trailing source citations like "（央视新闻）" or "（外交部网站）"
        line = _SOURCE_CITATION_RE.sub("", line).strip()
        if not line:
            continue

        # Skip too-short lines that don't start with a number prefix
        # (numbered entries may be short after stripping prefix, keep them)
        if len(line) < 5 and not _LINE_PREFIX_RE.match(line):
            continue
        result.append(line)
    return result


def parse_news_list(data: dict) -> list[NewsListItem]:
    items: list[NewsListItem] = []
    seen_ids: set[str] = set()
    for raw in data.get("newslist", []):
        news_id = raw.get("id", "").strip()
        title = raw.get("title", "").strip()
        url = raw.get("url", "").strip()
        publish_time = raw.get("time", "").strip()
        if not news_id or not title or not url:
            continue
        if news_id in seen_ids:
            continue
        seen_ids.add(news_id)
        items.append(
            NewsListItem(
                news_id=news_id,
                title=title,
                url=url,
                publish_time=publish_time,
            )
        )
    return items


def find_target_item(items: list[NewsListItem]) -> NewsListItem:
    """Find the most recent item whose title contains the keyword."""
    for item in items:
        if KEYWORD in item.title:
            return item
    raise ValueError(f"No news item with keyword '{KEYWORD}' found.")


def _extract_title_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    og_title = soup.select_one('meta[property="og:title"]')
    if og_title:
        return og_title.get("content", "").strip()
    h1 = soup.select_one("h1") or soup.select_one("h2")
    if h1:
        return h1.get_text(" ", strip=True)
    return ""


def _extract_publish_time(html: str) -> str:
    match = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", html)
    return match.group(0) if match else ""


def _extract_non_nested_text(sec) -> str:
    """Extract text from a section that is NOT inside any child <section>."""
    parts: list[str] = []
    for child in sec.children:
        if getattr(child, "name", None) == "section":
            continue
        if isinstance(child, str):
            text = child.strip()
            if text:
                parts.append(text)
        else:
            text = child.get_text(" ", strip=True)
            if text:
                parts.append(text)
    return " ".join(parts)


def _remove_noise_markers(text: str) -> str:
    return _NOISE_INLINE_RE.sub(" ", text).strip()


def _extract_body_lines_from_origin(html: str) -> list[str] | None:
    """Try to extract clean body lines from window.DATA.originContent.text."""
    m = re.search(r"window\.DATA\s*=\s*({.+?});", html, re.DOTALL)
    if not m:
        return None
    try:
        data = __import__("json").loads(m.group(1))
    except Exception:
        return None
    origin_html = data.get("originContent", {}).get("text", "")
    if not origin_html:
        return None
    soup = BeautifulSoup(origin_html, "html.parser")
    for rem in soup.select("script, style"):
        rem.decompose()

    # Extract text from every <section> that is NOT part of a child <section>.
    # This catches cover-news text which sits alongside the "封面新闻" label
    # inside an outer <section>.
    lines: list[str] = []
    seen: set[str] = set()
    for sec in soup.find_all("section"):
        text = _extract_non_nested_text(sec)
        text = _remove_noise_markers(text)
        if text and text not in seen:
            seen.add(text)
            lines.append(text)
    if not lines:
        # Fallback to <p> tags, then plain get_text
        for p in soup.find_all("p"):
            text = p.get_text(" ", strip=True)
            if text:
                lines.append(text)
    if not lines:
        lines = clean_lines(soup.get_text("\n", strip=True).splitlines())
    return clean_lines(lines)


def parse_article(html: str, url: str) -> Article:
    title = _extract_title_from_html(html)
    publish_time = _extract_publish_time(html)

    # Prefer originContent for cleaner text, fallback to .content-article
    lines = _extract_body_lines_from_origin(html)
    if lines is None:
        soup = BeautifulSoup(html, "html.parser")
        body = soup.select_one(".content-article")
        if not body:
            raise ValueError("Could not find article body: expected .content-article")
        for rem in body.select("script, style, iframe, video"):
            rem.decompose()
        # Extract text from every <section> that is NOT inside a child <section>.
        lines = []
        seen: set[str] = set()
        for sec in body.find_all("section"):
            text = _extract_non_nested_text(sec)
            text = _remove_noise_markers(text)
            if text and text not in seen:
                seen.add(text)
                lines.append(text)
        if not lines:
            for p in body.find_all("p"):
                text = p.get_text(" ", strip=True)
                if text:
                    lines.append(text)
        if not lines:
            lines = clean_lines(body.get_text("\n", strip=True).splitlines())

    # Heuristic source detection from HTML meta
    source = ""
    og_site_match = re.search(r'<meta[^>]*property="og:site_name"[^>]*content="([^"]*)"', html)
    if og_site_match:
        source = og_site_match.group(1).strip()
    if not source:
        author_match = re.search(r'<meta[^>]*name="author"[^>]*content="([^"]*)"', html)
        if author_match:
            source = author_match.group(1).strip()

    lines = filter_article_lines(lines, article_title=title, article_source=source)
    content = "\n".join(lines)
    if not content:
        raise ValueError("Article body was found but no text content was extracted.")

    return Article(
        title=title,
        url=url,
        publish_time=publish_time,
        content=content,
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
        target = today_in_timezone(DEFAULT_TIMEZONE)

        list_data = fetch_json(LIST_URL)
        items = parse_news_list(list_data)
        item = find_target_item(items)

        detail_url = DETAIL_URL_TEMPLATE.format(news_id=item.news_id)
        article_html = fetch_html(detail_url)
        article = parse_article(article_html, url=detail_url)

        if not article.publish_time:
            article.publish_time = item.publish_time

        if not article.lines:
            raise ValueError("Article was found but no lines were extracted.")

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
                "remark": "腾讯新闻-三分钟新闻早知道",
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

    list_data = fetch_json(LIST_URL)
    items = parse_news_list(list_data)
    item = find_target_item(items)

    detail_url = DETAIL_URL_TEMPLATE.format(news_id=item.news_id)
    article_html = fetch_html(detail_url)
    article = parse_article(article_html, url=detail_url)

    if not article.publish_time:
        article.publish_time = item.publish_time

    if not article.lines:
        print("ERROR: Article was found but no lines were extracted.", file=sys.stderr)
        raise SystemExit(1)

    lines: list[str] = []
    for raw_line in article.lines:
        line = _LINE_PREFIX_RE.sub("", raw_line).strip()
        if line:
            lines.append(line)

    if not lines:
        print("ERROR: No valid lines after filtering.", file=sys.stderr)
        raise SystemExit(1)

    print("=" * 60)
    print(f"[Test Mode] news_id={item.news_id} title={article.title}")
    print(f"detail_url={detail_url}")
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
