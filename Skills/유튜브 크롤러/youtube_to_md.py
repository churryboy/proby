import os
import re
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)


def extract_video_id(url: str) -> str:
    """
    다양한 형태의 YouTube URL에서 video_id를 추출합니다.
    예)
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    if "v" in qs:
        return qs["v"][0]

    # /watch, /embed, /shorts, /VIDEO_ID 등 처리
    path = parsed.path.rstrip("/")
    if "/" in path:
        return path.split("/")[-1]
    return path


def get_vault_root() -> Path:
    """
    Obsidian vault의 루트 디렉터리를 반환합니다.
    - 우선순위: 환경변수 OBSIDIAN_VAULT_PATH -> 현재 작업 디렉터리
    """
    env_path = os.getenv("OBSIDIAN_VAULT_PATH")
    if env_path:
        return Path(env_path)
    return Path.cwd()


def seconds_to_timestamp(sec: float) -> str:
    s = int(sec)
    h, m = divmod(s, 3600)
    m, s = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def fetch_title(url: str) -> str:
    """
    YouTube HTML에서 <title> 태그를 파싱해 동영상 제목을 가져옵니다.
    뒤에 붙는 ' - YouTube' 꼬리는 제거합니다.
    """
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    m = re.search(r"<title>(.*?)</title>", resp.text, re.S | re.I)
    title = m.group(1).strip() if m else "youtube_video"

    # 끝에 붙는 ' - YouTube' 제거
    suffix = " - YouTube"
    if title.endswith(suffix):
        title = title[: -len(suffix)].rstrip()

    return title


def title_to_filename(title: str) -> str:
    """
    파일 시스템에 안전한 파일명으로 변환합니다.
    """
    safe = re.sub(r'[\\/*?:"<>|]', "_", title)
    safe = safe.strip()
    return f"{safe}.md" if not safe.endswith(".md") else safe


def transcript_to_text(transcript_items, max_chars: int = 12000) -> str:
    """
    LLM 입력용으로 타임스탬프 제거한 순수 텍스트를 생성합니다.
    너무 길어질 경우 max_chars 기준으로 잘라냅니다.
    """
    pieces: list[str] = []
    total = 0
    for item in transcript_items:
        text = item["text"].replace("\n", " ").strip()
        if not text:
            continue
        if total + len(text) > max_chars:
            remaining = max_chars - total
            if remaining <= 0:
                break
            pieces.append(text[:remaining])
            break
        pieces.append(text)
        total += len(text)
    return " ".join(pieces)


def load_strategy_context(max_chars: int = 8000) -> str:
    """
    전략수립 담당 폴더 내 주요 문서를 읽어 Proby 전략 컨텍스트를 구성합니다.
    """
    vault_root = get_vault_root()
    strategy_dir = vault_root / "10. 전략팀" / "전략수립 담당"
    if not strategy_dir.exists():
        return ""

    parts: list[str] = []
    total = 0

    for path in sorted(strategy_dir.glob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue

        header = f"# [Strategy Doc] {path.name}\n\n"
        chunk = header + content.strip() + "\n\n"

        if total + len(chunk) > max_chars:
            remaining = max_chars - total
            if remaining <= 0:
                break
            parts.append(chunk[:remaining])
            break

        parts.append(chunk)
        total += len(chunk)

    return "\n".join(parts)


def load_llm_client():
    """
    Anthropic 클라이언트를 초기화합니다. 실패 시 (키 없음/라이브러리 없음 등) None 반환.
    """
    try:
        from dotenv import load_dotenv

        script_dir = Path(__file__).resolve().parent
        env_candidates = [
            script_dir / ".env",
            script_dir.parent / ".env",
            script_dir.parent.parent / ".env",
            get_vault_root() / ".env",
            Path.cwd() / ".env",
        ]

        for env_path in env_candidates:
            if env_path and env_path.exists():
                load_dotenv(dotenv_path=str(env_path))
                break
    except Exception:
        # dotenv가 없어도 조용히 무시
        pass

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set; skipping LLM insight generation.")
        return None

    try:
        from anthropic import Anthropic
    except Exception as e:
        print(f"Anthropic client not available ({e}); skipping LLM insight generation.")
        return None

    return Anthropic(api_key=api_key)


def generate_llm_insights(url: str, transcript_items) -> str:
    """
    Anthropic LLM을 호출해 두 가지를 생성합니다:
    - Key insight / summary
    - Key implications for Proby platform (전략수립 담당 문서 기반)
    """
    client = load_llm_client()
    if client is None:
        return (
            "## Key insight / summary\n"
            "*LLM 요약 생성 실패: ANTHROPIC_API_KEY 또는 anthropic 패키지를 확인해주세요.*\n\n"
            "## Key implications for Proby platform\n"
            "*LLM 요약 생성 실패로 인해 Proby 시사점 섹션을 생성하지 못했습니다.*\n"
        )

    transcript_text = transcript_to_text(transcript_items)
    strategy_context = load_strategy_context()

    model_names = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-sonnet-4-20250514",
    ]

    base_prompt = f"""You are an AI strategy analyst for Proby, an AI-driven user research platform.

Below is the (possibly truncated) transcript of a single YouTube talk or interview.
Use it as the primary source to extract the key ideas.

<TRANSCRIPT>
{transcript_text}
</TRANSCRIPT>

Below is a collection of internal strategy documents about the Proby platform.
Use this as context to reason about how the talk's ideas connect to Proby's product and strategy.
If this section is empty, rely on your general understanding of B2B SaaS and AI user research instead.

