#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import warnings
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from urllib.parse import urljoin

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import requests
from bs4 import BeautifulSoup


LIST_URL = "https://www.qstheory.cn/qsyw/index.htm"
API_URL = "http://127.0.0.1:3000/news"
CRAWL_RESULT_API_URL = "http://127.0.0.1:3000/crawl-result"
CRAWLER_ID = 3
DEFAULT_TIMEZONE = "Asia/Shanghai"
MAX_ARTICLES = 30

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
class NewsItem:
    title: str
    url: str
    source: str
    author: str
    date_str: str


def today_in_timezone(tz_name: str) -> date:
    try:
        from zoneinfo import ZoneInfo
    except ImportError as exc:
        raise RuntimeError("Python 3.9+ is required for zoneinfo timezone support.") from exc
    return datetime.now(ZoneInfo(tz_name)).date()


def fetch_html(url: str, timeout: int = 20) -> str:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def resolve_full_date(date_str: str, reference_date: date) -> str:
    """将 'MM-DD' 转换为 'YYYY-MM-DD'，基于参考日期推断年份。"""
    match = re.match(r"(\d{2})-(\d{2})", date_str)
    if not match:
        return ""
    month = int(match.group(1))
    day = int(match.group(2))

    year = reference_date.year
    ref_month = reference_date.month
    if month > ref_month or (month == ref_month and day > reference_date.day):
        year -= 1

    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_news_list(html: str, base_url: str, reference_date: date) -> list[NewsItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[NewsItem] = []
    seen_urls: set[str] = set()

    for ul in soup.select("ul.wz-list"):
        for li in ul.select("li"):
            link = li.select_one("a[href]")
            if not link:
                continue

            title = link.get_text(strip=True)
            if ("习近平" in title):
                title = title.replace("习近平", "总书记")
            if ("赵乐际" in title):
                title = title.replace("赵乐际", "全国人大常委会委员长")
            if ("王沪宁" in title):
                title = title.replace("王沪宁", "全国政协主席")
            if ("蔡奇" in title):
                title = title.replace("蔡奇", "中央政治局常委")
            if ("丁薛祥" in title):
                title = title.replace("丁薛祥", "国务院副总理")
            href = link.get("href", "").strip()
            if not title or not href:
                continue

            url = urljoin(base_url, href)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            info_div = li.select_one(".list-style1-info")
            source = ""
            author = ""
            date_str = ""

            if info_div:
                spans = info_div.find_all("span")
                for span in spans:
                    text = span.get_text(strip=True)
                    if text.startswith("来源-"):
                        source = text.replace("来源-", "").strip()
                    elif text.startswith("作者-"):
                        author = text.replace("作者-", "").strip()
                    else:
                        # 最后一个 span 通常是日期
                        date_str = text

            items.append(
                NewsItem(
                    title=title,
                    url=url,
                    source=source,
                    author=author,
                    date_str=date_str,
                )
            )

    return items


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


def _build_payload(item: NewsItem, publish_dt: str) -> dict:
    return {
        "title": item.title,
        "content": item.title,
        "sourceUrl": item.url,
        "publishDateTime": publish_dt,
        "remark": "求是网-要闻",
    }


def main() -> int:
    target = today_in_timezone(DEFAULT_TIMEZONE)
    yesterday = target - timedelta(days=1)
    yesterday_str = yesterday.strftime("%m-%d")
    publish_dt = f"{target.isoformat()} 00:00"

    try:
        html = fetch_html(LIST_URL)
        items = parse_news_list(html, base_url=LIST_URL, reference_date=target)

        if not items:
            raise ValueError("No news items found on the page.")

        items = [item for item in items if item.date_str == yesterday_str]
        if not items:
            raise ValueError(
                f"No news items found for yesterday ({yesterday_str})."
            )

        ok_count = 0
        fail_count = 0
        for item in items[:MAX_ARTICLES]:
            payload = _build_payload(item, publish_dt)
            try:
                response = requests.post(API_URL, json=payload, timeout=30)
                response.raise_for_status()
                ok_count += 1
                print(f"[OK] {item.title}")
            except Exception as exc:
                fail_count += 1
                print(f"[FAIL] {item.title} | {exc}", file=sys.stderr)

        message = (
            f"[Crawl OK] submitted={ok_count} failed={fail_count} | "
            f"date_filter={yesterday_str}"
        )
        report_crawl_result(True, message)
        return 0 if fail_count == 0 else 1

    except Exception as exc:
        msg = f"[Crawl Failed] {exc}"
        print(f"ERROR: {exc}", file=sys.stderr)
        report_crawl_result(False, msg)
        return 1


def test_print() -> None:
    """测试模式：抓取并打印最终数据，不提交 API。"""
    target = today_in_timezone(DEFAULT_TIMEZONE)
    yesterday = target - timedelta(days=1)
    yesterday_str = yesterday.strftime("%m-%d")
    publish_dt = f"{target.isoformat()} 00:00"
    html = fetch_html(LIST_URL)
    items = parse_news_list(html, base_url=LIST_URL, reference_date=target)

    if not items:
        print("ERROR: No news items found on the page.", file=sys.stderr)
        raise SystemExit(1)

    items = [item for item in items if item.date_str == yesterday_str]
    if not items:
        print(
            f"ERROR: No news items found for yesterday ({yesterday_str}).",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print("=" * 60)
    print(f"[Test Mode] {len(items)} items for yesterday ({yesterday_str})")
    print("=" * 60)
    for item in items[:MAX_ARTICLES]:
        payload = _build_payload(item, publish_dt)
        print(f"title: {payload['title']}")
        print(f"sourceUrl: {payload['sourceUrl']}")
        print(f"publishDateTime: {payload['publishDateTime']}")
        print("-" * 40)
    print("=" * 60)


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_print()
    else:
        raise SystemExit(main())
