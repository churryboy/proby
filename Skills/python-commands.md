# Python Scripts 실행 커맨드

터미널에서 바로 복사해서 실행할 수 있는 커맨드 모음입니다.

## 기본 디렉토리 이동
```bash
cd /Users/churryboy/Desktop/proby-agents
```

---

## 1. todo_from_today.py - AI 기반 할일 생성기

```bash
python3 "Skills/투두 관리/todo_from_today.py"
```

**설명**: 오늘의 Actual 노트를 분석하여 내일의 우선순위 할일을 생성

---

## 2. create_todo.py - 할일 추가 유틸리티

### 기본 사용 (오늘 날짜 파일에 추가)
```bash
python3 "Skills/투두 관리/create_todo.py" "할 일 내용"
```

### 특정 파일에 추가
```bash
python3 "Skills/투두 관리/create_todo.py" "할 일 내용" --file "00. Todo/Actual/2025-02-15.md"
```

### 완료된 할일로 추가
```bash
python3 "Skills/투두 관리/create_todo.py" "완료된 작업" --checked
```

### 옵션 조합
```bash
python3 "Skills/투두 관리/create_todo.py" "할 일 내용" --file "경로/파일.md" --checked
```

**옵션**:
- `--file` 또는 `-f`: 특정 파일 경로 지정
- `--checked` 또는 `-c`: 완료된 할일로 표시
- `--today` 또는 `-t`: 오늘 날짜 파일에 추가 (기본값)

---

## 3. news_crawler.py - 대상 홀딩스 뉴스 크롤러

### 프로젝트 폴더에서 실행
```bash
cd /Users/churryboy/Desktop/proby-sync
python3 "Skills/시장조사 스크랩/news_crawler.py"
```

### 한 줄 실행 (어느 디렉토리에서든)
```bash
cd /Users/churryboy/Desktop/proby-sync && python3 "Skills/시장조사 스크랩/news_crawler.py"
```

**설명**: 대상 홀딩스·핵심 브랜드(청정원, 종가, 미원 등)·국내/해외 경쟁사 뉴스를 수집해 Obsidian vault의 `Laptop/10. 전략팀/리서치 애널리스트`에 저장. LLM 요약 포함.

---

## 4. generate_token_test_files.py - 토큰 테스트 파일 생성기

```bash
python3 generate_token_test_files.py
```

**설명**: 토큰 제한 테스트를 위한 HR 분야 유저 리서치 및 PRD 파일 생성 (총 100개 파일, 약 200,000 토큰)

**생성 위치**:
- 유저 리서치: `Laptop/99. TOKEN_TEST/User_Research/` (50개 파일)
- PRD: `Laptop/99. TOKEN_TEST/PRD/` (50개 파일)

**테스트 완료 후 삭제**:
```bash
rm -rf "/Users/churryboy/Desktop/proby-sync/Laptop/99. TOKEN_TEST"
```

---

## 5. notion_to_md.py - Notion 페이지를 마크다운으로 변환

### 기본 사용 (콘솔에 출력)
```bash
python3 notion_to_md.py "https://www.notion.so/Ridi-2fdd9296fa01808a977dfe453a911896"
```

### 파일로 저장
```bash
python3 notion_to_md.py "https://www.notion.so/Ridi-2fdd9296fa01808a977dfe453a911896" "output.md"
```

### 페이지 ID 직접 사용
```bash
python3 notion_to_md.py "2fdd9296fa01808a977dfe453a911896"
```

**설명**: Notion 페이지를 마크다운 형식으로 변환합니다.

**필수 설정**:
1. Notion API 통합 생성: https://www.notion.so/my-integrations
2. `.env` 파일에 `NOTION_API_KEY` 추가
3. 변환할 페이지에 API 통합 연결 (페이지 설정 > 연결 > 통합 추가)

**환경 변수 (.env 파일)**:
```env
NOTION_API_KEY=secret_...
```

---

## 6. social_listener.py - 소셜 리스닝 (멀티 플랫폼)

### 기본 실행
```bash
cd /Users/churryboy/Desktop/proby-sync
python3 "Skills/시장조사 스크랩/social_listener.py"
```

### 커스텀 키워드 (쉼표 구분)
```bash
python3 "Skills/시장조사 스크랩/social_listener.py" "Proby,user research,market research"
```

