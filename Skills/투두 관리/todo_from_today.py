#!/usr/bin/env python3
"""
AI-powered Todo Generator
Analyzes Today Actual notes and generates Tomorrow's prioritized todos using Claude AI.
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from typing import List, Optional
from dotenv import load_dotenv
import anthropic

# Import Path Abstraction Layer
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from vault_path import (
    get_vault_root,
    get_file_path,
    get_latest_file_by_date,
    extract_date_from_path
)

# Load .env file directly (bypass dotenv issues)
script_dir = Path(__file__).parent.parent  # 프로젝트 루트로 이동
env_path = script_dir / ".env"

def load_env_file(env_file):
    """Directly parse .env file and set environment variables."""
    if not env_file.exists():
        return {}
    
    env_vars = {}
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                env_vars[key] = value
                os.environ[key] = value  # Set immediately
    return env_vars

# Load .env file
load_env_file(env_path)

# Keep OBSIDIAN_VAULT_PATH for backward compatibility
OBSIDIAN_VAULT_PATH = str(get_vault_root())

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

TODAY = datetime.now().date()


@dataclass
class RevenueStatus:
    goal: int
    current: int
    remaining: int
    days_left: int
    end_date: date
    required_per_day: float
    source_rel_path: Optional[str] = None


@dataclass
class TodayActionStats:
    total_actions: int = 0
    revenue_actions: int = 0
    sample_actions: List[str] = None
    
    def __post_init__(self):
        if self.sample_actions is None:
            self.sample_actions = []


REVENUE_KEYWORDS = [
    "매출", "revenue", "세일즈", "sales", "영업", "고객",
    "클라이언트", "계약", "구독", "결제", "invoice", "구매", "판매"
]


def is_revenue_related(text: str) -> bool:
    lower = text.lower()
    return any(kw in text or kw in lower for kw in REVENUE_KEYWORDS)


def parse_revenue_from_content(content: str) -> Optional[int]:
    """Parse revenue from Current Revenue.md content."""
    # Find all numbers with "원" or "만원"
    money_pattern = re.compile(r"(\d[\d,]*)\s*(원|만원|만\s*원|만)?")
    candidates = []
    
    lines = content.split('\n')
    for line in lines:
        if any(kw in line for kw in ["매출", "revenue", "Revenue", "누적", "합계"]):
            for match in money_pattern.finditer(line):
                num_str = match.group(1).replace(",", "")
                unit = match.group(2) or ""
                try:
                    base = int(num_str)
                    if "만" in unit:
                        value = base * 10_000
                    else:
                        value = base
                    if value >= 10_000:  # Filter small numbers
                        candidates.append(value)
                except ValueError:
                    continue
    
    # Sum all monthly revenues (format: "2025-12 매출 : 770,000원")
    monthly_pattern = re.compile(r"(\d{4}-\d{2})\s*매출\s*[:：]\s*(\d[\d,]*)\s*원")
    monthly_total = 0
    for match in monthly_pattern.finditer(content):
        num_str = match.group(2).replace(",", "")
        try:
            monthly_total += int(num_str)
        except ValueError:
            continue
    
    if monthly_total > 0:
        return monthly_total
    
    return max(candidates) if candidates else None


def get_revenue_status() -> Optional[RevenueStatus]:
    """Get revenue status from Current Revenue.md using path abstraction."""
    vault_root = get_vault_root()
    
    # Use logical name to get revenue file
    revenue_file = get_file_path("revenue_current", must_exist=True)
    
    if not revenue_file or not revenue_file.exists():
        return None
    
    content = revenue_file.read_text(encoding='utf-8')
    current = parse_revenue_from_content(content) or 0
    
    goal = 10_000_000  # 1천만원
    end_feb = date(TODAY.year if TODAY.month <= 2 else TODAY.year + 1, 3, 1) - timedelta(days=1)
    days_left = max((end_feb - TODAY).days + 1, 0)
    remaining = max(goal - current, 0)
    required_per_day = float(remaining) / days_left if days_left > 0 else 0.0
    
    try:
        rel_path = str(revenue_file.relative_to(vault_root))
    except ValueError:
        rel_path = str(revenue_file)
    
    return RevenueStatus(
        goal=goal,
        current=current,
        remaining=remaining,
        days_left=days_left,
        end_date=end_feb,
        required_per_day=required_per_day,
        source_rel_path=rel_path,
    )


def analyze_today_actions(actual_content: str) -> TodayActionStats:
    """Analyze today's actual actions."""
    stats = TodayActionStats()
    
    lines = actual_content.split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Check for bullet points
        if re.match(r'^\s*[-*]\s+', line):
            text = re.sub(r'^\s*[-*]\s+', '', line).strip()
            if text:
                stats.total_actions += 1
                if is_revenue_related(text):
                    stats.revenue_actions += 1
                if len(stats.sample_actions) < 5:
                    stats.sample_actions.append(text)
    
    return stats


