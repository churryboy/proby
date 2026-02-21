#!/usr/bin/env python3
"""
News Crawler for Market Research
Collects news about market research companies and saves to Obsidian vault.
Generates LLM-based summaries and aggregates all articles into a single markdown file.
"""

import os
import re
import sys
import textwrap
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from pathlib import Path

import requests
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

# Import Path Abstraction Layer
try:
    from vault_path import get_vault_root, get_file_path
except ModuleNotFoundError:
    # Fallback: add common parent directories to sys.path so the shared vault_path module is discoverable
    current_dir = Path(__file__).resolve().parent
    candidate_roots = [
        current_dir.parent,
        current_dir.parent.parent,
    ]

    vault_env = os.getenv("OBSIDIAN_VAULT_PATH")
    if vault_env:
        candidate_roots.append(Path(vault_env))
        candidate_roots.append(Path(vault_env) / "Skills")

    for candidate in candidate_roots:
        if not candidate:
            continue
        if (candidate / "vault_path").exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
            break

    from vault_path import get_vault_root, get_file_path

# Companies you want to track specifically
COMPANY_KEYWORDS = [
    "listen labs",
    "outset.ai",
    "conveo.ai",
    "userflix.de",
    "strella.io",
    "maze",
    "qualtrics",
    "survey monkey",
    "surveymonkey",
    "오픈서베이",
    "open survey",
    "한국리서치",
    "엠브레인",
    "embrain",
    "칸타 코리아",
    "kantar korea",
    "입소스 코리아",
    "ipsos korea",
    "kantar",
    "ipsos",
    "typeform",
    "nielsen norman group",
    "nng",
    "ideo",
    "open claw",
]

INVESTOR_KEYWORDS = [
    "y combinator",
    "softbank",
    "softbank vision fund",
    "sequoia capital",
    "sequoia china",
    "andreessen horowitz",
    "a16z",
    "index ventures",
    "battery ventures",
    "benchmark",
    "bessemer venture partners",
    "greylock",
    "accel",
]

# Get vault root
VAULT_ROOT = get_vault_root()

# Keep OBSIDIAN_VAULT_PATH for backward compatibility
OBSIDIAN_VAULT_PATH = str(VAULT_ROOT)

# Subfolder within the vault where notes will be saved (using logical name)
MARKET_RESEARCH_FOLDER = get_file_path("market_research_folder", must_exist=True)
OUTPUT_SUBFOLDER = "10. Strategy/Market Research"  # Fallback if logical name not found

NEWS_FEEDS = [
    # AI 관련 동향 / 신기술 / 투자 (지난 1주일 내)
    "https://news.google.com/rss/search?q=%28AI+OR+%22artificial+intelligence%22%29+%28trend+OR+funding+OR+investment+OR+%22new+technology%22%29&hl=en-US&gl=US&ceid=US:en",
    
    # 특정 회사 관련 기사
    "https://news.google.com/rss/search?q=%22Listen+Labs%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Outset.ai%22+OR+%22Outset+AI%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Conveo.ai%22+OR+%22Conveo+AI%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22userflix.de%22+OR+Userflix&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22strella.io%22+OR+Strella&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Qualtrics&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=SurveyMonkey&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Typeform&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Kantar&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Ipsos&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Nielsen+Norman+Group%22+OR+NNG&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=IDEO+%22design%22+OR+%22design+thinking%22&hl=en-US&gl=US&ceid=US:en",
    
    # Usability testing / User interview / Research 동향
    "https://news.google.com/rss/search?q=%22usability+testing%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22user+interview%22+%28UX+OR+research+OR+%22user+research%22%29&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22AI+moderated+research%22+OR+%22AI+moderated+survey%22+OR+%22AI+user+research%22&hl=en-US&gl=US&ceid=US:en",

    # 주요 투자사 / VC 동향
    "https://news.google.com/rss/search?q=%22Y+Combinator%22+OR+%22YC%22+%22investment%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22SoftBank%22+OR+%22SoftBank+Vision+Fund%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Sequoia+Capital%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Andreessen+Horowitz%22+OR+%22a16z%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Index+Ventures%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Bessemer+Venture+Partners%22+OR+%22Bessemer%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Greylock%22+%28Capital+OR+Partners%29&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Accel%22+%22investment%22&hl=en-US&gl=US&ceid=US:en",
]


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def fetch_article_body(url: str, timeout: int = 10) -> str:
    """Best-effort extraction of article body text from a URL."""
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception:
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")
    candidates = []
    for selector in ["article", "div.article", "div.post", "div.entry-content", "main"]:
        candidates.extend(soup.select(selector))

    if not candidates:
        paragraphs = soup.find_all("p")
    else:
        best = max(candidates, key=lambda c: len(c.get_text(" ", strip=True)))
        paragraphs = best.find_all("p") or [best]

    texts = [normalize_text(p.get_text(" ", strip=True)) for p in paragraphs]
    texts = [t for t in texts if t]
    return "\n\n".join(texts[:40])


