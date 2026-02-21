#!/usr/bin/env python3
"""
혁신의숲(InnoForest) 분석리포트 크롤러
https://www.innoforest.co.kr/report?newsTypeCd=RR&page=1
목록은 JS 렌더링이므로 Playwright로 수집 후, 본문은 requests로 수집 시도.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse

# Vault root
try:
    from vault_path import get_vault_root
except ModuleNotFoundError:
    current_dir = Path(__file__).resolve().parent
    for parent in [current_dir.parent, current_dir.parent.parent]:
        if (parent / "Skills" / "vault_path").exists():
            sys.path.insert(0, str(parent / "Skills"))
            break
    from vault_path import get_vault_root

VAULT_ROOT = get_vault_root()

# 기본 저장: 전략팀 리서치 하위 혁신의숲 폴더
DEFAULT_OUTPUT_DIR = VAULT_ROOT / "10. 전략팀" / "리서치 애널리스트" / "시장동향" / "혁신의숲"

BASE_URL = "https://www.innoforest.co.kr"
LIST_URL = f"{BASE_URL}/report"
LIST_PARAMS = {"newsTypeCd": "RR", "page": 1}


def get_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        return None


def crawl_list_playwright(max_pages: int = 5) -> List[Dict[str, Any]]:
    """Playwright로 리포트 목록 페이지를 열고, 링크·제목 수집 (페이지네이션 지원)."""
    sync_playwright = get_playwright()
    if not sync_playwright:
        print("Playwright가 필요합니다: pip install playwright && playwright install chromium")
        return []

    items: List[Dict[str, Any]] = []
    seen_urls: set = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_default_timeout(15000)

            for page_num in range(1, max_pages + 1):
                url = f"{LIST_URL}?newsTypeCd=RR&page={page_num}"
                print(f"목록 로딩: {url}")
                page.goto(url, wait_until="networkidle")

                # 리스트가 로드될 때까지 대기 (카드/링크 선택자)
                page.wait_for_timeout(2000)

                # 리포트 상세로 가는 링크 수집: /report/ 로 시작하거나 report 포함, 쿼리만 있는 목록 URL 제외
                links = page.query_selector_all('a[href*="report"]')
                page_items = 0
                for a in links:
                    href = a.get_attribute("href") or ""
                    full_url = urljoin(BASE_URL, href)
                    if full_url in seen_urls:
                        continue
                    # 목록 페이지 자체 제외 (report?newsTypeCd=...)
                    if "newsTypeCd=" in href and "/report/" not in href:
                        continue
                    # 상세 페이지만: /report/숫자 또는 /report/슬러그
                    if "/report/" not in href:
                        continue
                    try:
                        title_el = a.query_selector("h2, h3, .title, [class*='title'], strong")
                        title = (title_el and title_el.inner_text()) or a.inner_text() or full_url
                        title = title.strip() or f"Report {len(items)+1}"
                    except Exception:
                        title = f"Report {len(items)+1}"
                    seen_urls.add(full_url)
                    items.append({"title": title, "url": full_url})
                    page_items += 1
                    print(f"  수집: {title[:50]}...")

                if page_items == 0:
                    break
                # 다음 페이지가 있는지 확인 (버튼/링크)
                next_btn = page.query_selector('a[href*="page="], button:has-text("다음"), [aria-label*="next"]')
                if not next_btn or page_num >= max_pages:
                    break

        finally:
            browser.close()

    return items


def fetch_article_body(url: str, timeout: int = 10) -> str:
    """본문 텍스트 추출 시도 (requests)."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return ""
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
        r.raise_for_status()
    except Exception:
        return ""
    soup = BeautifulSoup(r.text, "html.parser")
    for sel in ["article", "div.article", ".post-content", ".content", "main", "[class*='report'] [class*='body']"]:
        el = soup.select_one(sel)
        if el:
            paras = el.find_all("p")
            if paras:
                return "\n\n".join(p.get_text(strip=True) for p in paras[:50])
    return ""


def save_to_markdown(items: List[Dict[str, Any]], output_dir: Path, fetch_body: bool = False) -> str:
    """수집한 목록을 마크다운 한 파일로 저장."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"혁신의숲_분석리포트_{date_str}.md"
    path = output_dir / filename

    lines = [
        "---",
        f"title: 혁신의숲 분석리포트 스크랩 ({date_str})",
        f"date: {date_str}",
        f"source: {LIST_URL}",
        f"total: {len(items)}",
        "---",
        "",
        f"# 혁신의숲 분석리포트 ({date_str})",
        "",
        f"총 **{len(items)}**건 수집.",
        "",
        "---",
        "",
    ]

    for i, item in enumerate(items, 1):
        title = item.get("title", "")
        url = item.get("url", "")
        body = ""
        if fetch_body and url:
            body = fetch_article_body(url)
        lines.append(f"## {i}. [{title}]({url})")
        lines.append("")
        if body:
            lines.append(body[:4000] + ("..." if len(body) > 4000 else ""))
            lines.append("")
        lines.append("---")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="혁신의숲 분석리포트 크롤링")
    parser.add_argument("--max-pages", type=int, default=5, help="목록 최대 페이지 수")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR), help="저장 디렉터리")
    parser.add_argument("--fetch-body", action="store_true", help="각 리포트 본문도 수집 (requests)")
    args = parser.parse_args()

    items = crawl_list_playwright(max_pages=args.max_pages)
    if not items:
        print("수집된 항목이 없습니다. Playwright 설치: pip install playwright && playwright install chromium")
        return 1

    out_path = save_to_markdown(items, Path(args.output_dir), fetch_body=args.fetch_body)
    print(f"저장 완료: {out_path} ({len(items)}건)")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
