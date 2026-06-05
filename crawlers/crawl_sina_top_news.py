#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import warnings
from datetime import date, datetime
from typing import Iterable

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import requests
from bs4 import BeautifulSoup


SINA_API_URL_TEMPLATE = (
    "https://top.news.sina.com.cn/ws/GetTopDataList.php"
    "?top_type=day&top_cat=www_www_all_suda_suda"
    "&top_time={date_str}&top_show_num={show_num}"
    "&top_order=DESC&js_var=all_1_data01"
)
API_URL = "http://127.0.0.1:3000/news"
CRAWL_RESULT_API_URL = "http://127.0.0.1:3000/crawl-result"
CRAWLER_ID = 2
DEFAULT_TIMEZONE = "Asia/Shanghai"
MAX_ARTICLES = 10

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


def fetch_api(url: str, timeout: int = 20) -> str:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_jsonp(jsonp_text: str) -> dict:
    match = re.search(r"\w+\s*=\s*({.*})", jsonp_text, re.DOTALL)
    if not match:
        raise ValueError("Could not find JSON data in JSONP response")
    return json.loads(match.group(1))


def parse_sina_article(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_node = soup.select_one("h1") or soup.select_one("#artibodyTitle")
    title = title_node.get_text(strip=True) if title_node else ""

    body = soup.select_one("#artibody")
    if not body:
        body = soup.select_one("article")
    if not body:
        body = soup.select_one(".article-content")

    if body:
        for removable in body.select("script, style, iframe, video"):
            removable.decompose()
        paragraphs = [p.get_text(strip=True) for p in body.select("p") if p.get_text(strip=True)]
        content = "\n".join(paragraphs)
    else:
        content = ""

    return {"title": title, "content": content, "sourceUrl": url}


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


def _build_payload(item: dict) -> dict:
    create_date = item.get("create_date", "")
    create_time = item.get("create_time", "")
    publish_dt = f"{create_date} {create_time}" if create_date and create_time else ""
    return {
        "title": item.get("title", ""),
        "content": item.get("title", ""),
        "sourceUrl": item.get("url", ""),
        "publishDateTime": publish_dt,
        "remark": "新浪新闻排行榜-国内新闻",
    }


def main() -> int:
    target = today_in_timezone(DEFAULT_TIMEZONE)
    date_str = target.strftime("%Y%m%d")
    api_url = SINA_API_URL_TEMPLATE.format(date_str=date_str, show_num=MAX_ARTICLES)

    try:
        api_text = fetch_api(api_url)
        api_data = parse_jsonp(api_text)
        news_list = api_data.get("data", [])

        if not news_list:
            raise ValueError("No news items returned from Sina API")

        ok_count = 0
        fail_count = 0
        for item in news_list[:MAX_ARTICLES]:
            payload = _build_payload(item)
            try:
                response = requests.post(API_URL, json=payload, timeout=30)
                response.raise_for_status()
                ok_count += 1
                print(f"[OK] {payload['title']}")
            except Exception as exc:
                fail_count += 1
                print(f"[FAIL] {payload['title']} | {exc}", file=sys.stderr)

        message = (
            f"[Crawl OK] submitted={ok_count} failed={fail_count} | "
            f"date_filter={target.isoformat()}"
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
    date_str = target.strftime("%Y%m%d")
    api_url = SINA_API_URL_TEMPLATE.format(date_str=date_str, show_num=MAX_ARTICLES)

    try:
        api_text = fetch_api(api_url)
        api_data = parse_jsonp(api_text)
        news_list = api_data.get("data", [])

        if not news_list:
            print("ERROR: No news items returned from Sina API", file=sys.stderr)
            raise SystemExit(1)

        print("=" * 60)
        print(f"[Test Mode] {len(news_list[:MAX_ARTICLES])} items would be submitted:")
        print("=" * 60)
        for item in news_list[:MAX_ARTICLES]:
            payload = _build_payload(item)
            print(f"title: {payload['title']}")
            print(f"sourceUrl: {payload['sourceUrl']}")
            print(f"publishDateTime: {payload['publishDateTime']}")
            print("-" * 40)
        print("=" * 60)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_print()
    else:
        raise SystemExit(main())
