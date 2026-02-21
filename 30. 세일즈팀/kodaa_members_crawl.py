#!/usr/bin/env python3
"""
KODAA(한국디지털광고협회) 전체 회원사 목록 수집 스크립트.
https://kodaa.or.kr/43 페이지에서 회원사 이름과, 공개된 경우 이메일을 수집해 CSV로 저장합니다.

사용: python3 kodaa_members_crawl.py
출력: 30. 세일즈팀/kodaa_members.csv
"""

import csv
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://kodaa.or.kr"
MEMBERS_PAGE = f"{BASE_URL}/43"
OUTPUT_CSV = Path(__file__).resolve().parent / "kodaa_members.csv"

# 이메일 정규식 (일반적인 비즈니스 이메일)
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def fetch(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def extract_emails_from_text(text: str) -> list[str]:
    return list(set(EMAIL_PATTERN.findall(text)))


# 메뉴/네비 텍스트 제외용 (회원사명으로 오인하지 않기)
SKIP_TEXTS = {
    "뒤로", "더보기", "로그아웃", "협회소개", "인사말", "주요사업", "조직도", "찾아오시는 길",
    "데이터센터", "산업시장", "법제·정책", "법제동향", "회원사 정보", "회원사 현황", "임원사", "전체 회원사",
    "회원사 가입 절차 안내", "대한민국 디지털 광고 대상", "출품안내", "대한민국 대학생 디지털 광고제",
    "site search", "MENU", "Alarm", "마이페이지", "게시물 알림", "공지사항", "내 글 반응",
    "2025 KODAF 수상작", "2024 KUDAF 수상작", "2025 KUDAF 수상작", "2025 광고제 접수 안내",
    "(사)한국디지털광고협회",
}


def extract_members_from_list_page(html: str) -> list[dict]:
    """회원 목록 페이지 HTML에서 회원사 이름·링크·이메일 후보를 추출.
    (페이지가 JS 로딩이면 회원 그리드가 없을 수 있어, 후처리에서 fallback 사용)
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    page_emails = extract_emails_from_text(html)

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = (a.get_text() or "").strip()
        if not text or "다운로드" in text or "준비중" in text:
            continue
        name = normalize_company_name(text)
        if len(name) < 2:
            continue
        if name in SKIP_TEXTS or any(skip in name for skip in ("반응", "알림", "설정", "검색", "공지사항", "사이트에서")):
            continue
        if len(name) > 45:  # 메뉴 설명 등 긴 텍스트 제외
            continue
        full_url = href if href.startswith("http") else (BASE_URL.rstrip("/") + "/" + href.lstrip("/"))
        if "javascript" in href:
            full_url = ""
        rows.append({
            "company_name": name,
            "profile_url": full_url,
            "email": "",
            "source": "list_page",
        })

    seen = set()
    unique_rows = []
    for r in rows:
        key = r["company_name"]
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(r)

    if page_emails and unique_rows:
        for addr in page_emails:
            if "kodaa" in addr.lower():
                continue
        if page_emails:
            unique_rows[0]["email"] = "; ".join(page_emails[:3])

    return unique_rows


def normalize_company_name(raw: str) -> str:
    """회사명 정규화 (반복 제거, 공백 정리)."""
    s = raw.strip()
    # 같은 문자열이 2~3번 반복된 경우 한 번만
    if len(s) >= 4:
        third = len(s) // 3
        if third > 0 and s[:third] == s[third : 2 * third] == s[2 * third : 3 * third]:
            s = s[:third]
        elif len(s) >= 2 and s[: len(s) // 2] == s[len(s) // 2 :]:
            s = s[: len(s) // 2]
    return s.strip()


# 회사 사이트에서 제외할 이메일 패턴 (일반 문의용 아님)
EMAIL_BLACKLIST = re.compile(
    r"noreply|no-reply|donotreply|do-not-reply|notification|newsletter|"
    r"support@(facebook|google|microsoft)|sentry|wix\.com|example\.com|"
    r"email\s*protection|@.*\.(png|jpg|gif|svg)\b",
    re.I
)


def is_good_contact_email(addr: str, site_domain: str) -> bool:
    """문의용으로 쓸 만한 이메일인지 판별."""
    addr_lower = addr.lower()
    if EMAIL_BLACKLIST.search(addr_lower):
        return False
    if addr_lower.count("@") != 1:
        return False
    # 도메인 일치 또는 회사 도메인과 관련 있으면 우선 (선택)
    return True


def pick_best_email(emails: list[str]) -> str:
    """우선순위: info, contact, biz, sales, help, 그 외 첫 번째."""
    for prefix in ("info@", "contact@", "biz@", "sales@", "help@", "ad@", "marketing@"):
        for e in emails:
            if e.lower().startswith(prefix):
                return e
    return emails[0] if emails else ""


def scrape_emails_from_company_sites(members: list[dict], delay_sec: float = 1.2) -> list[dict]:
    """각 회원사의 profile_url(회사 웹사이트)에 접속해 이메일 수집. kodaa.or.kr 제외."""
    total = len(members)
    has_url = sum(1 for m in members if m.get("profile_url") and "kodaa.or.kr" not in (m.get("profile_url") or ""))
    print(f"회사 웹사이트에서 이메일 수집 중 (대상 {has_url}개, KODAA 제외) ...")

    for i, m in enumerate(members):
        url = (m.get("profile_url") or "").strip()
        if not url or "javascript" in url or "kodaa.or.kr" in url:
            continue
        try:
            html = fetch(url)
            # mailto: 링크 우선
            soup = BeautifulSoup(html, "html.parser")
            mailto_emails = []
            for a in soup.find_all("a", href=True):
                h = a.get("href", "").strip()
                if h.lower().startswith("mailto:"):
                    addr = h[7:].split("?")[0].strip().split(",")[0].strip()
                    if EMAIL_PATTERN.fullmatch(addr) and is_good_contact_email(addr, url):
                        mailto_emails.append(addr)
            # 페이지 텍스트에서 이메일
            text_emails = [e for e in extract_emails_from_text(html) if is_good_contact_email(e, url)]
            candidates = list(dict.fromkeys(mailto_emails + text_emails))  # 순서 유지, 중복 제거
            if candidates:
                m["email"] = pick_best_email(candidates)
                m["source"] = "company_site"
            if (i + 1) % 20 == 0:
                print(f"  진행: {i+1}/{total}")
        except Exception as e:
            pass  # 타임아웃/연결 실패 시 스킵
        time.sleep(delay_sec)

    return members


FALLBACK_MEMBER_NAMES = [
    "나스미디어", "씨제이메조미디어", "코마스인터렉티브", "엠포스", "디트라이브", "크로스미디어",
    "다츠", "리서치애드", "네이트커뮤니케이션즈", "인크로스", "카카오", "이엠넷",
    "나무커뮤니케이션", "판도라TV", "제이슨그룹", "네이버", "벡터컴", "에이전시더블유",
    "펜타브리드", "숲", "인터웍스미디어", "플레이디", "하나애드IMC", "다트미디어",
    "차이커뮤니케이션", "유어비즈", "디지털다임", "마더브레인", "비욘드마케팅그룹", "애드미션",
    "애드쿠아인터렉티브", "이너스커뮤니티", "퍼틸레인", "크리테오", "수커뮤니케이션", "키스톤마케팅컴퍼니",
    "메타", "구글코리아", "엔에이치엔애드", "엔비티", "비즈스프링", "미래I&C",
    "아이디어키", "아이애드원", "애드게이트", "엠피인터랙티브", "예지솔루션", "이레컴즈",
    "이프로애드", "카페24", "트리플하이엠", "엔에이치엔에이스", "프로그레스미디어", "디지털트리니티",
    "디티에스아이", "엠투디지털", "제일기획", "버즈빌", "펜타클", "게티이미지코리아",
    "바이너리큐브", "이인벤션", "모비데이즈", "모티브 인텔리전스", "아티스트유나이티드", "베리타스커넥트",
    "디퍼플", "에이치에스애드", "디지털퍼스트", "블루오렌지커뮤니케이션즈", "아인스미디어", "인라이플",
    "디엑스이", "휴먼미디어그룹", "픽스다인엠", "애드이피션시", "제이브릿지마케팅컴퍼니", "더에스엠씨",
    "씨더블유", "엣지랭크", "애니포인트미디어", "에이엠피엠글로벌", "와일리", "아이지에이웍스",
    "넥스트미디어그룹", "퍼포먼스바이TBWA", "오피엠에스", "망고스타코리아", "위시미디어", "티디아이플레이",
    "에이원퍼포먼스팩토리", "젤리피쉬코리아", "드림인사이트", "그랑몬스터", "엠플랜잇", "이스터씨앤아이",
    "함샤우트글로벌", "엘지CNS", "이엠씨지", "인테그럴 애드 사이언스", "온더플래닛", "애드온컴퍼니",
    "위플랫폼", "볼디", "그루컴퍼니", "스파클인터렉티브", "봄센", "미래PMP",
    "크리에이터링", "매드업", "생각하는늑대", "페리온", "와이즈버즈", "오버맨",
    "리머지", "디플랜360", "스타디엠코퍼레이션", "디뉴먼트", "피알원", "에이디쏠인터렉티브",
    "토이306", "코비그룹", "프레인글로벌", "엠코퍼레이션", "틱톡", "티엠씨케이",
    "케이피알앤드어소시에이츠", "매드코퍼레이션", "아치서울", "이노션", "비바리퍼블리카", "비에이티",
    "더쏠트", "크로마엔터테인먼트", "나인독", "함파트너스", "엠서치마케팅", "몽규",
    "레뷰코퍼레이션", "벨커뮤니케이션즈", "포이시스", "커뮤니크", "PTKOREA", "애드커넥스",
    "스마일코리아", "커스텀그라운드", "가치브라더", "잘함", "스냅컴퍼니", "퍼즐코퍼레이션",
    "카카오페이", "하이브월드와이드", "더트레이드데스크", "닐슨미디어코리아", "케이앤웍스", "포바이포",
    "애디플", "엑솔라코리아", "제이비컴스컴퍼니", "엘리케이트", "투겟", "부스터즈",
    "써치엠", "지엔앰퍼포먼스", "씨브이쓰리", "어센드미디어", "얀고애즈", "이엔미디어",
    "유디엠", "트레져헌터", "런커뮤니케이션즈",
]


def main():
    print("KODAA 회원사 목록 수집 중:", MEMBERS_PAGE)
    html = fetch(MEMBERS_PAGE)
    members = extract_members_from_list_page(html)

    # 페이지가 JS 로딩이면 회원 그리드가 HTML에 없어, 회원처럼 보이는 게 20개 미만이면 협회 공개 명단 사용
    if len(members) < 20:
        members = [
            {"company_name": name, "profile_url": MEMBERS_PAGE, "email": "", "source": "kodaa_fallback"}
            for name in FALLBACK_MEMBER_NAMES
        ]

    # 최종 필터: 메뉴/협회 안내 항목 제거
    members = [m for m in members if m["company_name"] in FALLBACK_MEMBER_NAMES or (
        m["company_name"] not in SKIP_TEXTS
        and "및 연혁" not in m["company_name"]
        and "공지사항" not in m["company_name"]
    )]

    # 각 회원사 웹사이트(profile_url)에 직접 접속해 이메일 수집 (KODAA 사이트 제외)
    members = scrape_emails_from_company_sites(members, delay_sec=1.2)

    # CSV 저장
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["company_name", "email", "profile_url", "source"])
        w.writeheader()
        w.writerows(members)

    print(f"저장 완료: {OUTPUT_CSV} (총 {len(members)}개 회원사)")
    has_email = sum(1 for m in members if m.get("email"))
    if has_email == 0:
        print("안내: KODAA 공개 페이지에는 회원사별 이메일이 없을 수 있습니다. 회사명만 저장되었습니다.")
        print("이메일은 각사 웹사이트, B2B DB(예: Apollo, ZoomInfo), 또는 협회 문의로 보완하실 수 있습니다.")


if __name__ == "__main__":
    main()
