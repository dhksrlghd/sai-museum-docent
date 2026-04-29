"""
K-Curator: 큐레이터 추천 작품 1개 스크래핑
- 입력: relicRecommendId (예: 2351292 = 〈기영회도〉)
- 출력: data/raw/relic_{ID}.json
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
DETAIL_URL = BASE_URL + "/MUSEUM/contents/M0501000000.do"
USER_AGENT = "Mozilla/5.0 (K-Curator portfolio scraper)"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def fetch_page(relic_id: int) -> BeautifulSoup:
    """상세 페이지를 받아 BeautifulSoup으로 반환."""
    params = {"schM": "view", "relicRecommendId": str(relic_id)}
    resp = requests.get(
        DETAIL_URL,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return BeautifulSoup(resp.text, "lxml")


def extract_title_block(soup: BeautifulSoup) -> dict:
    """타이틀 이미지(curator_NNN_tit.*)의 alt에서 제목/부제/큐레이터 분리.
    예: '〈기영회도〉- 세 가지 복을 누린 원로 관료들의 잔치 : 오다연'
    """
    tit_img = soup.find("img", src=re.compile(r"curator_\d+_tit"))
    result = {"title": "", "subtitle": "", "curator": "", "tit_image": ""}
    if not tit_img:
        return result

    result["tit_image"] = urljoin(BASE_URL, tit_img.get("src", ""))
    alt = (tit_img.get("alt") or "").strip()
    if not alt:
        return result

    # 큐레이터명 분리: 공백 변형(' : ', ':', ' :', ': ')과 한국어 콜론 ':' 모두 지원.
    # 거짓 매칭 방지: 콜론 뒤 부분은 ≤20자, 괄호류 미포함이어야 큐레이터로 인정.
    m = re.search(
        r"^(.+?)\s*[:：]\s*([^:：<>《》〈〉『』\[\]]{1,20})\s*$", alt
    )
    if m:
        head = m.group(1).strip()
        result["curator"] = m.group(2).strip()
    else:
        head = alt

    # 제목/부제 분리: ASCII '-', en-dash '–', em-dash '—' 모두 지원
    m = re.match(r"^(.+?)\s*[-–—]\s*(.+)$", head)
    if m:
        result["title"] = m.group(1).strip()
        result["subtitle"] = m.group(2).strip()
    else:
        result["title"] = head.strip()
    return result


def extract_metadata(first_caption: str) -> dict:
    """첫 번째 캡션을 ', '로 분리해 작가/시대/재질/크기/소장번호/등급 추정.
    예: '작가 모름, <기영회도>, 조선 1584년, 비단에 색, 163x128.5cm,
         국립중앙박물관(신수14888), 보물 제1328호'
    """
    meta = {
        "raw_caption": first_caption,
        "artist": "",
        "period": "",
        "medium": "",
        "size": "",
        "collection_no": "",
        "grade": "",
    }
    if not first_caption:
        return meta

    parts = [p.strip() for p in first_caption.split(",") if p.strip()]

    # 휴리스틱: 작가는 보통 0번, 제목은 다양한 괄호로 감싸짐
    # 〈〉 (U+3008/9), 《》 (U+300A/B), 『』 (U+300E/F), <> (ASCII)
    title_re = re.compile(r"[〈《『<].+[〉》』>]")
    title_idx = next((i for i, p in enumerate(parts) if title_re.search(p)), -1)
    rest_start = title_idx + 1 if title_idx >= 0 else 0
    if title_idx > 0:
        meta["artist"] = parts[0]

    period_re = re.compile(
        r"\d{1,4}\s*(년|세기)|조선|고려|신라|백제|고구려|삼국|일제|대한제국"
    )
    grade_re = re.compile(r"(보물|국보|등록문화재|사적|명승)\s*(제\d+\S*)?")

    rest = parts[rest_start:]
    for p in rest:
        if not meta["period"] and period_re.search(p):
            meta["period"] = p
            continue
        # 등급 키워드가 사이즈 등 다른 텍스트와 합쳐진 경우 → 등급만 추출
        gm = grade_re.search(p)
        if gm and not meta["grade"]:
            meta["grade"] = gm.group(0).strip()
            leftover = (p[: gm.start()] + p[gm.end():]).strip(" ,")
            if leftover and re.search(r"\bcm\b|×|x\d", leftover) and not meta["size"]:
                meta["size"] = leftover
            continue
        if re.search(r"\bcm\b|×|x\d", p):
            if not meta["size"]:
                meta["size"] = p
            continue
        if "(" in p and ")" in p and not meta["collection_no"]:
            meta["collection_no"] = p
            continue
        if not meta["medium"]:
            meta["medium"] = p

    return meta


def extract_images(soup: BeautifulSoup) -> list[dict]:
    """본문 이미지(curator_NNN_숫자.*)와 alt 캡션을 순서대로 수집."""
    images = []
    for img in soup.find_all("img", src=re.compile(r"curator_\d+_\d+\.")):
        src = img.get("src", "")
        images.append(
            {
                "url": urljoin(BASE_URL, src),
                "caption": (img.get("alt") or "").strip(),
            }
        )
    return images


def extract_body(soup: BeautifulSoup) -> list[dict]:
    """div.curator50 > div.prg 의 직계 자식을 순서대로 분류.
    h5=heading / p=paragraph / p.quot=quote / div.thum=caption.
    descendants를 쓰면 caption div 내부 텍스트가 paragraph로 중복되므로
    직계 자식만 본다.
    """
    blocks = []
    container = soup.find("div", class_="curator50")
    if not container:
        return blocks

    for prg in container.find_all("div", class_="prg", recursive=False) or [container]:
        for el in prg.find_all(recursive=False):
            name = el.name
            cls = el.get("class") or []
            if name == "h5":
                text = el.get_text(strip=True)
                if text:
                    blocks.append({"type": "heading", "text": text})
            elif name == "p":
                text = el.get_text(" ", strip=True)
                if not text:
                    continue
                block_type = "quote" if "quot" in cls else "paragraph"
                blocks.append({"type": block_type, "text": text})
            elif name == "div" and "thum" in cls:
                cap_span = el.find("span")
                text = cap_span.get_text(" ", strip=True) if cap_span else ""
                img = el.find("img")
                src = img.get("src") if img else ""
                if text:
                    blocks.append(
                        {
                            "type": "caption",
                            "text": text,
                            "image_url": urljoin(BASE_URL, src) if src else "",
                        }
                    )

    return blocks


def extract_license(soup: BeautifulSoup) -> str:
    """공공누리 라이선스 문구."""
    box = soup.find("div", class_="codeCopyright")
    if not box:
        return ""
    txt = box.find("div", class_="txt")
    if txt:
        return txt.get_text(" ", strip=True)
    return box.get_text(" ", strip=True)


def scrape(relic_id: int) -> dict:
    """한 작품 전체 스크래핑."""
    soup = fetch_page(relic_id)

    title_info = extract_title_block(soup)
    images = extract_images(soup)
    first_caption = images[0]["caption"] if images else ""
    metadata = extract_metadata(first_caption)
    body = extract_body(soup)
    license_text = extract_license(soup)

    return {
        "relic_recommend_id": relic_id,
        "source_url": f"{DETAIL_URL}?schM=view&relicRecommendId={relic_id}",
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "title": title_info["title"],
        "subtitle": title_info["subtitle"],
        "curator": title_info["curator"],
        "title_image_url": title_info["tit_image"],
        "metadata": metadata,
        "images": images,
        "body": body,
        "license": license_text,
    }


def save(data: dict) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"relic_{data['relic_recommend_id']}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out_path


def print_summary(data: dict) -> None:
    """수집 결과 요약 (이모지 없이, 한글 콘솔 안전)."""
    print("=" * 60)
    print(f"  제목      : {data['title']}")
    print(f"  부제      : {data['subtitle']}")
    print(f"  큐레이터  : {data['curator']}")
    print("-" * 60)
    md = data["metadata"]
    print(f"  작가      : {md['artist']}")
    print(f"  시대      : {md['period']}")
    print(f"  재질      : {md['medium']}")
    print(f"  크기      : {md['size']}")
    print(f"  소장번호  : {md['collection_no']}")
    print(f"  등급      : {md['grade']}")
    print("-" * 60)
    print(f"  이미지    : {len(data['images'])}장")
    print(f"  본문블록  : {len(data['body'])}개")
    body_chars = sum(len(b["text"]) for b in data["body"])
    print(f"  본문길이  : 약 {body_chars:,}자")
    print(f"  라이선스  : {data['license'][:80]}...")
    print("=" * 60)


def main() -> int:
    # 기본값: 〈기영회도〉
    relic_id = int(sys.argv[1]) if len(sys.argv) > 1 else 2351292

    print(f"[scrape_one] relicRecommendId = {relic_id}")
    print("[scrape_one] 페이지 요청 중...")

    try:
        data = scrape(relic_id)
    except requests.RequestException as e:
        print(f"[scrape_one] 네트워크 오류: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # 파싱 단계 실패도 명시적으로
        print(f"[scrape_one] 파싱 오류: {e}", file=sys.stderr)
        return 2

    out = save(data)
    print(f"[scrape_one] 저장 완료: {out}")
    print()
    print_summary(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