def parse_entry_date(entry: Dict[str, Any]) -> datetime:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if value:
            try:
                return date_parser.parse(value)
            except Exception:
                continue
    return datetime.now(timezone.utc)


def detect_topic_hit(title: str, summary: str) -> str:
    """Detect which topic category this article belongs to."""
    text = f"{title} {summary}".lower()
    
    # Company matches
    if "listen labs" in text:
        return "company: listen labs"
    if "outset.ai" in text or "outset ai" in text:
        return "company: outset.ai"
    if "conveo.ai" in text or "conveo ai" in text:
        return "company: conveo.ai"
    if "userflix.de" in text or "userflix" in text:
        return "company: userflix.de"
    if "strella.io" in text or " strella " in text:
        return "company: strella.io"
    if "qualtrics" in text:
        return "company: qualtrics"
    if "surveymonkey" in text or "survey monkey" in text:
        return "company: surveymonkey"
    if "typeform" in text:
        return "company: typeform"
    if "kantar" in text:
        return "company: kantar"
    if "ipsos" in text:
        return "company: ipsos"
    if "nielsen norman group" in text or " nng " in text or "nngroup.com" in text:
        return "company: nielsen norman group"
    if " ideo " in text or text.startswith("ideo "):
        return "company: ideo"
    
    # Investor matches
    for investor in INVESTOR_KEYWORDS:
        if investor in text:
            return f"investor: {investor}"
    
    # Research methodology matches
    if "usability testing" in text:
        return "usability testing"
    if "user interview" in text:
        return "user interview"
    if "user research" in text or "ux research" in text:
        return "user research"
    if "ai moderated research" in text or "ai-moderated research" in text:
        return "user research"
    if "ai moderated survey" in text or "ai-moderated survey" in text:
        return "user research"
    if "ai user research" in text:
        return "user research"
    if "synthetic user" in text:
        return "user research"
    
    # AI general
    if " artificial intelligence" in text or " ai " in text or "generative ai" in text:
        return "ai_general"
    
    return ""


def has_company_in_title(title: str) -> bool:
    """Check if any company keyword appears in the title (not just source)."""
    title_lower = title.lower()
    for keyword in COMPANY_KEYWORDS:
        if keyword.lower() in title_lower:
            return True
    return False


def build_article_section(entry: Dict[str, Any], article_body: str, topic_hit: str) -> str:
    """Build a markdown section for a single article."""
    title = entry.get("title", "Untitled")
    link = entry.get("link", "")
    
    section = f"[{title}]({link})\n---\n"
    return section


def generate_llm_summary_body(clips: List[Dict[str, Any]]) -> str:
    """Use Anthropic LLM to generate topic-based summary."""
    if not clips:
        return ""

    try:
        from dotenv import load_dotenv
        script_dir = Path(__file__).resolve().parent

        env_candidates = [
            script_dir / ".env",
            script_dir.parent / ".env",
            VAULT_ROOT / ".env",
            Path.cwd() / ".env",
        ]

        for env_path in env_candidates:
            if env_path and env_path.exists():
                load_dotenv(dotenv_path=str(env_path))
    except Exception:
        pass

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set; skipping LLM summary.")
        return ""

    try:
        from anthropic import Anthropic
    except Exception as e:
        print(f"Anthropic client not available ({e}); skipping LLM summary.")
        return ""

    # Build article list for prompt
    article_chunks: List[str] = []
    for idx, clip in enumerate(clips, start=1):
        entry = clip.get("entry", {})
        title = entry.get("title", "")
        source = entry.get("source", {}).get("title", "")
        topic_hit = clip.get("topic_hit", "")
        summary_html = entry.get("summary", "")
        summary_text = normalize_text(
            BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True)
        )

        article_chunks.append(
            f"""[{idx}]
Title: {title}
Source: {source}
TopicTag: {topic_hit}
Summary: {summary_text}
"""
        )

    articles_text = "\n".join(article_chunks)

    # Try different model names
    model_names = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-sonnet-4-20250514",
    ]

    client = Anthropic(api_key=api_key)
    prompt = f"""다음은 지난 1주일 동안 수집된 B2B SaaS 시장/경쟁사/리서치/투자사 관련 뉴스 기사들입니다.

각 기사를 다음 4개 섹션으로 분류하고 요약해주세요:
1) AI 동향 - AI 투자, 기술, 트렌드 관련
2) 경쟁사 동향 - Listen Labs, Outset.ai, Conveo.ai, Userflix.de, Strella.io, Qualtrics, SurveyMonkey, Typeform, Kantar, Ipsos, Nielsen Norman Group, IDEO 관련
3) Research 동향 - Usability testing, User interview, UX research, AI moderated research/survey 관련
4) 투자사 동향 - Y Combinator, SoftBank, Sequoia Capital, Andreessen Horowitz(a16z), Index Ventures, Bessemer Venture Partners, Greylock, Accel 등 주요 VC·투자사 관련

각 섹션마다:
- 해당 기사들을 종합하여 6~12문장으로 요약 (10~20문장이 아니라 더 짧게)
- 그 아래 "**Implications**" 소제목으로 3~5개 불릿 포인트로 "그래서 우리에게 어떤 의미인지(So what)" 정리

해당 섹션에 기사가 하나도 없으면 "해당 섹션에 해당하는 기사가 수집되지 않았습니다."라고 한 문장만 쓰고, 짧은 implication 1~2개만 추가.

마크다운 형식으로 작성해주세요:
## AI 동향
...
**Implications**
- ...

## 경쟁사 동향
...
**Implications**
- ...

## Research 동향
...
**Implications**
- ...

## 투자사 동향
...
**Implications**
- ...

기사 목록:
{articles_text}
"""

    for model_name in model_names:
        try:
            print(f"  Trying model: {model_name}")
            message = client.messages.create(
                model=model_name,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
            )
            summary = message.content[0].text
            print(f"  Successfully generated LLM summary with {model_name}")
            return f"\n## Topic-based summary (LLM)\n\n{summary}\n\n"
        except Exception as e:
            error_str = str(e)
            if "not_found_error" in error_str or "404" in error_str:
                print(f"  Model {model_name} not found, trying next...")
                continue
            print(f"  LLM summary generation failed with {model_name}: {e}")
            # Don't return immediately, try next model
    
    print("LLM summary generation failed: No available model found.")
    return ""


