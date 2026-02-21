# Path Abstraction Layer 설계 문서

## 📋 목표

폴더 구조 변경에 강한 파일 접근 시스템 구축
- **경로 하드코딩 제거**: 논리적 이름으로 파일 접근
- **메타데이터 기반 검색**: frontmatter 태그로 파일 찾기
- **중앙화된 경로 관리**: 한 곳에서 경로 변경 관리

---

## 🏗️ 아키텍처 개요

```
┌─────────────────────────────────────────┐
│     Application Scripts                 │
│  (todo_from_today.py, news_crawler.py)  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│     Path Abstraction Layer              │
│  (vault_path.py)                        │
│  - Logical Name → Path 매핑             │
│  - Metadata 기반 검색                    │
│  - Frontmatter 파싱                     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│     Configuration                        │
│  - vault_paths.json (Logical mappings)   │
│  - .env (VAULT_ROOT)                     │
└─────────────────────────────────────────┘
```

---

## 📁 파일 구조

```
proby-agents/
├── vault_path.py              # Path Abstraction Layer (새로 생성)
├── vault_paths.json           # Logical Name → Path 매핑 (새로 생성)
├── .env                       # VAULT_ROOT 환경변수
├── todo_from_today.py         # 기존 스크립트 (리팩토링)
├── news_crawler.py            # 기존 스크립트 (리팩토링)
└── create_todo.py             # 기존 스크립트 (리팩토링)
```

---

## 🔧 1단계: Vault Root 단일 변수화

### 현재 문제

```python
# 여러 스크립트에서 각각 정의
OBSIDIAN_VAULT_PATH = os.environ.get(
    "OBSIDIAN_VAULT_PATH",
    "/Users/churryboy/Desktop/proby-sync",
)
```

### 해결책

**중앙화된 경로 관리**

```python
# vault_path.py
import os
from pathlib import Path

VAULT_ROOT = Path(os.getenv("OBSIDIAN_VAULT_PATH", "/Users/churryboy/Desktop/proby-sync"))

def get_vault_root() -> Path:
    """Get the Obsidian vault root path."""
    return VAULT_ROOT
```

**이점**:

- ✅ 한 곳에서만 수정
- ✅ 환경변수 변경만으로 전체 경로 변경 가능

---

## 🗺️ 2단계: Logical Name → Path 매핑

### 설계: `vault_paths.json`

```json
{
  "logical_paths": {
    "todo_actual_folder": "Laptop/00. Todo/Actual",
    "todo_proposed_folder": "Laptop/00. Todo/Proposed",
    "todo_folder": "Laptop/00. Todo",
    "revenue_current": "Laptop/50. Revenue/Current Revenue.md",
    "revenue_folder": "Laptop/50. Revenue",
    "market_research_folder": "Laptop/10. Strategy/Market Research",
    "strategy_folder": "Laptop/10. Strategy"
  },
  "search_patterns": {
    "todo_actual_files": {
      "folder": "todo_actual_folder",
      "glob": "*.md",
      "sort_by": "date_in_filename"
    },
    "revenue_files": {
      "folder": "revenue_folder",
      "glob": "*.md",
      "metadata_filter": {
        "type": "revenue"
      }
    }
  }
}
```

### 사용 예시

**Before (하드코딩)**:

```python
possible_paths = [
    vault_path / "00. Todo" / "Actual",
    vault_path / "Laptop" / "00. Todo" / "Actual",
    # ... 10개 이상의 경로 시도
]
```

**After (논리적 이름)**:

```python
from vault_path import get_file_path, find_files_by_metadata

# 논리적 이름으로 접근
actual_folder = get_file_path("todo_actual_folder")
revenue_file = get_file_path("revenue_current")
```

**이점**:

- ✅ 폴더 구조 변경 시 `vault_paths.json`만 수정
- ✅ 코드는 논리적 이름만 사용
- ✅ 여러 가능한 경로를 자동으로 시도 (fallback 지원)

---

## 🏷️ 3단계: Metadata/Tag 기반 검색

### Frontmatter 예시

