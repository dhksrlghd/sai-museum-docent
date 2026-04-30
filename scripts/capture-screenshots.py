"""
사이 (SAI) — 라이브 사이트 자동 캡처
- Playwright headless Chromium으로 라이브 HF Space 순회
- docs/images/ 에 PNG 저장
- LFS 트래킹 대상이므로 git add 시 자동으로 LFS 포인터로 변환됨
"""

from __future__ import annotations

import sys
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "images"
BASE = "https://wangihong-k-curator.hf.space"

# 데스크톱 기준 1280×800 (README 미리보기 표 셀에 280px 노출 시 자연스러움)
VIEWPORT = {"width": 1280, "height": 800}


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT, locale="ko-KR")
        page = context.new_page()

        # 1) 홈
        print("[1/4] /  → home.png")
        page.goto(f"{BASE}/", wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(2_000)  # 매일의 큐레이션 fetch 대기
        page.screenshot(path=str(OUT_DIR / "home.png"), full_page=False)

        # 2) 코스 빌더
        print("[2/4] /plan → plan-builder.png")
        page.goto(f"{BASE}/plan", wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(1_500)
        page.screenshot(path=str(OUT_DIR / "plan-builder.png"), full_page=False)

        # 3) 작품 상세 (기영회도)
        print("[3/4] /work/2351292 → work-detail.png")
        page.goto(f"{BASE}/work/2351292", wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(3_000)  # 닮은 작품 grid fetch 대기
        page.screenshot(path=str(OUT_DIR / "work-detail.png"), full_page=False)

        # 4) 모바일 뷰
        print("[4/4] mobile / → mobile.png")
        mobile_ctx = browser.new_context(
            viewport={"width": 390, "height": 800},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
        )
        mpage = mobile_ctx.new_page()
        mpage.goto(f"{BASE}/", wait_until="networkidle", timeout=60_000)
        mpage.wait_for_timeout(2_000)
        mpage.screenshot(path=str(OUT_DIR / "mobile.png"), full_page=False)
        mobile_ctx.close()

        browser.close()

    print("\n✓ 4장 저장 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
