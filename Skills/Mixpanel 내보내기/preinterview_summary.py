#!/usr/bin/env python3
"""
export_*.jsonl에서 'pre-interview button click' 이벤트만 추출해
직군(jobTitle) / 회사(company) 별 클릭 수를 집계한 마크다운 테이블을 출력합니다.

사용: python3 preinterview_summary.py [경로/export_2026-01-01_2026-02-20.jsonl]
      인자 없으면 70. 메이커스/믹스패널 데이터/ 에서 최신 export_*.jsonl 자동 선택
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

_VAULT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DIR = _VAULT_ROOT / "70. 메이커스" / "믹스패널 데이터"
EVENT_NAME = "pre-interview button click"


def main() -> None:
    if len(sys.argv) >= 2:
        path = Path(sys.argv[1])
    else:
        candidates = sorted(DEFAULT_DIR.glob("export_*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            print("export_*.jsonl 파일이 없습니다.")
            sys.exit(1)
        path = candidates[0]

    if not path.exists():
        print(f"파일 없음: {path}")
        sys.exit(1)

    # (company, job_title) -> count
    by_company_role = defaultdict(int)
    total = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("event") != EVENT_NAME:
                continue
            props = row.get("properties") or {}
            company = (props.get("company") or "").strip() or "(미설정)"
            job_title = (props.get("jobTitle") or "").strip() or "(미설정)"
            by_company_role[(company, job_title)] += 1
            total += 1

    # 회사별 합계도 구함
    by_company = defaultdict(int)
    for (company, job_title), count in by_company_role.items():
        by_company[company] += count

    # 테이블: 직군(jobTitle) | 회사(company) | 클릭 수
    rows = []
    for (company, job_title), count in sorted(by_company_role.items(), key=lambda x: (-x[1], x[0][0], x[0][1])):
        rows.append((job_title, company, count))

    # 마크다운 테이블
    print(f"# pre-interview button click 집계 (총 {total}회)")
    print()
    print(f"데이터 출처: `{path.name}`")
    print()
    print("| 직군 (jobTitle) | 회사 | 클릭 수 |")
    print("| --- | --- | ---:|")
    for job_title, company, count in rows:
        print(f"| {job_title} | {company} | {count} |")
    print()
    print("## 회사별 합계")
    print()
    print("| 회사 | 클릭 수 |")
    print("| --- | ---:|")
    for company, count in sorted(by_company.items(), key=lambda x: -x[1]):
        print(f"| {company} | {count} |")


if __name__ == "__main__":
    main()
