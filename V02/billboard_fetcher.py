import csv
import datetime as dt
import itertools
import logging
import os
import random
import time
from importlib import metadata as importlib_metadata

import billboard
import requests

CHART_NAME = "hot-100"
CHART_DATE = "2025-12-27"
OUTPUT_XLSX = "billboard_hot100_2025.xlsx"
OUTPUT_CSV = "billboard_hot100_2025.csv"
LOG_FILE = "billboard_fetch.log"
REQUEST_DELAY_SECONDS = 1.5
RETRY_DELAY_SECONDS = 5
MAX_RETRIES = 3
PAGE_SIZE = 25
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def parse_version(version_str):
    if not version_str:
        return (0, 0, 0)
    parts = []
    for chunk in version_str.split("."):
        if chunk.isdigit():
            parts.append(int(chunk))
        else:
            num = "".join(ch for ch in chunk if ch.isdigit())
            parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def check_billboard_version():
    try:
        version_str = importlib_metadata.version("billboard.py")
    except importlib_metadata.PackageNotFoundError:
        version_str = None
    version_tuple = parse_version(version_str)
    if version_tuple < (6, 0, 0):
        logging.warning("billboard.py版本可能低于6.0：%s", version_str)
    else:
        logging.info("billboard.py版本：%s", version_str)


def make_session_with_user_agent(user_agent, max_retries):
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    session.mount(
        "https://www.billboard.com",
        requests.adapters.HTTPAdapter(max_retries=max_retries),
    )
    return session


def fetch_chart_with_retries():
    user_agent_cycle = itertools.cycle(USER_AGENTS)
    last_error = None
    original_session_builder = billboard._get_session_with_retries
    for attempt in range(1, MAX_RETRIES + 1):
        user_agent = next(user_agent_cycle)
        logging.info("开始抓取（第%d次），User-Agent=%s", attempt, user_agent)
        try:
            time.sleep(REQUEST_DELAY_SECONDS)

            def _session_builder(max_retries):
                return make_session_with_user_agent(user_agent, max_retries)

            billboard._get_session_with_retries = _session_builder
            chart = billboard.ChartData(
                CHART_NAME,
                date=CHART_DATE,
                max_retries=0,
                timeout=25,
            )
            if len(chart.entries) < 100:
                raise ValueError(f"抓取到的条数不足100：{len(chart.entries)}")
            return chart
        except Exception as exc:
            last_error = exc
            logging.exception("抓取失败：%s", exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
        finally:
            billboard._get_session_with_retries = original_session_builder
    raise last_error


def paginate_entries(entries):
    pages = []
    for idx in range(0, len(entries), PAGE_SIZE):
        pages.append(entries[idx : idx + PAGE_SIZE])
    return pages


def deduplicate_entries(entries):
    seen = set()
    deduped = []
    for entry in entries:
        title = (getattr(entry, "title", "") or "").strip().lower()
        artist = (getattr(entry, "artist", "") or "").strip().lower()
        key = (title, artist)
        if key in seen:
            logging.warning("发现重复记录：%s - %s", entry.title, entry.artist)
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def entry_to_dict(entry, chart, fetched_at, total_count):
    data = {}
    if hasattr(entry, "__dict__"):
        data.update(entry.__dict__)
    for field in [
        "title",
        "artist",
        "rank",
        "peakPos",
        "lastPos",
        "weeks",
        "isNew",
        "isReEntry",
        "weeksOnChart",
        "image",
        "detail",
        "songid",
    ]:
        if field not in data and hasattr(entry, field):
            data[field] = getattr(entry, field)
    data["chart_name"] = chart.name
    data["chart_title"] = chart.title
    data["chart_date"] = chart.date or CHART_DATE
    data["fetched_at"] = fetched_at
    data["total_count"] = total_count
    return data


def write_csv(rows, fieldnames):
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(rows, fieldnames, fetched_at, total_count):
    try:
        import openpyxl
    except ImportError as exc:
        raise ImportError("缺少openpyxl依赖，请先安装：pip install openpyxl") from exc

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "hot100"
    sheet.append(fieldnames)
    for row in rows:
        sheet.append([row.get(name, "") for name in fieldnames])

    summary = workbook.create_sheet(title="summary")
    summary.append(["fetched_at", fetched_at])
    summary.append(["total_count", total_count])
    summary.append(["chart_name", CHART_NAME])
    summary.append(["chart_date", CHART_DATE])

    workbook.save(OUTPUT_XLSX)


def main():
    setup_logging()
    logging.info("开始执行Billboard Hot 100抓取")
    check_billboard_version()

    chart = fetch_chart_with_retries()
    entries = chart.entries

    pages = paginate_entries(entries)
    logging.info("分页完成：共%d页，每页最多%d条", len(pages), PAGE_SIZE)

    flattened = [entry for page in pages for entry in page]
    deduped = deduplicate_entries(flattened)

    if len(deduped) != 100:
        raise ValueError(f"去重后条数不为100：{len(deduped)}")

    fetched_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    total_count = len(deduped)

    rows = [entry_to_dict(entry, chart, fetched_at, total_count) for entry in deduped]
    fieldnames = sorted({key for row in rows for key in row.keys()})

    write_csv(rows, fieldnames)
    write_xlsx(rows, fieldnames, fetched_at, total_count)

    logging.info("CSV输出完成：%s", os.path.abspath(OUTPUT_CSV))
    logging.info("Excel输出完成：%s", os.path.abspath(OUTPUT_XLSX))

    top10 = [(row.get("rank"), row.get("title"), row.get("artist")) for row in rows]
    logging.info("Top10抽查数据：%s", top10[:10])
    logging.info("抓取完成，总条数：%d", total_count)


if __name__ == "__main__":
    main()
