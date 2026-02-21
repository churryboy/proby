#!/usr/bin/env python3
"""
설문 제목 + 문항(타입·선택지 포함)으로 Google Form을 생성합니다.
문항 타입: text(단답), choice(라디오), checkbox(복수선택), scale(선형 배율).

[사용법]
  -q "질문"                    → 단답형
  --item "choice:질문|옵션1|옵션2"   → 객관식(라디오)
  --item "checkbox:질문|옵션1|옵션2"  → 복수 선택
  --item "scale:질문|1|5|최저|최고"  → 선형 배율
  --from-json survey.json     → JSON 파일에서 문항 로드
"""

import argparse
import base64
import json
import sys
from email.mime.text import MIMEText
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VAULT_ROOT = SCRIPT_DIR.parent.parent

# 설문 생성 + (선택) Gmail 발송용
SCOPES_FORMS = ["https://www.googleapis.com/auth/forms.body"]
SCOPES_GMAIL_SEND = ["https://www.googleapis.com/auth/gmail.send"]


def get_credentials(need_gmail_send: bool = False):
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError:
        print("필요 패키지: pip install -r requirements-forms.txt", file=sys.stderr)
        sys.exit(1)

    SCOPES = SCOPES_FORMS + (SCOPES_GMAIL_SEND if need_gmail_send else [])
    token_path = SCRIPT_DIR / "token_forms.json"
    creds_path = SCRIPT_DIR / "credentials.json"
    if not creds_path.exists():
        fallback = SCRIPT_DIR.parent / "이메일 스크랩" / "credentials.json"
        creds_path = fallback if fallback.exists() else creds_path
    if not creds_path.exists():
        print("credentials.json을 이 폴더에 넣어주세요.", file=sys.stderr)
        sys.exit(1)

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    # Gmail 발송이 필요한데 기존 토큰에 gmail.send 권한이 없으면 재인증
    if need_gmail_send and creds and getattr(creds, "scopes", None):
        if "https://www.googleapis.com/auth/gmail.send" not in (creds.scopes or []):
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds


def _item_to_create_request(spec: dict, index: int) -> dict:
    """문항 스펙 하나를 Forms API createItem 요청으로 변환."""
    title = (spec.get("title") or "").strip()
    if not title:
        return None
    q = {"required": spec.get("required", False)}

    if spec.get("type") == "text" or "textQuestion" in spec:
        q["textQuestion"] = {"paragraph": spec.get("paragraph", False)}
    elif spec.get("type") == "choice" or "choiceQuestion" in spec:
        opts = spec.get("options") or spec.get("choiceQuestion", {}).get("options", [])
        if isinstance(opts[0], str) if opts else False:
            opts = [{"value": o} for o in opts]
        q["choiceQuestion"] = {
            "type": "RADIO",
            "options": opts,
        }
    elif spec.get("type") == "checkbox":
        opts = spec.get("options", [])
        if isinstance(opts[0], str) if opts else False:
            opts = [{"value": o} for o in opts]
        q["choiceQuestion"] = {
            "type": "CHECKBOX",
            "options": opts,
        }
    elif spec.get("type") == "scale":
        low = int(spec.get("low", 1))
        high = int(spec.get("high", 5))
        q["scaleQuestion"] = {
            "low": low,
            "high": high,
            "lowLabel": spec.get("lowLabel", ""),
            "highLabel": spec.get("highLabel", ""),
        }
    else:
        q["textQuestion"] = {"paragraph": False}

    return {
        "createItem": {
            "item": {
                "title": title,
                "questionItem": {"question": q},
            },
            "location": {"index": index},
        }
    }


def _parse_item_string(s: str) -> dict:
    """--item "type:payload" 또는 "choice:제목|옵션1|옵션2" 형태 파싱."""
    s = (s or "").strip()
    if not s:
        return None
    if ":" not in s:
        return {"type": "text", "title": s}
    typ, rest = s.split(":", 1)
    typ = typ.strip().lower()
    if typ == "text":
        return {"type": "text", "title": rest.strip()}
    if typ == "choice":
        parts = [p.strip() for p in rest.split("|") if p.strip()]
        if not parts:
            return None
        return {"type": "choice", "title": parts[0], "options": parts[1:]}
    if typ == "checkbox":
        parts = [p.strip() for p in rest.split("|") if p.strip()]
        if not parts:
            return None
        return {"type": "checkbox", "title": parts[0], "options": parts[1:]}
    if typ == "scale":
        parts = [p.strip() for p in rest.split("|") if p.strip()]
        if len(parts) < 3:
            return None
        title = parts[0]
        low, high = int(parts[1]), int(parts[2])
        low_label = parts[3] if len(parts) > 3 else ""
        high_label = parts[4] if len(parts) > 4 else ""
        return {
            "type": "scale",
            "title": title,
            "low": low,
            "high": high,
            "lowLabel": low_label,
            "highLabel": high_label,
        }
    return {"type": "text", "title": rest.strip()}


