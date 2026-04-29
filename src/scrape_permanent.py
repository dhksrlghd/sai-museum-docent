"""
사이 (SAI): 국립중앙박물관 상설전시 스크래퍼
- 7관 39실을 순회하며 각 실의 소개 텍스트 + 현재 전시중인 작품 리스트 수집
- 출력: data/raw/permanent.json (단일 파일)

전략:
  1. 7개 관 메인 페이지로 시작 → 각 관 안의 실 목록 발견
  2. 각 실 페이지에서 실 소개 본문 + '전시품' 목록 추출
  3. 층(F) 정보는 사전에서 부착
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

# 7관 entry: (관 이름, 층, 진입 URL)
HALLS = [
    ("중·근세관",     "1F", "https://www.museum.go.kr/MUSEUM/contents/M0201040100.do?showHallId=759&showroomCode=DM0036"),
    ("선사·고대관",   "1F", "https://www.museum.go.kr/MUSEUM/contents/M0201030100.do?showHallId=760&showroomCode=DM0002"),
    ("서화관",        "2F", "https://www.museum.go.kr/MUSEUM/contents/M0201050100.do?showHallId=758&showroomCode=DM0028"),
    ("기증관",        "2F", "https://www.museum.go.kr/MUSEUM/contents/M0201060100.do?showHallId=755&showroomCode=DM0078"),
    ("사유의 방",     "2F", "https://www.museum.go.kr/MUSEUM/contents/M0201070100.do?showHallId=631120&showroomCode=DM0075"),
    ("조각·공예관",   "3F", "https://www.museum.go.kr/MUSEUM/contents/M0201080100.do?showHallId=757&showroomCode=DM0074"),
    ("세계문화관",    "3F", "https://www.museum.go.kr/MUSEUM/contents/M0201090200.do?showHallId=756&showroomCode=DM0024"),
]

REQUEST_DELAY = 1.0


def fetch(url: str) -> BeautifulSoup:
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
    r.raise_for_status()
    r.encoding = "utf-8"
    return BeautifulSoup(r.text, "lxml")


def discover_rooms(hall_entry_url: str) -> list[dict]:
    """관 메인 페이지에서 그 안의 모든 실 URL 발견.
    좌측 메뉴/탭에 다른 실들이 링크돼 있다.
    """
    soup = fetch(hall_entry_url)
    rooms: list[dict] = []
    seen_codes = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        name = a.get_text(strip=True)
        if not name or len(name) > 30:
            continue
        m = re.search(r"showHallId=(\d+)&showroomCode=(DM\d+)", href)
        if not m:
            continue
        hall_id, code = m.group(1), m.group(2)
        if code in seen_codes:
            continue
        seen_codes.add(code)
        rooms.append(
            {
                "showroom_code": code,
                "hall_id": hall_id,
                "room_name": name,
                "url": urljoin(BASE_URL, href),
            }
        )
    return rooms


def _korean_ratio(s: str) -> float:
    """문자열에서 한글(가-힣) 비율. alt 텍스트(영어)와 한국어 본문 구분용."""
    if not s:
        return 0.0
    korean = sum(1 for c in s if "가" <= c <= "힣")
    total_letters = sum(1 for c in s if c.isalpha())
    if total_letters == 0:
        return 0.0
    return korean / total_letters


def parse_room_page(soup: BeautifulSoup) -> dict:
    """실 페이지 파싱:
      - intro: 한국어 비율이 높은 단락들 모음 (영어 alt 텍스트, 부모 관 공통 안내 제외)
      - works: '전시품' 섹션의 작품 이름 리스트
    """
    out = {"intro": "", "works": [], "page_title": ""}
    if soup.title:
        out["page_title"] = soup.title.get_text(strip=True)

    container = soup.find(id="contents-area") or soup.body
    if not container:
        return out

    # ------ intro 추출 ------
    # 의미있는 단락(50~2500자)이고, 한국어 비율 ≥ 60%인 것들만 수집
    candidates: list[str] = []
    seen_signatures: set = set()
    for el in container.find_all(["div", "p"]):
        # 자식에 큰 컨테이너가 또 있으면 패스 (중복 방지)
        if el.find(["div", "p", "ul", "ol", "table"]):
            continue
        text = el.get_text(" ", strip=True)
        if not text or len(text) < 50 or len(text) > 2500:
            continue
        # alt 텍스트 마커 / 네비게이션 제거
        if re.match(r"^\(.*?에 대한 대체", text):
            continue
        if re.match(r"^(QR|주소|스크랩|인쇄|공유|Home|이전|다음|페이지|첨부|위치)", text):
            continue
        # 한국어 비율 필터
        if _korean_ratio(text) < 0.55:
            continue
        # 중복(같은 시작 60자) 제거
        sig = text[:60]
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)
        candidates.append(text)

    # 부모 관 공통 안내(같은 관의 모든 실에서 반복되는 130자짜리)는 호출자가 제거
    out["intro"] = "\n\n".join(candidates).strip()

    # ------ works 추출 ------
    works: list[str] = []
    # '전시품' 섹션 헤더부터 다음 헤더 전까지의 li 수집
    for hdr in container.find_all(["h3", "h4", "h5"]):
        if hdr.get_text(strip=True) == "전시품":
            sib = hdr.find_next_sibling()
            steps = 0
            while sib and steps < 8:
                if sib.name in ("ul", "ol", "dl"):
                    for li in sib.find_all(["li", "dt", "dd"], recursive=True):
                        t = li.get_text(" ", strip=True)
                        if t and 4 <= len(t) <= 200:
                            works.append(t)
                    break
                if sib.name in ("h3", "h4", "h5"):
                    break
                sib = sib.find_next_sibling()
                steps += 1
            break

    # 백업: 텍스트 마커 기반
    if not works:
        text = container.get_text("\n", strip=True)
        m = re.search(r"전시품\s*\n(.+?)(?=\n(?:전시실 소개|이전|다음|페이지|\Z))", text, re.S)
        if m:
            for line in m.group(1).splitlines():
                line = line.strip()
                if line and 4 <= len(line) <= 200 and not re.match(r"^(더보기|위치|전시관)", line):
                    works.append(line)

    out["works"] = [w for w in works if w]
    return out


def scrape_room(hall_name: str, floor: str, room: dict) -> dict:
    soup = fetch(room["url"])
    parsed = parse_room_page(soup)
    return {
        "hall": hall_name,
        "floor": floor,
        "room_name": room["room_name"],
        "showroom_code": room["showroom_code"],
        "hall_id": room["hall_id"],
        "url": room["url"],
        "page_title": parsed["page_title"],
        "intro": parsed["intro"],
        "works": parsed["works"],
    }


def main() -> int:
    print(f"[scrape_permanent] {len(HALLS)}개 관 진입")
    all_rooms: list[dict] = []
    for hall_name, floor, entry_url in HALLS:
        print(f"\n[{hall_name} ({floor})] 실 목록 발견 중...")
        try:
            rooms = discover_rooms(entry_url)
        except Exception as e:
            print(f"  관 진입 실패: {e}", file=sys.stderr)
            continue
        # entry url의 진입 실도 포함시키기 (DM 코드가 위에 있으면 이미 들어가 있음)
        # 단, 다른 관의 entry로 잘못 잡힌 코드는 hall 컨텍스트로 필터
        # 단순화: 그냥 발견된 모든 실 사용
        print(f"  {len(rooms)}개 실 발견:")
        for r in rooms:
            print(f"    - {r['room_name']:30s} [{r['showroom_code']}]")

        for r in rooms:
            try:
                data = scrape_room(hall_name, floor, r)
                all_rooms.append(data)
                print(f"    OK {r['room_name']}: 소개 {len(data['intro'])}자 / 작품 {len(data['works'])}점")
            except Exception as e:
                print(f"    FAIL {r['room_name']}: {e}", file=sys.stderr)
            time.sleep(REQUEST_DELAY)

    # 동일 실이 여러 관에 잡힌 경우 dedupe (showroom_code 단위)
    by_code: dict = {}
    for room in all_rooms:
        key = room["showroom_code"]
        if key in by_code:
            # 더 풍부한 데이터 유지
            if len(room["intro"]) > len(by_code[key]["intro"]):
                by_code[key] = room
        else:
            by_code[key] = room
    deduped = list(by_code.values())

    out = {
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "https://www.museum.go.kr/MUSEUM/contents/M0201010000.do",
        "halls": [{"name": n, "floor": f} for n, f, _ in HALLS],
        "rooms": deduped,
    }

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / "permanent.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    total_works = sum(len(r["works"]) for r in deduped)
    total_intro_chars = sum(len(r["intro"]) for r in deduped)
    print()
    print("=" * 60)
    print(f"  실 수집: {len(deduped)}개 (dedupe 후)")
    print(f"  작품 총합: {total_works}점")
    print(f"  소개 텍스트: 총 {total_intro_chars:,}자")
    print(f"  저장: {out_path}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
