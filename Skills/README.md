# Agent Strategy Tools

Two productivity scripts for Obsidian + AI:

1. **News crawler** - Market research news aggregation
2. **Todo generator** - AI-powered daily todo planning

---

## 1. News crawler to Obsidian (market research)

This small script collects news about:

- **market research trend**
- **market research new AI tool**
- **market research funding**

and saves each clipped article as a markdown file into an Obsidian vault folder.

### 1. Install dependencies

From `/Users/churryboy/Desktop/proby-agents`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Point to your Obsidian vault

Decide where in your Obsidian vault you want notes to go, for example:

- **Vault path**: `/Users/you/Documents/Obsidian/MyVault`
- **Subfolder**: `News Clips` (will be created automatically)

You can configure the vault path in either of two ways:

- **Option A – environment variable (recommended)**:

  ```bash
  export OBSIDIAN_VAULT_PATH="/Users/you/Documents/Obsidian/MyVault"
  ```

- **Option B – edit the default in `news_crawler.py`**:

  In `news_crawler.py`, change the fallback value:

  ```python
  OBSIDIAN_VAULT_PATH = os.environ.get(
      "OBSIDIAN_VAULT_PATH",
      "/Users/churryboy/Obsidian/MarketResearch",  # change to your vault path
  )
  ```

### 3. Run the crawler

With the virtual environment activated and `OBSIDIAN_VAULT_PATH` set (or the default edited), run:

```bash
python news_crawler.py
```

Or, for a one-word command, you can use the helper script:

```bash
cd /Users/churryboy/Desktop/proby-agents
./strategy
```

The `strategy` command:

- Activates `.venv` in the project (if present).
- Uses `OBSIDIAN_VAULT_PATH` if already set, otherwise defaults to `/Users/churryboy/Desktop/proby`.
- Runs `news_crawler.py` with the current settings.

The script will:

- **Fetch** several Google News RSS feeds focused only on:
  - **Listen Labs**
  - **Conveo**
  - **Outset**  
  (in a market research / insights context)
- **Filter** items where the title/summary clearly mention one of those companies.
- **Restrict** to articles published in the **last 7 days** (including today) relative to the run date.
- **Fetch the article page** and attempt to extract the main text.
- **Create one `.md` file per article** in a **date-based folder**:
  - `<OBSIDIAN_VAULT_PATH>/News Clips/<MMM-DD-YYYY>/`
  - Example for Feb 2, 2026: `<OBSIDIAN_VAULT_PATH>/News Clips/Feb-02-2026/`

Each note includes:

