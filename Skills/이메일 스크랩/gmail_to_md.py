#!/usr/bin/env python3
"""
Gmail에서 특정 발신 도메인(@도메인)의 메일을 가져와 '30. 세일즈팀/이메일 맥락/<도메인명>/' 폴더에 md 파일로 저장합니다.
도메인만 넣으면 해당 도메인에서 온 메일 전체가 스크랩되며, 도메인 이름으로 하위 폴더가 자동 생성됩니다.

[설정]
1. Google Cloud Console에서 프로젝트 생성 → Gmail API 활성화
2. OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱) → credentials.json 다운로드
3. 이 폴더(Skills/이메일 스크랩)에 credentials.json 배치
4. 스크랩할 도메인: .env의 EMAIL_TARGET_DOMAINS(쉼표 구분) 또는 아래 _DEFAULT_DOMAINS
"""

import os
import re
import base64
from pathlib import Path
from datetime import datetime

# 스크랩할 발신 도메인 (기본값). .env에 EMAIL_TARGET_DOMAINS가 있으면 그걸 우선 사용 (쉼표 구분)
_DEFAULT_DOMAINS = [
    "consumerinsight.kr",
    "communique.co.kr",
    "ridi.com",
    "hanafn.com",
    "nicednr.co.kr",
    "healingpaper.com",
]


def _load_target_domains() -> list:
    """vault 루트 .env에서 EMAIL_TARGET_DOMAINS 읽기. 없거나 비면 기본 목록 사용."""
    env_path = _VAULT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("EMAIL_TARGET_DOMAINS="):
                raw = line.split("=", 1)[1].strip().strip('"').strip("'")
                if raw:
                    return [d.strip() for d in raw.split(",") if d.strip()]
                break
    return _DEFAULT_DOMAINS.copy()

# 저장 경로 = vault 루트(proby-sync)의 '30. 세일즈팀/이메일 맥락' (Skills 폴더가 아님)
_VAULT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = _VAULT_ROOT / "30. 세일즈팀" / "이메일 맥락"
TARGET_DOMAINS = []  # main()에서 _load_target_domains()로 채움


def slug_domain(domain: str) -> str:
    """도메인을 폴더명으로 쓸 수 있도록 안전한 문자열로 변환"""
    s = domain.strip()
    s = re.sub(r'[\\/*?:"<>|]', "_", s)
    return s or "unknown_domain"


def slug(s: str, max_len: int = 60) -> str:
    """파일명에 쓸 수 있도록 안전한 문자열로 변환"""
    s = re.sub(r"[^\w\s\-가-힣.]", "", s)
    s = re.sub(r"\s+", "_", s).strip("_.")
    return s[:max_len] if s else "no_subject"


def get_saved_ids(ids_file: Path) -> set:
    if not ids_file.exists():
        return set()
    return set(ids_file.read_text(encoding="utf-8").strip().splitlines())


def add_saved_id(ids_file: Path, msg_id: str) -> None:
    ids_file.parent.mkdir(parents=True, exist_ok=True)
    with open(ids_file, "a", encoding="utf-8") as f:
        f.write(msg_id + "\n")


def decode_body(payload: dict) -> str:
    """Gmail API payload에서 본문 텍스트 추출"""
    if "body" in payload and payload["body"].get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    if "parts" not in payload:
        return ""
    for part in payload["parts"]:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
            raw = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            # 간단히 HTML 태그 제거
            raw = re.sub(r"<[^>]+>", " ", raw)
            raw = re.sub(r"\s+", " ", raw).strip()
            return raw
    return ""


def get_header(headers: list, name: str) -> str:
    name = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name:
            return h.get("value", "")
    return ""


def build_md(msg_id: str, date_str: str, from_addr: str, to_addr: str, subject: str, body: str) -> str:
    return f"""---
message_id: {msg_id}
date: {date_str}
from: {from_addr}
to: {to_addr}
subject: {subject}
---

# {subject}

- **From**: {from_addr}
- **To**: {to_addr}
- **Date**: {date_str}

---

{body}
"""


def main():
    global TARGET_DOMAINS
    TARGET_DOMAINS = _load_target_domains()

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("필요 패키지: pip3 install -r requirements-gmail.txt (이 폴더에서 실행)")
        return

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds = None
    script_dir = Path(__file__).resolve().parent
    token_path = script_dir / "token.json"
    creds_path = script_dir / "credentials.json"

    if not creds_path.exists():
        print("이 폴더(Skills/이메일 스크랩)에 credentials.json을 넣어주세요. (Google Cloud Console → API 및 서비스 → 사용자 인증 정보)")
        return

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not TARGET_DOMAINS:
        print(".env의 EMAIL_TARGET_DOMAINS 또는 스크립트 내 _DEFAULT_DOMAINS에 스크랩할 발신 도메인을 추가한 뒤 다시 실행하세요.")
        return

    added = 0
    for domain in TARGET_DOMAINS:
        domain = domain.strip()
        if not domain:
            continue
        # 도메인별 하위 폴더: 이메일 맥락/<도메인명>/
        domain_dir = OUTPUT_DIR / slug_domain(domain)
        domain_dir.mkdir(parents=True, exist_ok=True)
        saved_ids_file = domain_dir / ".saved_message_ids.txt"
        saved_ids = get_saved_ids(saved_ids_file)

        # 도메인 기준 검색: from:도메인 → 해당 도메인에서 온 모든 메일
        response = service.users().messages().list(
            userId="me",
            q=f"from:{domain}",
            maxResults=100,
        ).execute()
        messages = response.get("messages", [])

        for m in messages:
            msg_id = m["id"]
            if msg_id in saved_ids:
                continue
            detail = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            payload = detail["payload"]
            headers = payload.get("headers", [])

            date_raw = get_header(headers, "Date")
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(date_raw)
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = date_raw or ""

            from_addr = get_header(headers, "From")
            to_addr = get_header(headers, "To")
            subject = get_header(headers, "Subject")
            body = decode_body(payload)

            safe_subject = slug(subject)
            date_prefix = date_str.replace(" ", "_").replace(":", "-")[:16]
            fname = f"{date_prefix}_{safe_subject}_{msg_id[:8]}.md"
            out_path = domain_dir / fname
            out_path.write_text(
                build_md(msg_id, date_str, from_addr, to_addr, subject, body),
                encoding="utf-8",
            )
            add_saved_id(saved_ids_file, msg_id)
            saved_ids.add(msg_id)
            added += 1
            print(f"저장: {domain_dir.name}/{fname}")

    print(f"완료. 새로 저장된 메일: {added}통")


if __name__ == "__main__":
    main()
