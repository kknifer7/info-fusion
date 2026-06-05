#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import urllib3
import warnings
from dataclasses import dataclass
from datetime import date, datetime

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests


LIST_API_URL = "https://odin.sohu.com/odin/api/blockdata"
API_URL = "http://127.0.0.1:3000/news"
CRAWL_RESULT_API_URL = "http://127.0.0.1:3000/crawl-result"
CRAWLER_ID = 5
DEFAULT_TIMEZONE = "Asia/Shanghai"
# This API returns the "24小时热点" topic feed; all items are news headlines.

# Fixed POST payload
LIST_PAYLOAD = {
    "pvId": "1780383647746_6m5U6RU",
    "pageId": "1780383696578_1780383453951odi_kK5",
    "mainContent": {
        "productType": "15",
        "productId": "16030",
        "secureScore": "100",
        "categoryId": "46",
        "adTags": "11111111",
        "authorId": 121087346,
    },
    "resourceList": [
        {
            "tplCompKey": "PCTopicTimeLine_1_1_pc_1646220148099",
            "isServerRender": True,
            "isSingleAd": False,
            "content": {
                "spm": "smpc.topic_195.block2_219_toBGno_1_fd",
                "productType": "15",
                "productId": "16030",
                "page": 1,
                "size": 20,
                "pro": "0,1",
                "innerTag": "time-axis",
                "feedType": "XTOPIC_LATEST",
                "view": "timeLineMode",
                "requestId": "1780383650140S82sJIb_16030",
            },
            "adInfo": {"posCode": ""},
            "context": {},
        }
    ],
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Content-Type": "application/json",
}


@dataclass
class NewsItem:
    title: str
    url: str
    pub_time: str  # e.g. "15:39"
    group_title: str  # e.g. "今天", "昨天", "6月4日"


def today_in_timezone(tz_name: str) -> date:
    try:
        from zoneinfo import ZoneInfo
    except ImportError as exc:
        raise RuntimeError("Python 3.9+ is required for zoneinfo timezone support.") from exc
    return datetime.now(ZoneInfo(tz_name)).date()


def _resolve_date(group_title: str, reference_date: date) -> date:
    """Parse groupTitle into a concrete date."""
    if group_title in ("今日", "\u4eca\u65e5"):
        return reference_date
    if group_title in ("昨日", "\u6628\u65e5"):
        return reference_date - __import__("datetime").timedelta(days=1)
    # e.g. "6月4日"
    m = re.match(r"(\d{1,2})\u6708(\d{1,2})\u65e5", group_title)
    if m:
        return date(reference_date.year, int(m.group(1)), int(m.group(2)))
    # e.g. "2025年6月4日"
    m = re.match(r"(\d{4})\u5e74(\d{1,2})\u6708(\d{1,2})\u65e5", group_title)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # Fallback
    return reference_date


def _build_publish_dt(group_title: str, sub_time: str, reference_date: date) -> str:
    """Combine groupTitle date + subGroupTitle time into 'YYYY-MM-DD HH:MM:00'."""
    date_obj = _resolve_date(group_title, reference_date)
    # sub_time is like "15:39"
    time_match = re.match(r"(\d{1,2}):(\d{2})", sub_time)
    if time_match:
        return f"{date_obj.isoformat()} {time_match.group(1).zfill(2)}:{time_match.group(2)}:00"
    return f"{date_obj.isoformat()} 00:00:00"


def fetch_list() -> list[NewsItem]:
    response = requests.post(
        LIST_API_URL,
        json=LIST_PAYLOAD,
        headers=HEADERS,
        timeout=20,
        verify=False,
    )
    response.raise_for_status()
    data = response.json()

    items: list[NewsItem] = []
    inner = data.get("data", {}).get("PCTopicTimeLine_1_1_pc_1646220148099", {})
    raw_list = inner.get("list", [])

    for raw in raw_list:
        title = raw.get("title", "").strip()
        url_path = raw.get("url", "").strip()
        pub_time = raw.get("subGroupTitle", "").strip()  # e.g. "15:39"
        group_title = raw.get("groupTitle", "").strip()  # e.g. "今天"
        if not title:
            continue
        url = f"https://www.sohu.com{url_path}" if url_path else ""
        items.append(NewsItem(title=title, url=url, pub_time=pub_time, group_title=group_title))

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


def main() -> int:
    success = False
    message = ""

    try:
        reference = today_in_timezone(DEFAULT_TIMEZONE)

        items = fetch_list()

        if not items:
            raise ValueError("No news items returned from API.")

        ok_count = 0
        fail_count = 0
        for item in items:
            publish_dt = _build_publish_dt(item.group_title, item.pub_time, reference)
            article_data = {
                "title": item.title,
                "content": item.title,
                "sourceUrl": item.url,
                "publishDateTime": publish_dt,
                "remark": "搜狐-24小时热点",
            }
            try:
                response = requests.post(API_URL, json=article_data, timeout=30)
                response.raise_for_status()
                ok_count += 1
                print(f"[OK] {item.title}")
            except Exception as exc:
                fail_count += 1
                print(f"[FAIL] {item.title} | {exc}", file=sys.stderr)

        message = (
            f"[Crawl OK] submitted={ok_count} failed={fail_count}"
        )
        success = fail_count == 0
    except Exception as exc:
        message = f"[Crawl Failed] {exc}"
        print(f"ERROR: {exc}", file=sys.stderr)

    report_crawl_result(success, message)
    return 0 if success else 1


def test_print() -> None:
    """测试模式：抓取并打印最终数据，不提交 API。"""
    reference = today_in_timezone(DEFAULT_TIMEZONE)

    items = fetch_list()

    if not items:
        print("ERROR: No news items returned from API.", file=sys.stderr)
        raise SystemExit(1)

    print("=" * 60)
    print(f"[Test Mode] {len(items)} items would be submitted")
    print("=" * 60)
    for item in items:
        publish_dt = _build_publish_dt(item.group_title, item.pub_time, reference)
        print(f"title: {item.title}")
        print(f"sourceUrl: {item.url}")
        print(f"publishDateTime: {publish_dt}")
        print("-" * 40)
    print("=" * 60)


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_print()
    else:
        raise SystemExit(main())