def get_latest_actual_note():
    """Find the latest file in 00. Todo/Actual folder using path abstraction."""
    vault_root = get_vault_root()
    
    # Use logical name to get actual folder
    actual_folder = get_file_path("todo_actual_folder", must_exist=True)
    
    if not actual_folder or not actual_folder.exists():
        # Debug: list what folders actually exist
        print(f"[DEBUG] Vault path: {vault_root}")
        if vault_root.exists():
            print(f"[DEBUG] Top-level folders in vault:")
            for item in sorted(vault_root.iterdir()):
                if item.is_dir():
                    print(f"  - {item.name}/")
        raise FileNotFoundError(
            f"Actual folder not found. Please check if 'todo_actual_folder' is correctly configured in vault_paths.json"
        )
    
    files = list(actual_folder.glob("*.md"))
    if not files:
        raise FileNotFoundError("No markdown files found in Actual folder")
    
    # Use vault_path utility to get latest file by date
    latest_file = get_latest_file_by_date(files)
    if latest_file:
        return latest_file
    
    # Fallback to mtime if no date found in filename
    return max(files, key=lambda p: p.stat().st_mtime)


def generate_todos_with_claude(actual_content: str, revenue: Optional[RevenueStatus], stats: TodayActionStats):
    """Call Claude API to generate tomorrow's todos."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Build revenue context
    revenue_context = ""
    if revenue:
        revenue_context = f"""
Revenue Goal Status:
- 목표 매출(2월 말까지): {revenue.goal:,}원
- 현재 누적 매출: {revenue.current:,}원
- 남은 매출: {revenue.remaining:,}원
- 남은 일수: {revenue.days_left}일
- 일별 필요 매출: 약 {int(revenue.required_per_day):,}원/일
"""
    else:
        revenue_context = "Revenue information not found. Assume goal is 10M KRW by end of February 2026."
    
    # Build today actions analysis
    actions_context = f"""
Today's Actions Analysis:
- 총 행동 수: {stats.total_actions}개
- 매출 관련 행동 수: {stats.revenue_actions}개
- 매출 관련 비율: {(stats.revenue_actions/stats.total_actions*100) if stats.total_actions > 0 else 0:.1f}%
"""
    
    prompt = f"""당신은 스타트업 대표의 업무 비서입니다. 오늘 실제로 수행한 행동 기록을 보고, 내일 해야 할 구체적인 액션 아이템을 생성해주세요.

<today_actual>
{actual_content}
</today_actual>

{revenue_context}

{actions_context}

**중요**: 위 Today 기록은 '진단 자료'로만 사용하고, **'2월 말까지 1,000만원 매출 달성'이라는 목표에 가장 적합한 이상적인 계획으로 설계**해주세요. Today에서 한 행동이 부족하거나 방향이 어긋났다면, **과감하게 다른 행동을 제안**해도 됩니다.

위 Today 기록을 분석해서, **내일 해야 할 Task와 세부 액션**을 다음 기준으로 생성해주세요:

1. **사업 관련 (Business) Task 3개**:
   - 미팅 후속 연락/제안
   - 고객 연락/세일즈 액션
   - 콘텐츠 반응 확인/후속 콘텐츠
   - 제품/툴 피드백 수집
   - 직접 매출로 이어질 수 있는 행동

