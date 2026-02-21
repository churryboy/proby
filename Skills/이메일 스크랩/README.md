# 이메일 스크랩

Gmail에서 **특정 도메인에서 온 메일**을 가져와 **30. 세일즈팀/이메일 맥락/** 폴더에 md 파일로 저장하는 스크립트입니다.

- **저장 형식**: 메일 1통 = md 파일 1개 (제목·발신·날짜·본문)
- **실행 방법**: 이 폴더에서 `python3 gmail_to_md.py`
- **설정**: `gmail_to_md.py` 상단의 `TARGET_DOMAINS`에 스크랩할 **발신 도메인** 추가 (예: `consumerinsight.kr` → 해당 도메인에서 온 메일 전체 수집)
- **Gmail API**: 이 폴더에 `credentials.json` 배치 (스크립트 주석 참고)
- **의존성**: 이 폴더에서 `pip3 install -r requirements-gmail.txt`