```markdown
---
type: revenue
role: current_revenue
project: core
date: 2025-02-07
---

# Current Revenue
...
```

### 검색 API 설계

```python
# vault_path.py

def find_files_by_metadata(
    metadata_filter: dict,
    folder: Optional[str] = None,
    glob_pattern: str = "*.md"
) -> List[Path]:
    """
    Find files by frontmatter metadata.
    
    Args:
        metadata_filter: {"type": "revenue", "role": "current_revenue"}
        folder: Logical folder name (optional, searches entire vault if None)
        glob_pattern: File pattern to search (default: "*.md")
    
    Returns:
        List of matching file paths
    """
    pass

def get_file_by_metadata(
    metadata_filter: dict,
    folder: Optional[str] = None
) -> Optional[Path]:
    """
    Get single file by metadata (returns first match).
    """
    pass
```

### 사용 예시

**Before (경로 직접 지정)**:

```python
revenue_file = vault_path / "50. Revenue" / "Current Revenue.md"
if not revenue_file.exists():
    revenue_file = vault_path / "Laptop" / "50. Revenue" / "Current Revenue.md"
    # ... 여러 경로 시도
```

**After (메타데이터 검색)**:

```python
from vault_path import get_file_by_metadata

# type=revenue, role=current_revenue인 파일 찾기
revenue_file = get_file_by_metadata({
    "type": "revenue",
    "role": "current_revenue"
})

# 또는 논리적 이름 + 메타데이터 조합
revenue_file = get_file_by_metadata(
    {"type": "revenue"},
    folder="revenue_folder"
)
```

**이점**:

- ✅ 파일명 변경에 영향 없음
- ✅ 폴더 이동에 영향 없음
- ✅ 여러 파일 중 조건에 맞는 파일 자동 선택

---

## 🔄 4단계: 하이브리드 접근 (논리적 이름 + 메타데이터)

### 실제 사용 패턴

**Case 1: 정확한 파일이 필요한 경우**

```python
# 논리적 이름 사용 (빠르고 명확)
revenue_file = get_file_path("revenue_current")
```

**Case 2: 조건에 맞는 파일을 찾는 경우**

```python
# 메타데이터 검색 (유연함)
latest_actual = get_file_by_metadata(
    {"type": "todo_actual"},
    folder="todo_actual_folder"
)
```

**Case 3: 여러 파일 중 선택**

```python
# 날짜 기반 검색
from datetime import datetime
today = datetime.now().date()

actual_files = find_files_by_metadata(
    {"type": "todo_actual"},
    folder="todo_actual_folder"
)

# 날짜가 파일명에 포함된 최신 파일 찾기
latest = max(actual_files, key=lambda p: extract_date_from_path(p))
```

---

## 📝 구현 계획

### Phase 1: Core Infrastructure

1. ✅ `vault_path.py` 생성
   - `get_vault_root()` 함수
   - `get_file_path(logical_name)` 함수
   - JSON 설정 파일 로딩

2. ✅ `vault_paths.json` 생성
   - 현재 사용 중인 모든 경로 매핑
   - 검색 패턴 정의

### Phase 2: Metadata Support

3. ✅ Frontmatter 파싱 유틸리티
   - `parse_frontmatter(file_path)` 함수
   - `find_files_by_metadata()` 함수

4. ✅ 기존 파일에 frontmatter 추가 (선택적)
   - `Current Revenue.md`에 `type: revenue` 추가
   - `Actual/*.md`에 `type: todo_actual` 추가

### Phase 3: Migration

5. ✅ 기존 스크립트 리팩토링
   - `todo_from_today.py` → `vault_path` 사용
   - `news_crawler.py` → `vault_path` 사용
   - `create_todo.py` → `vault_path` 사용

### Phase 4: Enhancement

6. ✅ 고급 검색 기능
   - 날짜 범위 검색
   - 태그 조합 검색
   - 캐싱 (성능 최적화)

---

## 🎯 마이그레이션 전략

### 점진적 마이그레이션

**Step 1**: `vault_path.py` 생성 + 기존 코드와 병행 사용