2. **전략 관련 (Strategy) Task 3개**:
   - 데이터 분석/정리
   - 프로세스 개선/문서화
   - 시장/경쟁사 리서치
   - 중장기 기획/로드맵

**중요**: 각 Task는 큰 목표(30-50자)이고, 그 아래에 **구체적인 실행 액션(subtodos) 3~5개**를 생성해주세요.

다음 JSON 형식으로 응답해주세요:
{{
  "business_todos": [
    {{
      "task": "메인 Task (30-50자)",
      "subtodos": ["세부 액션 1", "세부 액션 2", "세부 액션 3", ...],
      "priority": 1-10
    }},
    ...
  ],
  "strategy_todos": [
    {{
      "task": "메인 Task (30-50자)",
      "subtodos": ["세부 액션 1", "세부 액션 2", "세부 액션 3", ...],
      "priority": 1-10
    }},
    ...
  ]
}}"""
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )
    
    response_text = message.content[0].text.strip()
    
    # Parse JSON (handle code blocks)
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    response_text = response_text.strip()
    
    return json.loads(response_text)


def build_today_review(revenue: Optional[RevenueStatus], stats: TodayActionStats) -> str:
    """Build Today review & diagnosis section."""
    lines = ["## 1. Today review & diagnosis", ""]
    
    if revenue:
        lines.extend([
            f"- **목표 매출(2월 말까지)**: {revenue.goal:,}원",
            f"- **현재 누적 매출**: {revenue.current:,}원",
            f"- **남은 매출**: {revenue.remaining:,}원",
            f"- **남은 일수당 필요 매출**: 약 {int(revenue.required_per_day):,}원/일 (마감: {revenue.end_date.isoformat()})",
            "",
        ])
        if revenue.source_rel_path:
            base, _ = os.path.splitext(revenue.source_rel_path)
            lines.append(f"- **매출 데이터 원본**: [[{base}]]")
            lines.append("")
    
    # Diagnosis
    lines.append("")
    if revenue and revenue.remaining > 0:
        revenue_ratio = (stats.revenue_actions / stats.total_actions * 100) if stats.total_actions > 0 else 0
        if stats.total_actions == 0:
            lines.append(
                "오늘은 00. Todo/Actual에 기록된 행동이 거의 없습니다. "
                "목표 달성까지 남은 기간을 고려하면, 하루 단위로 **실제 실행한 행동을 빠짐없이 기록**하는 것이 좋습니다."
            )
        elif revenue_ratio < 20:
            lines.append(
                "Today 기록을 보면, 대부분의 행동이 정리·리서치·준비에 치우쳐 있고 "
                "**직접 매출에 연결되는 행동(콜, 제안, 견적, DM 등)의 비중이 20% 미만**입니다. "
                "2월 말까지 목표 매출을 달성하려면, 내일은 '수익을 바로 만들 수 있는 행동'의 비율을 의도적으로 끌어올릴 필요가 있습니다."
            )
        elif revenue_ratio < 50:
            lines.append(
                "오늘 행동 중 일부는 매출과 직접 연결되어 있지만, 여전히 절반 이상은 간접 활동(준비·정리·리서치)에 머물러 있습니다. "
                "내일은 **가장 매출 임팩트가 큰 채널/오퍼를 하나 정하고, 그쪽 행동을 조금 더 과감하게 늘리는 것**이 좋겠습니다."
            )
        else:
            lines.append(
                "Today 행동 기록을 보면, **매출과 직접 연결되는 행동 비중이 비교적 높은 편**입니다. "
                "내일은 오늘과 비슷한 패턴을 유지하되, 성과가 좋았던 채널/메시지를 중심으로 반복·확대하는 것이 좋겠습니다."
            )
    elif revenue and revenue.remaining == 0:
        lines.append(
            "2월 목표 매출을 이미 달성했습니다. 오늘 행동은 **성과 유지 및 재사용 가능한 자산(템플릿, 프로세스)**으로 "
            "정리하는 데 초점을 맞추면 좋습니다."
        )
    else:
        lines.append(
            "50. Revenue 폴더에서 명확한 누적 매출 데이터를 찾지 못했습니다. "
            "우선 **현재까지의 매출 현황을 한 페이지에 정리**하는 것이 좋습니다."
        )
    
    if stats.sample_actions:
        lines.append("")
        lines.append("예시 Today 노트에 적힌 문장 (오늘 작성한 내용 일부, 과거 날짜 언급 포함):")
        for action in stats.sample_actions:
            lines.append(f"- {action}")
    
    return "\n".join(lines)


def save_proposed_todos(todos_data: dict, revenue: Optional[RevenueStatus], stats: TodayActionStats):
    """Save generated todos to Proposed folder using path abstraction."""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Use logical name to get proposed folder
    proposed_folder = get_file_path("todo_proposed_folder")
    
    # If not found, create it
    if not proposed_folder:
        vault_root = get_vault_root()
        proposed_folder = vault_root / "Laptop" / "00. Todo" / "Proposed"
    
    proposed_folder.mkdir(parents=True, exist_ok=True)
    
    filename = f"{tomorrow} - Proposed Todos.md"
    filepath = proposed_folder / filename
    
    # Build content
    today_review = build_today_review(revenue, stats)
    
    tomorrow_actions = ["## 2. Tomorrow actions", ""]
    
    task_idx = 1
    business_todos = todos_data.get("business_todos", [])[:3]
    strategy_todos = todos_data.get("strategy_todos", [])[:3]
    
    if business_todos:
        tomorrow_actions.append(f"{task_idx}. **사업 관련 (Business)**")
        for todo in business_todos:
            tomorrow_actions.append(f"   - **{todo.get('task', '')}**")
            for subtodo in todo.get('subtodos', []):
                tomorrow_actions.append(f"     - {subtodo}")
        task_idx += 1
    
    if strategy_todos:
        tomorrow_actions.append("")
        tomorrow_actions.append(f"{task_idx}. **전략 관련 (Strategy)**")
        for todo in strategy_todos:
            tomorrow_actions.append(f"   - **{todo.get('task', '')}**")
            for subtodo in todo.get('subtodos', []):
                tomorrow_actions.append(f"     - {subtodo}")
    
    content = f"""# Proposed Todos for {tomorrow}

