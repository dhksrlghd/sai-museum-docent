"""
사이 (SAI): 국립중앙박물관 특별전/테마전 스크래퍼
- 현재 진행중인 특별·테마 전시 + 상세 페이지 본문 수집
- 출력: data/raw/special.json
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
USER_AGENT = "Mozilla/5.0 (K-Curator portfolio scraper)"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

LIST_URL = (
    BASE_URL + "/MUSEUM/contents/M0202010000.do?schM=list&menuId=current"
)
DETAIL_URL_TMPL = (
    BASE_URL
    + "/MUSEUM/contents/M0202010000.do?schM=view&menuId=current&exhiSpThemId={id}"
)
REQUEST_DELAY = 1.0


def fetch(url: str) -> BeautifulSoup:
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
    r.raise_for_status()
    r.encoding = "utf-8"
    return BeautifulSoup(r.text, "lxml")


def parse_listing(soup: BeautifulSoup) -> list[dict]:
    items: list[dict] = []
    for a in soup.find_all("a", href=True):
        m = re.search(r"exhiSpThemId=(\d+)", a["href"])
        if not m:
            continue
        eid = m.group(1)
        # 카드를 거슬러 올라가 li까지
        li = a
        while li and li.name != "li":
            li = li.parent
        if not li:
            continue
        # 카드 안의 정보 추출
        title_el = None
        for cand in li.find_all("a", href=True):
            txt = cand.get_text(strip=True)
            if txt and "exhiSpThemId" in cand["href"] and 4 < len(txt) < 60:
                title_el = cand
                break
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        # 라벨 (현재전시 / 특별전 / 테마전)
        labels = [l.get_text(strip=True) for l in li.select(".label-type") if l.get_text(strip=True)]
        # 기간 / 장소 (li 내 ul/li 구조)
        period, location = "", ""
        for inner_li in li.select("li"):
            t = inner_li.get_text(" ", strip=True)
            if "기간" in t and not period:
                period = re.sub(r"^기간\s*", "", t)
            elif "장소" in t and not location:
                location = re.sub(r"^장소\s*", "", t)

        # 썸네일: 첫 <img>는 hover-over 버튼 아이콘이므로 건너뛰고,
        # previewThumbnail 또는 실제 썸네일 경로를 가진 img를 우선 선택.
        thumb = ""
        for cand in li.find_all("img"):
            src = cand.get("src", "")
            if not src:
                continue
            if "btn_more_report" in src or "/btn/" in src:
                continue
            thumb = urljoin(BASE_URL, src)
            break

        # 중복 방지
        if any(it["exhi_id"] == eid for it in items):
            continue
        items.append(
            {
                "exhi_id": eid,
                "title": title,
                "labels": labels,
                "period": period,
                "location": location,
                "thumbnail_url": thumb,
                "detail_url": DETAIL_URL_TMPL.format(id=eid),
            }
        )
    return items


def parse_detail(soup: BeautifulSoup) -> dict:
    """특별전 상세에서 본문 + 추가 이미지 추출.
    페이지가 헤더 없이 평범한 <p> 들로 본문을 두는 케이스가 많아
    '50자 이상 <p>'를 모두 모으는 단순 휴리스틱을 사용.
    """
    out = {"intro": "", "page_title": "", "extra_images": []}
    if soup.title:
        out["page_title"] = soup.title.get_text(strip=True)

    container = soup.find(id="contents-area") or soup.body
    if not container:
        return out

    # 의미있는 단락 수집 (네비/푸터 무시)
    paragraphs: list[str] = []
    for p in container.find_all("p"):
        # 자식에 또 다른 큰 컨테이너가 있으면 스킵
        if p.find(["p", "ul", "ol", "table"]):
            continue
        txt = p.get_text(" ", strip=True)
        if not txt:
            continue
        # 너무 짧거나 네비/메뉴성 문구 필터
        if len(txt) < 30:
            continue
        if re.match(r"^(QR|주소|스크랩|인쇄|공유|Home|기간|장소|문의|운영)", txt):
            continue
        if txt in paragraphs:
            continue
        paragraphs.append(txt)

    out["intro"] = "\n\n".join(paragraphs).strip()

    # 본문 이미지
    for img in container.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue
        if any(k in src for k in ("exhi", "files/zin", "previewThumbnail")):
            url = urljoin(BASE_URL, src)
            if url not in out["extra_images"]:
                out["extra_images"].append(url)

    return out


def main() -> int:
    print(f"[scrape_special] 리스트 페이지 요청...")
    soup = fetch(LIST_URL)
    items = parse_listing(soup)
    print(f"[scrape_special] {len(items)}개 전시 발견")

    enriched: list[dict] = []
    for it in items:
        time.sleep(REQUEST_DELAY)
        print(f"  [{it['exhi_id']}] {it['title']} 상세...")
        try:
            d = fetch(it["detail_url"])
            detail = parse_detail(d)
            enriched.append({**it, **detail})
            print(f"    소개 {len(detail['intro'])}자 / 이미지 {len(detail['extra_images'])}장")
        except Exception as e:
            print(f"    FAIL: {e}", file=sys.stderr)
            enriched.append({**it, "intro": "", "page_title": "", "extra_images": []})

    out = {
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": LIST_URL,
        "exhibitions": enriched,
    }
    out_path = RAW_DIR / "special.json"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print(f"  진행중 전시: {len(enriched)}개")
    total_chars = sum(len(e["intro"]) for e in enriched)
    print(f"  소개 본문 총합: {total_chars:,}자")
    print(f"  저장: {out_path}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