```python
# 기존 코드 유지하면서 새 모듈 추가
from vault_path import get_file_path

# 점진적으로 교체
# old: vault_path / "00. Todo" / "Actual"
# new: get_file_path("todo_actual_folder")
```

**Step 2**: 한 스크립트씩 마이그레이션

- `create_todo.py` 먼저 (가장 단순)
- `todo_from_today.py` 다음
- `news_crawler.py` 마지막

**Step 3**: 기존 경로 탐색 로직 제거

- `possible_paths` 리스트 제거
- `find_vault_file()` 함수 제거 (vault_path로 대체)

---

## 📊 비교: Before vs After

### Before (현재)

```python
# todo_from_today.py
def get_latest_actual_note():
    vault_path = Path(OBSIDIAN_VAULT_PATH)
    possible_paths = [
        vault_path / "00. Todo" / "Actual",
        vault_path / "00.Todo" / "Actual",
        vault_path / "00 Todo" / "Actual",
        vault_path / "Laptop" / "00. Todo" / "Actual",
        vault_path / "Laptop" / "00.Todo" / "Actual",
        vault_path / "Laptop" / "00 Todo" / "Actual",
        vault_path / "Mobile" / "00. Todo" / "Actual",
        vault_path / "Mobile" / "00.Todo" / "Actual",
        vault_path / "iMAC" / "00. Todo" / "Actual",
        vault_path / "iMAC" / "00.Todo" / "Actual",
    ]
    # ... 20줄 이상의 경로 탐색 로직
```

**문제점**:

- ❌ 경로 변경 시 코드 수정 필요
- ❌ 중복 코드 (여러 스크립트에 동일 로직)
- ❌ 유지보수 어려움

### After (제안)

```python
# todo_from_today.py
from vault_path import get_file_path, find_files_by_metadata
from datetime import datetime

def get_latest_actual_note():
    # 방법 1: 논리적 이름 사용
    actual_folder = get_file_path("todo_actual_folder")
    
    # 방법 2: 메타데이터 검색 (더 강력)
    today = datetime.now().date()
    actual_files = find_files_by_metadata(
        {"type": "todo_actual"},
        folder="todo_actual_folder"
    )
    
    # 날짜 기반으로 최신 파일 선택
    return max(actual_files, key=lambda p: extract_date(p))
```

**장점**:

- ✅ 경로 변경 시 `vault_paths.json`만 수정
- ✅ 코드 간결 (5줄 이하)
- ✅ 메타데이터 기반으로 더 유연한 검색

---

## 🔍 고급 기능 (선택적)

### 1. 캐싱

```python
# vault_path.py
from functools import lru_cache

@lru_cache(maxsize=100)
def get_file_path(logical_name: str) -> Path:
    """캐싱으로 성능 향상"""
    pass
```

### 2. 자동 경로 발견

```python
def auto_discover_paths(vault_root: Path) -> dict:
    """
    Vault를 스캔해서 자동으로 경로 매핑 생성
    (초기 설정 시 유용)
    """
    pass
```

### 3. 경로 검증

```python
def validate_paths(config: dict) -> List[str]:
    """
    vault_paths.json의 모든 경로가 존재하는지 검증
    누락된 경로 리스트 반환
    """
    pass
```

---

## 📌 핵심 원칙

1. **단일 책임**: `vault_path.py`는 경로 관리만 담당

2. **설정과 코드 분리**: 경로는 JSON, 로직은 Python

3. **하위 호환성**: 기존 코드와 병행 사용 가능

4. **점진적 마이그레이션**: 한 번에 모든 것을 바꾸지 않음

5. **메타데이터 우선**: 가능하면 메타데이터 기반 검색 사용

---

## 🚀 다음 단계

1. 이 설계 문서 검토 및 피드백

2. `vault_path.py` 구현 시작

3. `vault_paths.json` 초기 버전 작성

4. 첫 번째 스크립트 마이그레이션 (`create_todo.py`)

---

**작성일**: 2025-02-07
**목적**: 폴더 구조 변경에 강한 Path Abstraction Layer 설계
