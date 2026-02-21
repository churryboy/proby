# 설문 연동 (Google Forms)

Cursor 또는 터미널에서 설문 제목 + 질문을 입력하면 Google Form이 자동 생성됩니다.

## 1. 사전 준비

1. **Google Cloud Console**  
   - [Google Forms API](https://console.cloud.google.com/apis/library/forms.googleapis.com) 활성화  
   - **설문 링크 자동 발송**을 쓰려면 [Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)도 같은 프로젝트에서 활성화  
   - **API 및 서비스 → 사용자 인증 정보**에서 OAuth 2.0 클라이언트 ID (데스크톱 앱) 생성 후 JSON 다운로드  

2. **credentials.json 배치**  
   - 다운로드한 파일 이름을 `credentials.json`으로 바꿔 이 폴더(`Skills/설문 연동`)에 저장  
   - Gmail 스크랩과 같은 프로젝트를 쓰는 경우: `Skills/이메일 스크랩/credentials.json`을 이 폴더로 복사해도 됨 (클라이언트 ID가 같으면 재사용 가능)  

3. **의존성 설치**  
   ```bash
   pip3 install -r requirements-forms.txt
   ```
   (또는 프로젝트 루트에서 `pip3 install -r "Skills/설문 연동/requirements-forms.txt"`)

4. **최초 1회 실행**  
   - 아래처럼 한 번 실행하면 브라우저가 열리고 Google 로그인·권한 허용 후 `token_forms.json`이 생성됩니다.  
   - 이후에는 이 토큰으로 자동 인증됩니다.

## 2. 사용법

### 단답형만 (기존처럼)
```bash
python3 "Skills/설문 연동/question_to_google_form.py" "설문 제목" -q "질문1" -q "질문2"
```

### 문항 타입 지정 (객관식·체크박스·선형 배율)
```bash
# 객관식(라디오): choice:질문|옵션1|옵션2|옵션3
# 복수선택:       checkbox:질문|옵션1|옵션2
# 선형 배율(1~5): scale:질문|1|5|최저 라벨|최고 라벨
python3 "Skills/설문 연동/question_to_google_form.py" "제목" \
  --item "choice:사용 빈도?|매일|주 1회|가끔" \
  --item "scale:만족도|1|5|불만|만족"
```

### JSON 파일로 한 번에 (추천)
```bash
python3 "Skills/설문 연동/question_to_google_form.py" "제목" --from-json "Skills/설문 연동/surveys/광고_도입_반응_조사.json"
```
JSON 형식: `{ "title": "설문 제목", "items": [ {"type": "text"|"choice"|"checkbox"|"scale", "title": "...", "options": [...] 또는 "low"/"high"/"lowLabel"/"highLabel" } ] }`

출력 예:
```
생성 완료.
편집: https://docs.google.com/forms/d/xxx/edit
응답: https://docs.google.com/forms/d/xxx/viewform
```

- **편집**: 설문 수정용 링크  
- **응답**: 설문 응답 받는 링크 (공유용)

### 설문 링크 자동 발송 (Gmail)

생성된 **응답 링크**를 지정한 이메일 주소로 **chris@proby.io(또는 로그인한 Google 계정)** 에서 자동 발송하려면:

1. 위에서 **Gmail API** 활성화 후, **최초 1회** `--send-to` 옵션으로 실행하면 브라우저에서 **Gmail 발송 권한**까지 한 번 더 허용합니다. (기존 `token_forms.json`이 있으면 삭제 후 다시 로그인하면 새 권한이 추가됩니다.)
2. 실행 예:
```bash
python3 "Skills/설문 연동/question_to_google_form.py" "설문 제목" --from-json "Skills/설문 연동/surveys/파일명.json" --send-to "user1@example.com,user2@example.com"
```
3. 발신자는 **OAuth 로그인한 계정**(예: chris@proby.io)으로 표시되고, 수신자에게 설문 제목 + 응답 링크가 담긴 메일이 발송됩니다.

## 3. Cursor에서 쓰기

- 채팅에서 "이 주제로 구글 폼 만들어줘"라고 하면, 에이전트가 위 스크립트를 실행해 설문을 만들고 링크를 알려줄 수 있습니다.  
- 추후 `%설문 설문 제목 / 질문1 / 질문2` 같은 단축어 규칙을 추가하면 더 편합니다.
