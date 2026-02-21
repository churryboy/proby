#!/usr/bin/env python3
"""
Mixpanel Data Export API 2.0로 Raw Event를 내보내서
'70. 메이커스/믹스패널 데이터/' 폴더에 JSONL 파일로 저장합니다.

[설정]
1. Mixpanel 프로젝트 설정 → Access Keys에서 Project ID, API Secret 확인
2. vault 루트 .env에 추가:
   MIXPANEL_PROJECT_ID=프로젝트ID
   MIXPANEL_API_SECRET=API시크릿

[실행]
  python3 "Skills/Mixpanel 내보내기/mixpanel_export.py"
  python3 "Skills/Mixpanel 내보내기/mixpanel_export.py" 2026-02-01 2026-02-20  # 기간 지정
"""

import base64
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

try:
    import requests
except ImportError:
    print("requests 필요: pip install requests")
    sys.exit(1)

_VAULT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = _VAULT_ROOT / "70. 메이커스" / "믹스패널 데이터"
EXPORT_URL = "https://data.mixpanel.com/api/2.0/export"


def _load_env(key: str) -> str:
    """vault 루트 .env에서 key 값 읽기."""
    env_path = _VAULT_ROOT / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip().strip('"').strip("'")
    return ""


def export_events(
    from_date: str,
    to_date: str,
    project_id: str,
    basic_auth_user: str,
    basic_auth_secret: str,
    event_filter: Optional[List[str]] = None,
) -> List[dict]:
    """Mixpanel Export API 2.0로 이벤트 조회. Basic auth는 Service Account 또는 project_id:api_secret."""
    auth = base64.b64encode(f"{basic_auth_user}:{basic_auth_secret}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Accept": "text/plain"}
    params = {"project_id": project_id, "from_date": from_date, "to_date": to_date}
    if event_filter:
        params["event"] = json.dumps(event_filter)

    # stream=False로 호출해 4xx 시 응답 본문을 확실히 확인할 수 있게 함
    r = requests.get(EXPORT_URL, headers=headers, params=params, timeout=120)
    if not r.ok:
        print("응답 본문:", r.text[:1500] if r.text else "(비어 있음)")
        r.raise_for_status()

    out = []
    for line in r.text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def main() -> None:
    project_id = _load_env("MIXPANEL_PROJECT_ID")
    api_secret = _load_env("MIXPANEL_API_SECRET")
    sa_username = _load_env("MIXPANEL_SA_USERNAME")
    sa_secret = _load_env("MIXPANEL_SA_SECRET")

    if not project_id:
        print("오류: .env에 MIXPANEL_PROJECT_ID를 설정해주세요.")
        sys.exit(1)

    # Service Account가 있으면 그걸로 Basic auth, 없으면 project_id:api_secret (레거시)
    if sa_username and sa_secret:
        basic_user, basic_secret = sa_username, sa_secret
    elif api_secret:
        basic_user, basic_secret = project_id, api_secret
    else:
        print("오류: .env에 MIXPANEL_API_SECRET 또는 MIXPANEL_SA_USERNAME+MIXPANEL_SA_SECRET을 설정해주세요.")
        sys.exit(1)

    # 기간: 인자 2개면 from_date, to_date / 아니면 최근 7일
    if len(sys.argv) >= 3:
        from_date = sys.argv[1]
        to_date = sys.argv[2]
    else:
        today = datetime.utcnow().date()
        to_date = today.isoformat()
        from_date = (today - timedelta(days=7)).isoformat()

    print(f"기간: {from_date} ~ {to_date}")
    print("요청 중...")

    try:
        events = export_events(from_date, to_date, project_id, basic_user, basic_secret)
    except requests.RequestException as e:
        print(f"API 오류: {e}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_name = f"export_{from_date}_{to_date}.jsonl"
    out_path = OUTPUT_DIR / out_name

    with open(out_path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    print(f"저장 완료: {len(events)}개 이벤트 → {out_path}")
    if events:
        names = {}
        for ev in events:
            n = ev.get("event") or "unknown"
            names[n] = names.get(n, 0) + 1
        print("  이벤트 종류:", dict(names))


if __name__ == "__main__":
    main()