<PROBY_STRATEGY_DOCS>
{strategy_context}
</PROBY_STRATEGY_DOCS>

Please respond in Korean.

Write your answer in **Markdown** with the following structure only:

## Key insight / summary

- 컨텐츠에서 가장 중요한 메시지, 프레임워크, 마인드셋, 배운 점을 5~10개 불릿으로 요약
- 필요한 경우, 짧은 맥락 설명을 괄호로 덧붙이기

## Key implications for Proby platform

- Proby의 현재/미래 제품 방향, 기능 설계, GTM에 어떤 시사점이 있는지 5~10개 불릿으로 정리
- 각 불릿에는 꼭 \"그래서 Proby는 무엇을 해야 하는가\" 관점의 구체적인 액션 또는 설계 아이디어를 포함
- 가능하면 위 전략 문서에 등장하는 개념, 포지셔닝, 타겟 세그먼트와 연결 지어 설명

URL (참고용): {url}
"""

    messages = [{"role": "user", "content": base_prompt}]

    for model_name in model_names:
        try:
            print(f"  Trying LLM model for YouTube note: {model_name}")
            message = client.messages.create(
                model=model_name,
                max_tokens=4000,
                messages=messages,
            )
            text = message.content[0].text
            print(f"  Successfully generated LLM insights with {model_name}")
            return text.strip() + "\n\n"
        except Exception as e:
            error_str = str(e)
            if "not_found_error" in error_str or "404" in error_str:
                print(f"  Model {model_name} not found, trying next...")
                continue
            print(f"  LLM insight generation failed with {model_name}: {e}")
            # 다음 모델 시도
            continue

    print("LLM insight generation failed: No available model found.")
    return (
        "## Key insight / summary\n"
        "*LLM 요약 생성 실패: 사용 가능한 Anthropic 모델을 찾지 못했습니다.*\n\n"
        "## Key implications for Proby platform\n"
        "*LLM 요약 생성 실패: 사용 가능한 Anthropic 모델을 찾지 못했습니다.*\n"
    )


def build_markdown(url: str, transcript_items, insights_md: str) -> str:
    """
    상단에 LLM 기반 인사이트 블록을 붙이고, 하단에 타임스탬프 포함 transcript를 붙입니다.
    """
    lines: list[str] = []

    # 1) LLM 기반 인사이트
    if insights_md:
        lines.append(insights_md.rstrip())
        lines.append("")

    # 2) Transcript 섹션
    lines.append("## Transcript")
    lines.append(f"- **URL**: {url}")
    lines.append("")

    for item in transcript_items:
        ts = seconds_to_timestamp(item["start"])
        text = item["text"].replace("\n", " ").strip()
        if not text:
            continue
        lines.append(f"- [{ts}] {text}")

    return "\n".join(lines) + "\n"


def fetch_transcript(video_id: str):
    """
    가능한 언어 조합(한국어, 영어)으로 자막을 가져옵니다.
    """
    # 우선순위: 한국어 → 영어 → 자동 번역
    language_prefs = [
        ["ko"],
        ["ko", "en"],
        ["en"],
    ]

    last_error = None

    api = YouTubeTranscriptApi()

    for langs in language_prefs:
        try:
            fetched = api.fetch(video_id, languages=langs)
            # 최신 버전에서는 FetchedTranscript 객체를 반환하므로
            # 기존 dict 리스트 형태와 맞추기 위해 to_raw_data() 사용
            return fetched.to_raw_data()
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            last_error = e
            continue

    # 마지막 에러 다시 던지기
    if last_error:
        raise last_error


def youtube_to_markdown(url: str, out_path: str):
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("유효한 YouTube URL이 아닙니다.")

    transcript = fetch_transcript(video_id)

    print("Generating LLM insights for this YouTube content...")
    insights_md = generate_llm_insights(url, transcript)

    md_content = build_markdown(url, transcript, insights_md)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md_content)


def main():
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python3 youtube_to_md.py <youtube_url> [output.md]")
        print()
        print("예시:")
        print('  python3 youtube_to_md.py "https://www.youtube.com/watch?v=4uzGDAoNOZc"')
        print('  python3 youtube_to_md.py "https://www.youtube.com/watch?v=4uzGDAoNOZc" "my_note.md"')
        sys.exit(1)

    url = sys.argv[1]

    if len(sys.argv) >= 3:
        # 사용자가 직접 지정한 경로를 그대로 사용
        out_path = sys.argv[2]
    else:
        # 기본 저장 위치:
        #   <OBSIDIAN_VAULT_PATH>/10. 전략팀/리서치 애널리스트/컨텐츠분석/<유튜브제목>.md
        vault_root = get_vault_root()
        target_dir = (
            vault_root / "10. 전략팀" / "리서치 애널리스트" / "컨텐츠분석"
        )
        target_dir.mkdir(parents=True, exist_ok=True)

        title = fetch_title(url)
        filename = title_to_filename(title)
        out_path = target_dir / filename

    try:
        youtube_to_markdown(url, out_path)
        print(f"저장 완료: {out_path}")
    except TranscriptsDisabled:
        print("❌ 이 영상은 자막(트랜스크립트)이 비활성화되어 있습니다.")
        print("   → 이 경우에는 yt-dlp + Whisper 조합으로 음성 인식이 필요합니다.")
        sys.exit(1)
    except NoTranscriptFound:
        print("❌ 이 영상에 사용할 수 있는 자막을 찾을 수 없습니다.")
        print("   → 이 경우에는 yt-dlp + Whisper 조합으로 음성 인식이 필요합니다.")
        sys.exit(1)
    except Exception as e:
        print(f"에러 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
