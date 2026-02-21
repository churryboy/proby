# Vault Path Abstraction Layer

Obsidian Vault의 파일 접근을 추상화하는 모듈입니다.

## 📁 구조

```
vault_path/
├── __init__.py              # Path Abstraction Layer 핵심 모듈
├── vault_paths.json         # 논리적 이름 → 경로 매핑 설정
├── DESIGN_PATH_ABSTRACTION.md # 설계 문서
└── README.md                # 이 파일
```

## 🎯 목적

폴더 구조 변경에 강한 파일 접근 시스템을 제공합니다:
- **경로 하드코딩 제거**: 논리적 이름으로 파일 접근
- **메타데이터 기반 검색**: frontmatter 태그로 파일 찾기
- **중앙화된 경로 관리**: 한 곳에서 경로 변경 관리

## 📖 사용법

### 기본 사용

```python
from vault_path import get_vault_root, get_file_path

# Vault 루트 경로 가져오기
vault_root = get_vault_root()

# 논리적 이름으로 파일/폴더 접근
revenue_file = get_file_path("revenue_current")
todo_folder = get_file_path("todo_folder")
```

### 메타데이터 기반 검색

```python
from vault_path import find_files_by_metadata, get_file_by_metadata

# 메타데이터로 파일 찾기
revenue_files = find_files_by_metadata(
    {"type": "revenue"},
    folder="revenue_folder"
)

# 단일 파일 찾기
revenue_file = get_file_by_metadata(
    {"type": "revenue", "role": "current_revenue"}
)
```

## ⚙️ 설정

`vault_paths.json`에서 논리적 이름과 실제 경로를 매핑합니다:

```json
{
  "logical_paths": {
    "todo_actual_folder": "Laptop/00. Todo/Actual",
    "revenue_current": "Laptop/50. Revenue/Current Revenue.md"
  }
}
```

폴더 구조가 변경되면 이 파일만 수정하면 됩니다.

## 📚 자세한 내용

설계 문서는 `DESIGN_PATH_ABSTRACTION.md`를 참고하세요.
