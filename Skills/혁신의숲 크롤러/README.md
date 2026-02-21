# 혁신의숲 분석리포트 크롤러

[혁신의숲 분석리포트](https://www.innoforest.co.kr/report?newsTypeCd=RR&page=1) 목록을 수집해 마크다운으로 저장합니다.  
목록이 JavaScript로 렌더링되므로 **Playwright**로 페이지를 연 뒤 링크/제목을 수집합니다.

## 설치

```bash
pip install -r requirements.txt
playwright install chromium
```

## 사용

```bash
# 프로젝트 루트에서
python3 "Skills/혁신의숲 크롤러/innoforest_report_crawler.py"
```

- `--max-pages N`: 수집할 목록 페이지 수 (기본 5)
- `--output-dir PATH`: 저장 폴더 (기본: `10. 전략팀/리서치 애널리스트/시장동향/혁신의숲`)
- `--fetch-body`: 각 리포트 본문도 requests로 수집 (선택)

## 출력

`혁신의숲_분석리포트_YYYY-MM-DD.md` 한 파일에 제목·URL 목록이 저장됩니다.
