# Surl-project

서버리스 URL 단축 서비스, AI 트렌드분석을 곁들인

## 프로젝트 구조

```
surl-project/
├── template.yaml           # AWS SAM 인프라 정의 (IaC)
├── requirements.txt        # 공통 의존성 (boto3 등)
│
├── src/                    # 람다 함수 소스코드
│   ├── common/             # 공통 로직 (Base62 변환 등)
│   │   └── base62.py
│   ├── create/             # URL 단축 람다
│   │   └── app.py
│   └── redirect/           # 리다이렉트 람다
│       └── app.py
│
├── scripts/                # 로컬 확인용 스크립트
│   └── local_run.py       # SQLite로 URL 단축 create/get (AWS 불필요)
├── tests/                  # 테스트 폴더
│   ├── unit/               # 로컬 유닛 테스트
│   │   └── test_logic.py   # Base62 등 검증 코드
│   └── events/             # SAM 로컬 테스트용 이벤트 샘플
│       ├── create_event.json
│       └── redirect_event.json
│
└── README.md               # 프로젝트 문서
```

## 로컬 기능 확인 (AWS 없이, 가장 간단)

**SQLite + Python만**으로 URL 단축이 동작하는지 확인할 때 사용합니다.  
DB 파일은 프로젝트 루트에 `local_links.db`로 생성됩니다.

```bash
# 프로젝트 루트에서 실행 (WSL Ubuntu)
cd /mnt/c/CE/99.project/Surl-project

# 1) URL 저장 → short_code 받기
python3 scripts/local_run.py create "https://긴주소.com/페이지"

# 2) short_code로 원본 URL 조회
python3 scripts/local_run.py get 1
```

- 첫 실행 시 `local_links.db` 파일이 자동 생성됩니다.
- `create`는 입력한 URL을 DB에 저장하고 짧은 코드(예: 1, 2, 1Z)를 출력합니다.
- `get`은 해당 코드로 저장된 원본 URL을 출력합니다.

---

## 로컬 실행 (WSL Ubuntu)

### 의존성 설치

```bash
pip3 install -r requirements.txt
```

### 유닛 테스트 실행

```bash
cd tests/unit && python3 test_logic.py
# 또는
python3 -m pytest tests/unit/ -v
```

### SAM 로컬 테스트

```bash
# Create 람다
sam local invoke CreateFunction -e tests/events/create_event.json

# Redirect 람다
sam local invoke RedirectFunction -e tests/events/redirect_event.json
```

### SAM 빌드 & 배포

```bash
sam build
sam deploy --guided
```