**지원 채널**:
| 채널 | 필요 설정 | 비고 |
|------|-----------|------|
| **Reddit** | REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET | PRAW, 무료 |
| **Twitter/X** | TWITTER_BEARER_TOKEN | Free tier 7일 검색 |
| **Threads** | THREADS_ACCESS_TOKEN | Meta Graph API |
| **Instagram** | INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID | 해시태그 검색, App Review 필요 |
| **Facebook** | FACEBOOK_PAGE_ACCESS_TOKEN, FACEBOOK_PAGE_IDS | 본인 관리 페이지만 |
| **LinkedIn** | - | 공식 API에 공개 검색 없음 |
| **TikTok** | - | Research API는 학술용만 |

**출력 위치**: `market_research_folder/Social Listening/` (또는 `10. 전략팀/리서치 애널리스트/Social Listening`)

**추가 의존성**: `pip install praw tweepy requests python-dotenv`

---

## 7. youtube_to_md.py - YouTube 자막을 마크다운으로 저장

### 기본 사용 (동영상 URL만으로 파일 자동 생성)
```bash
cd /Users/churryboy/Desktop/proby-sync
python3 "Skills/유튜브 크롤러/youtube_to_md.py" "https://www.youtube.com/watch?v=4uzGDAoNOZc"
```

### 출력 파일명을 직접 지정
```bash
python3 "Skills/유튜브 크롤러/youtube_to_md.py" "https://www.youtube.com/watch?v=4uzGDAoNOZc" "my_video_note.md"
```

**설명**: YouTube 영상의 자막(트랜스크립트)을 불러와 타임스탬프가 포함된 마크다운 파일로 저장합니다.  
**주의**: 영상에 자막이 없거나, 자막이 비활성화된 경우에는 별도의 음성 인식(Whisper 등)이 필요합니다.

---

## 8. md_to_slack.py - 마크다운을 Slack 채널로 전송

### 기본 사용 (마크다운 파일 전송)
```bash
cd /Users/churryboy/Desktop/proby-sync
python3 "Skills/슬랙 전송/md_to_slack.py" "00. 경영지원/투두 관리자/이메일맥락_투두_체크리스트.md"
```

### 메시지 제목 추가
```bash
python3 "Skills/슬랙 전송/md_to_slack.py" "00. 경영지원/투두 관리자/Actual/2026-02-20.md" "오늘 할일"
```

**설명**: 마크다운 파일 내용을 `.env`의 `SLACK_WEBHOOK_URL`로 설정한 채널(예: #all-todo)에 전송합니다.  
**필수 설정**: `.env`에 `SLACK_WEBHOOK_URL` 추가 (Slack 앱 → Incoming Webhooks에서 발급).

---

## 9. question_to_google_form.py - Google Form 설문지 자동 생성

### 기본 사용 (제목 + 질문들)
```bash
cd /Users/churryboy/Desktop/proby-sync
python3 "Skills/설문 연동/question_to_google_form.py" "설문 제목" -q "질문1" -q "질문2" -q "질문3"
```

### 예시 (고객 만족도)
```bash
python3 "Skills/설문 연동/question_to_google_form.py" "고객 만족도 조사" -q "이름" -q "이번 서비스에 만족하셨나요? (1-5)" -q "추가 의견"
```

**설명**: Google Forms API로 설문지를 생성하고 **편집 URL** / **응답 URL**을 출력합니다.  
**사전 준비**: Google Cloud에서 Forms API 활성화, OAuth 클라이언트 ID로 `Skills/설문 연동/credentials.json` 배치 (Gmail 스크랩과 같은 프로젝트면 이메일 스크랩 폴더의 credentials.json 복사 가능). 최초 실행 시 브라우저 로그인으로 `token_forms.json` 생성.  
**의존성**: `pip3 install -r Skills/설문\ 연동/requirements-forms.txt`

---

## 의존성 설치

```bash
# 기본 (뉴스 크롤러, TODO 등)
pip3 install anthropic python-dotenv requests feedparser beautifulsoup4 python-dateutil

# 소셜 리스닝 추가
pip3 install praw tweepy
```

---

## 환경 변수 설정 (.env 파일)

```env
ANTHROPIC_API_KEY=your_api_key_here
OBSIDIAN_VAULT_PATH=/Users/churryboy/Desktop/proby-sync
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...   # md_to_slack.py용
```