_Based on notes updated on **{TODAY.isoformat()}** in this vault._

{today_review}

{chr(10).join(tomorrow_actions)}
"""
    
    filepath.write_text(content, encoding='utf-8')
    return filepath


def main():
    """Main function."""
    print("[INFO] Starting todo generator...")
    print(f"[DEBUG] Using vault path: {get_vault_root()}")
    
    # Read latest actual note
    actual_file = get_latest_actual_note()
    print(f"[INFO] Reading latest Actual note: {actual_file.name}")
    actual_content = actual_file.read_text(encoding='utf-8')
    
    # Analyze today's actions
    stats = analyze_today_actions(actual_content)
    print(f"[INFO] Today actions: {stats.total_actions} total, {stats.revenue_actions} revenue-related")
    
    # Get revenue status
    revenue = get_revenue_status()
    if revenue:
        print(f"[INFO] Revenue: {revenue.current:,}원 / {revenue.goal:,}원 (remaining: {revenue.remaining:,}원)")
    else:
        print("[WARNING] Revenue information not found")
    
    # Generate todos with Claude
    print("[INFO] Calling Claude to generate tomorrow's todos...")
    todos_data = generate_todos_with_claude(actual_content, revenue, stats)
    
    # Save to Proposed folder
    output_file = save_proposed_todos(todos_data, revenue, stats)
    print(f"[INFO] Saved proposed todos to: {output_file}")
    
    # Display summary
    business_count = len(todos_data.get("business_todos", []))
    strategy_count = len(todos_data.get("strategy_todos", []))
    print(f"[INFO] Generated {business_count} business + {strategy_count} strategy tasks")


if __name__ == "__main__":
    main()