def create_form(service, title: str, items: list) -> dict:
    """items: [ {"type": "text"|"choice"|"checkbox"|"scale", "title": "...", ... }, ... ]"""
    body = {"info": {"title": title}}
    create_result = service.forms().create(body=body).execute()
    form_id = create_result["formId"]

    if not items:
        form = service.forms().get(formId=form_id).execute()
        return {"formId": form_id, "responderUri": form.get("responderUri", "")}

    requests = []
    idx = 0
    for it in items:
        if isinstance(it, str):
            it = {"type": "text", "title": it}
        req = _item_to_create_request(it, idx)
        if req:
            requests.append(req)
            idx += 1

    if requests:
        service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

    form = service.forms().get(formId=form_id).execute()
    return {
        "formId": form.get("formId", form_id),
        "responderUri": form.get("responderUri", ""),
    }


def send_survey_link_by_gmail(creds, response_url: str, title: str, to_emails: list, from_email: str = "chris@proby.io") -> None:
    """Gmail API로 설문 응답 링크를 지정한 수신자들에게 발송. 발신자는 로그인한 계정(chris@proby.io 등)으로 표시됨."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("Gmail 발송 실패: google-api-python-client 필요", file=sys.stderr)
        return

    body_text = f"""안녕하세요,

아래 설문에 참여해 주시면 감사하겠습니다.

설문 제목: {title}
응답 링크: {response_url}

감사합니다.
"""
    gmail = build("gmail", "v1", credentials=creds)
    for to in to_emails:
        to_addr = to.strip()
        if not to_addr or "@" not in to_addr:
            continue
        # 한 명씩 보내기 (To 필드는 한 주소만)
        single = MIMEText(body_text, "plain", "utf-8")
        single["To"] = to_addr
        single["Subject"] = f"[설문] {title}"
        single["From"] = from_email
        raw_single = base64.urlsafe_b64encode(single.as_bytes()).decode().rstrip("=")
        gmail.users().messages().send(userId="me", body={"raw": raw_single}).execute()
        print(f"발송 완료: {to_addr}")
    return


def main():
    parser = argparse.ArgumentParser(description="Google Form 생성 (문항 타입 지원)")
    parser.add_argument("title", help="설문 제목")
    parser.add_argument("-q", "--question", action="append", dest="questions", default=[], help="단답형 질문")
    parser.add_argument(
        "--item",
        action="append",
        dest="items",
        default=[],
        help='문항: choice:제목|옵션1|옵션2 / checkbox:제목|옵션1|옵션2 / scale:제목|1|5|최저|최고',
    )
    parser.add_argument("--from-json", dest="from_json", metavar="FILE", help="JSON 파일에서 문항 로드 (items 배열)")
    parser.add_argument(
        "--send-to",
        dest="send_to",
        metavar="EMAILS",
        default="",
        help="쉼표 구분 수신자 이메일. 지정 시 설문 응답 링크를 해당 주소로 Gmail 발송 (발신: 로그인한 계정)",
    )
    args = parser.parse_args()

    if args.from_json:
        path = Path(args.from_json)
        if not path.is_absolute():
            path = VAULT_ROOT / path
        data = json.loads(path.read_text(encoding="utf-8"))
        title = data.get("title") or args.title
        items = data.get("items", [])
    else:
        title = args.title
        items = []
        for q in args.questions or []:
            items.append({"type": "text", "title": q})
        for s in args.items or []:
            it = _parse_item_string(s)
            if it:
                items.append(it)

    need_send = bool((args.send_to or "").strip())
    creds = get_credentials(need_gmail_send=need_send)
    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("필요 패키지: pip install google-api-python-client", file=sys.stderr)
        sys.exit(1)

    service = build("forms", "v1", credentials=creds)
    result = create_form(service, title, items)

    form_id = result["formId"]
    edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"
    response_url = result.get("responderUri") or f"https://docs.google.com/forms/d/{form_id}/viewform"

    print("생성 완료.")
    print(f"편집: {edit_url}")
    print(f"응답: {response_url}")

    if need_send:
        to_list = [e.strip() for e in args.send_to.split(",") if e.strip() and "@" in e]
        if to_list:
            send_survey_link_by_gmail(creds, response_url, title, to_list)
        else:
            print("--send-to에 유효한 이메일이 없어 발송하지 않았습니다.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
