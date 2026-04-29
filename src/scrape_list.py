"""
K-Curator: 큐레이터 추천 작품 ID 리스트 수집
- 출처: https://www.museum.go.kr/MUSEUM/contents/M0501000000.do?searchId=recommend&relicRecommendUse=Y
- pageSize=500 으로 한 번에 321건을 받아온다.
- 출력: data/raw/relic_list.json
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.museum.go.kr"
LIST_URL = BASE_URL + "/MUSEUM/contents/M0501000000.do"
USER_AGENT = "Mozilla/5.0 (K-Curator portfolio scraper)"
PAGE_SIZE = 500  # 전체 321건이 1페이지에 다 들어옴

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def fetch_list(page: int, page_size: int = PAGE_SIZE) -> BeautifulSoup:
    """리스트 페이지 1개를 받아 BeautifulSoup으로 반환."""
    params = {
        "cp": page,
        "searchId": "recommend",
        "relicRecommendUse": "Y",
        "pageSize": page_size,
    }
    resp = requests.get(
        LIST_URL,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return BeautifulSoup(resp.text, "lxml")


def parse_total(soup: BeautifulSoup) -> int:
    """'총321건이 검색되었습니다.' 같은 문구에서 총 건수를 뽑는다."""
    el = soup.find(class_="board-list-total")
    if not el:
        return 0
    m = re.search(r"(\d[\d,]*)", el.get_text(strip=True))
    return int(m.group(1).replace(",", "")) if m else 0


def parse_cards(soup: BeautifulSoup) -> list[dict]:
    """<li class='card'> 카드들을 파싱."""
    items = []
    for card in soup.find_all("li", class_="card"):
        link = card.find("a", href=True)
        if not link:
            continue
        href = link["href"]
        m = re.search(r"relicRecommendId=(\d+)", href)
        if not m:
            continue
        relic_id = int(m.group(1))

        # 제목: 두 번째 <a>(div.txt 안)의 텍스트가 가장 깔끔
        txt_link = None
        txt_div = card.find("div", class_="txt")
        if txt_div:
            txt_link = txt_div.find("a")
        title_text = (txt_link.get_text(strip=True) if txt_link else "").strip()

        # 썸네일
        img = card.find("img")
        thumb = ""
        if img and img.get("src"):
            thumb = urljoin(BASE_URL, img["src"])

        items.append(
            {
                "relic_recommend_id": relic_id,
                "title_full": title_text,
                "thumbnail_url": thumb,
                "detail_url": urljoin(
                    BASE_URL,
                    "/MUSEUM/contents/M0501000000.do"
                    f"?schM=view&relicRecommendId={relic_id}",
                ),
            }
        )
    return items


def collect_all() -> dict:
    """전체 리스트를 한 번에 수집. 안전망으로 페이지 루프도 지원."""
    print(f"[scrape_list] pageSize={PAGE_SIZE}로 1페이지 요청...")
    soup = fetch_list(1)
    total = parse_total(soup)
    items = parse_cards(soup)
    print(f"[scrape_list] 총 표시 건수: {total}, 1페이지에서 받음: {len(items)}")

    seen = {it["relic_recommend_id"] for it in items}
    page = 2
    while len(items) < total and page <= 50:  # 안전 상한
        time.sleep(1.0)
        print(f"[scrape_list] 추가 페이지 {page} 요청...")
        soup = fetch_list(page)
        new_items = [
            it for it in parse_cards(soup) if it["relic_recommend_id"] not in seen
        ]
        if not new_items:
            print("[scrape_list] 새 항목 없음 — 종료")
            break
        items.extend(new_items)
        seen.update(it["relic_recommend_id"] for it in new_items)
        page += 1

    return {
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source_url": LIST_URL,
        "total_reported": total,
        "total_collected": len(items),
        "items": items,
    }


def save(data: dict) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "relic_list.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out


def print_summary(data: dict) -> None:
    print("=" * 60)
    print(f"  사이트가 보고한 건수 : {data['total_reported']}")
    print(f"  실제 수집한 건수     : {data['total_collected']}")
    print("-" * 60)
    print("  처음 3건 / 마지막 3건:")
    for it in data["items"][:3]:
        print(f"    {it['relic_recommend_id']}  {it['title_full'][:60]}")
    print("    ...")
    for it in data["items"][-3:]:
        print(f"    {it['relic_recommend_id']}  {it['title_full'][:60]}")
    print("=" * 60)


def main() -> int:
    try:
        data = collect_all()
    except requests.RequestException as e:
        print(f"[scrape_list] 네트워크 오류: {e}", file=sys.stderr)
        return 1

    if data["total_collected"] == 0:
        print("[scrape_list] 수집 실패: 항목 0건", file=sys.stderr)
        return 2

    out = save(data)
    print(f"[scrape_list] 저장 완료: {out}")
    print()
    print_summary(data)

    if data["total_collected"] != data["total_reported"]:
        print(
            "[scrape_list] 경고: 보고된 총 건수와 수집 건수가 다릅니다.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
