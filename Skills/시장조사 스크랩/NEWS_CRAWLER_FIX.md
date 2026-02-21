# News Crawler 모델 에러 수정

## 🔍 문제

LLM 요약 생성 시 모델을 찾을 수 없어 실패했습니다:
- `claude-3-5-sonnet-20241022` - not found
- `claude-3-5-sonnet-20240620` - not found  
- `claude-3-opus-20240229` - deprecated

---

## ✅ 수정 완료

모델 목록을 최신 모델로 업데이트했습니다:

```python
model_names = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",  # 새로 추가 (더 빠르고 저렴)
    "claude-3-5-sonnet-20240620",
    "claude-sonnet-4-20250514",   # 새로 추가 (최신 모델)
]
```

---

## 🚀 다음 단계

### 1. API 키 확인

```bash
cd ~/Desktop/proby-agents
grep ANTHROPIC_API_KEY .env
```

API 키가 없거나 잘못되었으면 `.env` 파일을 수정하세요.

### 2. 다시 실행

```bash
python3 news_crawler.py
```

또는

```bash
./strategy
```

---

## 💡 모델 선택 순서

스크립트는 다음 순서로 모델을 시도합니다:

1. **claude-3-5-sonnet-20241022** - 가장 강력한 모델
2. **claude-3-5-haiku-20241022** - 빠르고 저렴한 대안
3. **claude-3-5-sonnet-20240620** - 이전 버전
4. **claude-sonnet-4-20250514** - 최신 모델

첫 번째로 작동하는 모델을 사용합니다.

---

## ❓ 여전히 에러가 나면?

### API 키 확인
```bash
echo $ANTHROPIC_API_KEY
```

### Anthropic 계정 확인
- https://console.anthropic.com/ 에서
- API 키가 유효한지 확인
- 모델 접근 권한 확인

### 모델 이름 확인
- Anthropic 문서에서 현재 사용 가능한 모델 확인
- 필요하면 `news_crawler.py`의 `model_names` 리스트 수정

---

## ✅ 수정된 파일

- `news_crawler.py` - 모델 목록 업데이트

다시 실행해보세요!