def compute_period_label(clips: List[Dict[str, Any]]) -> str:
    """Compute a period label like 'YYYY-MM-DD~MM-DD' based on clip dates."""
    if not clips:
        today = datetime.now(timezone.utc).date()
        return today.strftime("%Y-%m-%d")

    dates = []
    for clip in clips:
        entry = clip.get("entry", {})
        try:
            dt = parse_entry_date(entry)
            dates.append(dt.date())
        except Exception:
            continue

    if not dates:
        today = datetime.now(timezone.utc).date()
        return today.strftime("%Y-%m-%d")

    start = min(dates)
    end = max(dates)
    if start == end:
        return start.strftime("%Y-%m-%d")
    return f"{start.strftime('%Y-%m-%d')}~{end.strftime('%m-%d')}"


def build_daily_summary(clips: List[Dict[str, Any]]) -> str:
    """Build summary block (YAML + prose) for the aggregated daily note."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    period_label = compute_period_label(clips)
    total_clips = len(clips)

    competitor_tags = ("company:",)
    investor_tags = ("investor:",)

    competitor_clips = sum(
        1
        for clip in clips
        if any(str(clip.get("topic_hit", "")).startswith(tag) for tag in competitor_tags)
    )
    investor_clips = sum(
        1
        for clip in clips
        if any(str(clip.get("topic_hit", "")).startswith(tag) for tag in investor_tags)
    )
    ai_ux_clips = total_clips - competitor_clips - investor_clips

    # Count by company
    company_counts: Dict[str, int] = {}
    for clip in clips:
        topic = clip.get("topic_hit", "")
        if topic.startswith("company: "):
            company = topic.replace("company: ", "").lower()
            company_counts[company] = company_counts.get(company, 0) + 1

    # Count by investor
    investor_counts: Dict[str, int] = {}
    for clip in clips:
        topic = clip.get("topic_hit", "")
        if topic.startswith("investor: "):
            investor = topic.replace("investor: ", "").lower()
            investor_counts[investor] = investor_counts.get(investor, 0) + 1

    # Count by topic
    ai_count = sum(1 for clip in clips if clip.get("topic_hit") == "ai_general")
    usability_count = sum(1 for clip in clips if "usability" in clip.get("topic_hit", "").lower())
    user_interview_count = sum(1 for clip in clips if "user interview" in clip.get("topic_hit", "").lower())

    lines = [
        "---",
        f'title: "{period_label} Market Research Summary"',
        f"date: {today_str}",
        f"total_clips: {total_clips}",
        f"competitor_clips: {competitor_clips}",
        f"ai_ux_clips: {ai_ux_clips}",
        f"trackable_metric: {total_clips}",
        f'period: "{period_label}"',
        "---",
        "",
        f"# Market Research Summary ({period_label})",
        "",
        f"- **Trackable metric (오늘 수집된 클리핑 수)**: {total_clips}",
        f"- **경쟁사 관련 기사 수**: {competitor_clips}",
        f"- **투자사 관련 기사 수**: {investor_clips}",
        f"- **AI / Usability / User Research 관련 기사 수**: {ai_ux_clips}",
        "",
        "## Summary",
        "",
        f"오늘은 총 {total_clips}건의 AI·리서치 관련 기사가 수집되었으며, 그 중 경쟁사 직접 관련 기사는 {competitor_clips}건, 주요 VC/투자사 관련 기사는 {investor_clips}건, 그 외 일반 AI·Usability·User Research 관련 기사는 {ai_ux_clips}건입니다.",
        f"토픽 기준으로는 일반 AI 동향/투자 기사가 {ai_count}건, Usability testing 관련 기사가 {usability_count}건, User interview 관련 기사가 {user_interview_count}건 포착되었습니다.",
    ]

    if company_counts:
        lines.append("")
        lines.append("### 경쟁사별 기사 수")
        lines.append("")
        for company, count in sorted(company_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- **{company}**: {count}건")

    if investor_counts:
        lines.append("")
        lines.append("### 투자사별 기사 수")
        lines.append("")
        for investor, count in sorted(investor_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- **{investor}**: {count}건")

    return "\n".join(lines)


def save_daily_markdown(clips: List[Dict[str, Any]], output_dir: str) -> None:
    """Save all clipped articles into a single markdown file with summary at the top."""
    if not clips:
        print("No clips to save.")
        return

    period_label = compute_period_label(clips)
    filename = f"{period_label} - Market Research Clips.md"
    path = os.path.join(output_dir, filename)

    # Build summary
    summary_md = build_daily_summary(clips)

    # Build LLM summary
    print("Generating LLM summary...")
    llm_summary = generate_llm_summary_body(clips)
    if not llm_summary:
        print("WARNING: LLM summary generation failed or returned empty. Check ANTHROPIC_API_KEY and model availability.")
        llm_summary = "\n## Topic-based summary (LLM)\n\n*LLM 요약 생성 실패: ANTHROPIC_API_KEY를 확인하거나 모델 접근 권한을 확인해주세요.*\n\n"

    # Build article sections
    article_sections = [
        build_article_section(clip["entry"], clip.get("article_body", ""), clip.get("topic_hit", ""))
        for clip in clips
    ]

    # Combine everything
    full_content = f"""{summary_md}

