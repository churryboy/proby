# Mixpanel 데이터 추출

Mixpanel Data Export API 2.0로 Raw Event를 내려받아 vault의 `70. 메이커스/믹스패널 데이터/`에 JSONL로 저장합니다.

## "Unable to authenticate request" (400)가 나올 때

Data Export API는 **Service Account** 인증만 허용하는 경우가 많습니다. 아래처럼 Service Account를 만들고 `.env`에 넣으세요.

1. [Mixpanel](https://mixpanel.com) 로그인 → 왼쪽 하단 **Organization Settings** (조직 설정).
2. **Service Accounts** 탭 → **Create service account**.
3. 이름 입력, 프로젝트(예: 3979838) 접근 권한 부여 후 생성.
4. 생성 직후 나오는 **Username**과 **Secret**을 반드시 복사해 둡니다. (Secret은 다시 볼 수 없음.)
5. vault 루트 `.env`에 추가:
   ```env
   MIXPANEL_PROJECT_ID=3979838
   MIXPANEL_SA_USERNAME=발급받은_Username
   MIXPANEL_SA_SECRET=발급받은_Secret
   ```
   기존 `MIXPANEL_API_SECRET`은 사용하지 않아도 됩니다.

---

## 설정

1. **Mixpanel에서 키 확인**  
   [Mixpanel](https://mixpanel.com) → 프로젝트 선택 → **설정(톱니바퀴)** → **Access Keys**  
   - **Project ID**: 숫자(예: 3979838). 조직 설정 → Projects에서 확인.  
   - **Data Export API 인증** (둘 중 하나):
     - **레거시**: **API Secret** 사용 → `.env`에 `MIXPANEL_API_SECRET` 설정.
     - **권장**: **Service Account** 사용 → 조직 설정에서 Service Account 생성 후 Username/Secret 발급 → `.env`에 `MIXPANEL_SA_USERNAME`, `MIXPANEL_SA_SECRET` 설정.

2. **vault 루트 `.env`에 추가**
   ```env
   MIXPANEL_PROJECT_ID=3979838
   MIXPANEL_API_SECRET=여기에_API_시크릿
   ```
   또는 Service Account 사용 시:
   ```env
   MIXPANEL_PROJECT_ID=3979838
   MIXPANEL_SA_USERNAME=서비스계정_사용자명
   MIXPANEL_SA_SECRET=서비스계정_비밀
   ```
   ※ Secret/비밀은 코드·공개 저장소에 올리지 마세요.

## 실행

```bash
# vault 루트(proby-sync)에서
python3 "Skills/Mixpanel 내보내기/mixpanel_export.py"
```
- 인자 없음: **최근 7일** 구간으로 내보내기  
- 기간 지정: `from_date to_date` (YYYY-MM-DD)
  ```bash
  python3 "Skills/Mixpanel 내보내기/mixpanel_export.py" 2026-02-01 2026-02-20
  ```

## 출력

- 저장 위치: `70. 메이커스/믹스패널 데이터/export_YYYY-MM-DD_YYYY-MM-DD.jsonl`
- 형식: JSONL (한 줄에 이벤트 하나씩 JSON)

## 의존성

```bash
pip install requests
```
