#!/usr/bin/env python3
"""
마크다운 파일 내용을 Slack Incoming Webhook으로 지정 채널에 전송합니다.
.env의 SLACK_WEBHOOK_URL을 사용합니다.

사용법:
  python3 "Skills/슬랙 전송/md_to_slack.py" "경로/파일.md"
  python3 "Skills/슬랙 전송/md_to_slack.py" "경로/파일.md" "메시지 제목(선택)"
"""

import os
import re
import sys
from pathlib import Path

# 프로젝트 루트(proby-sync) .env 로드
def load_dotenv():
    try:
        from dotenv import load_dotenv as _load_dotenv
    except ImportError:
        return
    script_dir = Path(__file__).resolve().parent
    vault_root = script_dir.parent.parent
    for p in [script_dir / ".env", script_dir.parent / ".env", vault_root / ".env", Path.cwd() / ".env"]:
        if p and p.exists():
            _load_dotenv(dotenv_path=str(p))
            return


def md_to_slack_mrkdwn(text: str) -> str:
    """일반 마크다운을 Slack mrkdwn에 가깝게 변환 (간단 버전)."""
    if not text:
        return text
    # **bold** -> *bold*
    s = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    # __bold__ -> *bold*
    s = re.sub(r"__(.+?)__", r"*\1*", s)
    return s


def send_to_slack(webhook_url: str, text: str, use_mrkdwn: bool = True) -> bool:
    """Slack Incoming Webhook으로 메시지 전송. 성공 시 True."""
    try:
        import urllib.request
        import json
    except ImportError:
        print("urllib.request / json 사용 불가")
        return False

    body = {"text": md_to_slack_mrkdwn(text) if use_mrkdwn else text}
    # Slack 메시지 상한 (40KB 등). 너무 길면 잘라서 전송할 수 있음
    if len(body["text"]) > 39000:
        body["text"] = body["text"][:38900] + "\n\n… (잘림)"

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"전송 실패: {e}")
        return False


def main():
    load_dotenv()
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not webhook_url:
        print(".env에 SLACK_WEBHOOK_URL을 설정해주세요.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("사용법: python3 md_to_slack.py <마크다운파일경로> [메시지 제목]")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"파일을 찾을 수 없습니다: {path}")
        sys.exit(1)

    title = sys.argv[2] if len(sys.argv) > 2 else None
    raw = path.read_text(encoding="utf-8")
    if title:
        text = f"*{title}*\n\n{raw}"
    else:
        text = raw

    if send_to_slack(webhook_url, text):
        print("Slack으로 전송했습니다.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
