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
├── tests/                  # 테스트 폴더
│   ├── unit/               # 로컬 유닛 테스트
│   │   └── test_logic.py   # Base62 등 검증 코드
│   └── events/             # SAM 로컬 테스트용 이벤트 샘플
│       ├── create_event.json
│       └── redirect_event.json
│
└── README.md               # 프로젝트 문서
```

## 로컬 실행 (WSL Ubuntu)

### 의존성 설치

```bash
pip install -r requirements.txt
```

### 유닛 테스트 실행

```bash
cd tests/unit && python test_logic.py
# 또는
python -m pytest tests/unit/ -v
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