{llm_summary}
---

## Articles

{''.join(article_sections)}"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(full_content)

    print(f"Saved aggregated markdown: {path}")


def crawl_feeds(feeds: List[str]) -> List[Dict[str, Any]]:
    """Crawl all feeds and return list of clips."""
    all_clips = []

    for feed_url in feeds:
        print(f"Fetching feed: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"  Failed to parse feed: {e}")
            continue

        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            source = entry.get("source", {}).get("title", "")

            # Filter by date: keep only articles within the past 1 week
            published_dt = parse_entry_date(entry)
            now = datetime.now(timezone.utc)
            if published_dt > now:
                print(f"    Skipping (future date: {published_dt.isoformat()}): {title[:60]}...")
                continue

            if now - published_dt > timedelta(days=7):
                print(f"    Skipping (older than 1 week: {published_dt.isoformat()}): {title[:60]}...")
                continue

            # Filter: company keyword must be in title (not just source)
            topic_hit = detect_topic_hit(title, summary)
            if topic_hit.startswith("company:"):
                if not has_company_in_title(title):
                    print(f"    Skipping (company keyword only/also in source): {title[:60]}...")
                    continue
                # Also skip if source contains company name
                if any(keyword.lower() in source.lower() for keyword in COMPANY_KEYWORDS):
                    print(f"    Skipping (company keyword only/also in source): {title[:60]}...")
                    continue

            print(f"  Clipping: {title}")
            article_body = fetch_article_body(entry.get("link", ""))
            
            all_clips.append({
                "entry": entry,
                "article_body": article_body,
                "topic_hit": topic_hit,
            })

    return all_clips


def main() -> None:
    """Main function."""
    date_folder = datetime.now().strftime("%b-%d-%Y")
    
    # Use logical name for market research folder
    if MARKET_RESEARCH_FOLDER and MARKET_RESEARCH_FOLDER.exists():
        output_dir = MARKET_RESEARCH_FOLDER / date_folder
    else:
        # Fallback to old path construction
        output_dir = VAULT_ROOT / OUTPUT_SUBFOLDER / date_folder
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Saving notes into: {output_dir}")
    
    clips = crawl_feeds(NEWS_FEEDS)
    save_daily_markdown(clips, str(output_dir))


if __name__ == "__main__":
    main()