- **YAML frontmatter** (title, source, URL, clipped time, `topic_match` which is one of `listen labs`, `conveo`, or `outset`, or `generic` if it didn't match cleanly)
- **Summary from the feed**
- **Auto-extracted article body** (if possible)

You can schedule this with `cron` or a task scheduler to keep your Obsidian vault up to date.

---

## 2. AI-powered Todo Generator (`todo_from_today.py`)

Analyzes your **Today Actual** notes and generates **Tomorrow's prioritized action items** using Claude AI.

### Features

- Reads `00. Todo/Actual` (latest note)
- Analyzes `50. Revenue` for revenue tracking
- Uses **Claude Sonnet 4** to generate context-aware todos
- Outputs to `00. Todo/Proposed/<date> - Proposed Todos.md`
- Groups todos into **Business (3)** and **Strategy (3)**
- Provides **Today review & diagnosis** based on revenue goal

### Setup

1. **Get Anthropic API key**:
   - Visit https://console.anthropic.com/
   - Create an API key

2. **Create `.env` file** (copy from `env.example`):
   ```bash
   cp env.example .env
   ```

3. **Edit `.env`**:
   ```bash
   OBSIDIAN_VAULT_PATH="/Users/you/Library/Mobile Documents/iCloud~md~obsidian/Documents/YourVault"
   ANTHROPIC_API_KEY="sk-ant-api03-..."
   ```

4. **Install dependencies** (if not done already):
   ```bash
   pip install -r requirements.txt
   ```

### Usage

```bash
python3 todo_from_today.py
```

**Output example**:
```
[INFO] Reading latest Actual note: 2026-02-04.md
[INFO] Calling Claude to generate tomorrow's todos...
[INFO] Generated 6 LLM-based todos
  - [business] 쿠팡 성민지님에게 AI moderator 데모 + 가격 제안서 이메일 발송 (score: 28)
  - [business] Ridi 미팅 아젠다 5개 작성하고 사전 공유 (score: 27)
  - [strategy] 2월 말까지 남은 865만원 달성을 위한 주간 액션 플랜 작성 (score: 23)
```

### How it works

1. Finds latest file in `00. Todo/Actual`
2. Reads current revenue from `50. Revenue/Current Revenue`
3. Sends context to Claude with prompt:
   - Today's actions
   - Revenue goal (10M KRW by end of Feb)
   - Current status
4. Claude generates 3 business + 3 strategy todos
5. Saves to `00. Todo/Proposed/<tomorrow-date> - Proposed Todos.md`

### Notes for GitHub

- `.env` is git-ignored (never commit API keys!)
- `env.example` is provided as template
- Works with both `OBSIDIAN_VAULT_PATH` env var or code default

---

## 3. Agent Context 자동 상속 시스템

Cursor 에이전트 간 컨텍스트를 자동으로 상속받을 수 있도록 하는 시스템입니다.

### 기능

- **자동 컨텍스트 상속**: 새로운 에이전트가 시작할 때 이전 에이전트의 작업 디렉토리와 컨텍스트를 자동으로 인식
- **작업 디렉토리 추적**: 현재 작업 중인 디렉토리를 자동으로 기록하고 공유
- **컨텍스트 지속성**: 에이전트 세션이 종료되어도 작업 컨텍스트가 유지됨

### 파일 구조

1. **`.cursorrules`** - Cursor가 자동으로 읽는 기본 규칙 파일
   - 프로젝트 구조와 주요 디렉토리 정보
   - 모든 새 에이전트가 `AGENT_CONTEXT.md`를 읽도록 지시

2. **`AGENT_CONTEXT.md`** - 동적 작업 컨텍스트 저장 파일
   - 현재 작업 디렉토리
   - 현재 작업 내용
   - 최근 작업 이력
   - 다음 작업 예정

3. **`update_context.py`** - 컨텍스트 업데이트 스크립트
   - 작업 디렉토리 변경 시 자동 업데이트
   - 명령줄 또는 인터랙티브 모드 지원

### 사용법

#### 기본 사용 (인터랙티브 모드)

```bash
python3 update_context.py
```

프롬프트에 따라:
- 작업 디렉토리 입력
- 작업 내용 설명 입력
- 다음 작업 예정 입력

#### 명령줄 사용

```bash
python3 update_context.py "/Users/churryboy/Desktop/proby-sync/Laptop/50. Revenue/" "매출 추적 및 분석" "매출 목표 달성 현황 확인"
```

#### 에이전트에서 자동 사용

에이전트가 작업 디렉토리를 변경할 때:

```python
# 에이전트가 자동으로 실행할 수 있는 예시
import subprocess
subprocess.run([
    "python3", "update_context.py",
    "/path/to/working/directory",
    "작업 내용 설명",
    "다음 작업 계획"
])
```

### 작동 원리

1. **에이전트 A**가 특정 디렉토리에서 작업 시작
2. `update_context.py`로 현재 작업 디렉토리와 컨텍스트를 `AGENT_CONTEXT.md`에 저장
3. **에이전트 B**가 새로 생성되면:
   - `.cursorrules` 파일을 통해 `AGENT_CONTEXT.md`를 읽도록 지시받음
   - `AGENT_CONTEXT.md`를 읽어서 현재 작업 디렉토리와 컨텍스트를 자동으로 인식
   - 별도 입력 없이 이전 에이전트의 작업을 이어서 진행 가능

### 예시 시나리오

```
1. 에이전트 A: "50. Revenue 폴더에서 매출 분석 작업 중"
   → update_context.py 실행
   → AGENT_CONTEXT.md 업데이트

2. 에이전트 B 생성
   → .cursorrules에 의해 AGENT_CONTEXT.md 자동 읽기
   → "현재 작업 디렉토리: 50. Revenue" 자동 인식
   → 별도 설명 없이 바로 작업 시작 가능
```

### 주의사항

- `AGENT_CONTEXT.md`는 프로젝트 루트에 있어야 합니다
- 작업 디렉토리가 변경되면 반드시 `update_context.py`를 실행하세요
- 중요한 컨텍스트 변경사항은 수동으로 `AGENT_CONTEXT.md`를 편집할 수도 있습니다

---

## 4. 데일리 컨텍스트 로그 시스템

매일 작업 컨텍스트를 날짜별로 기록하는 시스템입니다.

### 기능

- **날짜별 자동 분류**: 각 날짜별로 섹션이 자동으로 생성됩니다
- **중복 업데이트 지원**: 같은 날짜에 여러 번 업데이트하면 해당 날짜 섹션에 추가됩니다
- **자동 정렬**: 최신 날짜가 위에 표시됩니다
- **통합 업데이트**: `update_context.py` 실행 시 자동으로 데일리 로그에도 기록됩니다

### 파일 위치

- **데일리 컨텍스트 파일**: `Laptop/00. 개인비서/컨텍스트 담당자/데일리_컨텍스트.md`

### 사용법

#### 기본 사용 (인터랙티브 모드)

```bash
python3 update_daily_context.py
```

프롬프트에 따라:
- 작업 디렉토리 입력
- 작업 내용 설명 입력
- 중요 사항 입력
- 다음 작업 예정 입력

#### 명령줄 사용

```bash
python3 update_daily_context.py \
  "/Users/churryboy/Desktop/proby-sync/Laptop/50. Revenue/" \
  "매출 추적 및 분석" \
  "매출 목표 달성 현황 확인 필요" \
  "내일 매출 보고서 작성"
```

#### 통합 사용

`update_context.py`를 실행하면 자동으로 데일리 컨텍스트에도 기록됩니다:

```bash
python3 update_context.py \
  "/path/to/directory" \
  "작업 내용" \
  "다음 작업"
```

### 실시간 동기화

**중요**: `AGENT_CONTEXT.md`가 업데이트될 때마다 자동으로 데일리 컨텍스트 로그에 동기화됩니다.

- **자동 동기화**: `update_context.py`의 `update_context()` 함수를 사용하면 자동으로 동기화됩니다
- **수동 동기화**: `AGENT_CONTEXT.md`를 직접 수정한 경우 다음 명령으로 동기화하세요:
  ```bash
  python3 update_context.py --sync
  ```
- **대화 저장 시 동기화**: `conversation_logger.py`로 대화를 저장하면 자동으로 동기화됩니다

### 파일 형식

```markdown
# 데일리 컨텍스트 로그

## 2026-02-06

**업데이트 시간**: 14:30:15

### 작업 디렉토리
/Users/churryboy/Desktop/proby-sync/Laptop/50. Revenue/

### 작업 내용
매출 추적 및 분석

### 중요 사항
매출 목표 달성 현황 확인 필요

### 다음 작업
내일 매출 보고서 작성

---

## 2026-02-05

**업데이트 시간**: 16:45:22

### 작업 디렉토리
...
```

### 작동 원리

1. **첫 업데이트**: 해당 날짜의 섹션이 생성됩니다
2. **추가 업데이트**: 같은 날짜에 다시 업데이트하면 해당 날짜 섹션에 추가됩니다
3. **날짜 정렬**: 파일을 열 때마다 최신 날짜가 위에 표시되도록 자동 정렬됩니다
4. **통합 연동**: `update_context.py` 실행 시 자동으로 데일리 로그에도 기록됩니다

---

## 5. 대화 기록 Persist 시스템

Cursor 에이전트의 대화를 영구적으로 저장하고 관리하는 시스템입니다. **에이전트 세션이 종료되어도 모든 중요한 대화와 컨텍스트가 유지됩니다.**

### 핵심 기능

- **대화 영구 저장**: 중요한 대화를 JSON 형식으로 날짜별로 저장
- **자동 요약 추가**: 대화를 저장하면 자동으로 `AGENT_CONTEXT.md`에 요약 추가
- **컨텍스트 복원**: 새 에이전트가 시작할 때 이전 대화를 확인하여 작업 이어받기
- **태그 및 메타데이터**: 대화에 태그와 메타데이터를 추가하여 검색 및 관리 용이

### 파일 구조

```
conversations/
├── 2026-02-07/
│   ├── 143022_에이전트_persist_시스템_구축.json
│   └── 150530_매출_분석_논의.json
└── 2026-02-06/
    └── ...
```

### 사용법

#### Python 코드에서 사용

```python
from conversation_logger import save_conversation_from_text

# 간단한 대화 저장
save_conversation_from_text(
    title="에이전트 persist 시스템 구축",
    user_message="에이전트들이 언제나 소실되지 않고 persist했으면 좋겠어",
    assistant_message="대화 기록 persist 시스템을 구축했습니다...",
    summary="에이전트 대화를 영구 저장하는 시스템 구축 완료",
    tags=["시스템", "persist", "대화기록"],
    working_directory="/Users/churryboy/Desktop/proby-agents"
)
```

#### 인터랙티브 모드

```bash
python3 conversation_logger.py
```

프롬프트에 따라:
- 대화 제목 입력
- 사용자 메시지 입력
- 에이전트 응답 입력
- 대화 요약 입력 (선택사항)
- 태그 입력 (선택사항)

#### 최근 대화 확인

```python
from conversation_logger import list_recent_conversations

# 최근 7일간의 대화 목록
conversations = list_recent_conversations(days=7)
for conv in conversations:
    print(f"{conv['title']} - {conv['timestamp']}")
    print(f"  요약: {conv['summary']}")
    print(f"  태그: {', '.join(conv['tags'])}")
```

### 저장해야 할 대화

- ✅ 중요한 결정사항이 포함된 대화
- ✅ 복잡한 작업 요청이나 설명
- ✅ 문제 해결 과정이 포함된 대화
- ✅ 코드 변경에 대한 논의
- ✅ 프로젝트 방향성에 영향을 주는 대화

### 작동 원리

1. **대화 저장**: `conversation_logger.py`로 대화를 저장하면 `conversations/YYYY-MM-DD/` 디렉토리에 JSON 파일로 저장됩니다
2. **자동 요약**: 대화에 요약이 포함되어 있으면 자동으로 `AGENT_CONTEXT.md`의 "최근 대화 요약" 섹션에 추가됩니다
3. **컨텍스트 복원**: 새 에이전트가 시작할 때:
   - `AGENT_CONTEXT.md`를 읽어 현재 컨텍스트 확인
   - `conversations/` 디렉토리의 최근 대화 확인
   - 이전 작업을 이어받아 진행

### Cursor Rules 연동

`.cursor/rules/agent-persistence.mdc` 파일에 persist 규칙이 정의되어 있어, 모든 에이전트가 자동으로 이 시스템을 따릅니다.

### 주의사항

- 대화 기록은 기본적으로 git에 포함되지 않습니다 (`.gitignore`에 `conversations/` 포함)
- 대화 기록을 git에 포함하려면 `.gitignore`에서 해당 줄을 제거하세요
- 개인정보나 민감한 정보가 포함된 대화는 저장하지 마세요
