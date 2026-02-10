# SAM CLI로 AWS 배포 절차 (IaC)

## 사전 요구사항

1. **AWS 계정** 및 IAM 사용자(또는 역할)에 배포 권한
2. **AWS CLI** 설치 및 `aws configure` 완료
3. **SAM CLI** 설치

### WSL Ubuntu에서 설치

```bash
# AWS CLI (미설치 시)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# AWS 자격증명 설정 (Access Key, Secret Key 입력)
aws configure

# SAM CLI
pip3 install aws-sam-cli
# 또는: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
```

---

## 배포 절차 (요약)

| 단계 | 명령/작업 |
|------|-----------|
| 1 | 터미널에서 프로젝트 루트로 이동 |
| 2 | `sam build` 로 빌드 |
| 3 | `sam deploy --guided` 로 첫 배포(설정 저장) |
| 4 | 이후 배포는 `sam deploy` 만 실행 |

---

## 단계별 상세

### 1. 프로젝트 루트로 이동

```bash
cd /mnt/c/CE/99.project/Surl-project
```

### 2. 빌드

```bash
sam build
```

- `template.yaml`과 `CodeUri`에 맞게 Lambda 소스가 패키징됩니다.
- 출력 디렉터리: `.aws-sam/build/`

### 3. 첫 배포 (설정 저장)

```bash
sam deploy --guided
```

대화형으로 아래를 묻습니다. 한 번 입력한 값은 `samconfig.toml`에 저장됩니다.

| 질문 | 권장/설명 |
|------|-----------|
| **Stack Name** | 예: `surl-project` |
| **AWS Region** | 예: `ap-northeast-2` (서울) |
| **Confirm changes before deploy** | `y` 권장 |
| **Allow SAM CLI IAM role creation** | `y` (템플릿에 역할이 없으면 SAM이 생성) |
| **Disable rollback** | `n` (실패 시 롤백 유지) |
| **Save arguments to configuration file** | `y` |
| **SAM configuration file name** | 기본값 `samconfig.toml` |
| **SAM configuration environment** | 기본값 `default` |

### 4. 이후 배포

```bash
sam build
sam deploy
```

- `samconfig.toml`에 저장된 설정을 그대로 사용합니다.
- 옵션 변경이 필요하면 `sam deploy --guided` 를 다시 실행해 설정을 덮어쓸 수 있습니다.

### 5. 배포 결과 확인

- 터미널 출력의 **Outputs** 에서 `ApiEndpoint` URL 확인.
- 예: `https://xxxxxxxxxx.execute-api.ap-northeast-2.amazonaws.com/Prod/`
  - 단축 생성: `POST {ApiEndpoint}create` (body: `{"url": "https://..."}`)
  - 리다이렉트: `GET {ApiEndpoint}{shortCode}`

---

## 배포 취소 (스택 삭제)

```bash
aws cloudformation delete-stack --stack-name surl-project
```

---

## 참고

- **빌드 전 확인**: 사용자 규칙에 따라 빌드 전에 `빌드를 시작할까요? (y/n)` 등을 스크립트에서 묻도록 할 수 있습니다.
- **리전**: 동일 리전의 Lambda, API Gateway, (추가 시) DynamoDB가 함께 사용됩니다.

---

# template.yaml 코드 리뷰

## 적용된 수정 사항

### 1. Lambda 패키징 (공통 모듈 포함) — 수정 완료

- **이슈**: `CodeUri: src/create/`, `src/redirect/`만 사용하면 `common/base62.py`가 패키지에 포함되지 않아 배포 후 `ModuleNotFoundError: No module named 'common'` 발생.
- **조치**: 두 함수 모두 `CodeUri: src/`로 통일하고, `Handler`만 `create.app.handler` / `redirect.app.handler`로 지정. 이렇게 하면 `src/` 전체(create, redirect, common)가 패키징되어 `from common.base62 import ...` 가 정상 동작.

---

## DynamoDB 테이블 및 IAM 리뷰 (카운터 / 매핑)

### SurlCounterTable (카운터)

| 항목 | 내용 |
|------|------|
| PK | `counter_name` (String) — 예: `"url_id"` 한 건으로 순번 관리 |
| TableName | `SurlCounter` (고정명 지정 가능) |
| 용도 | Create 시 atomic increment 후 Base62(값) = short_code 생성 |

- **IAM**: CreateFunction에 `DynamoDBCrudPolicy` (UpdateItem으로 증가, 필요 시 GetItem/PutItem) 적용됨.
- **환경 변수**: CreateFunction에 `COUNTER_TABLE_NAME: !Ref SurlCounterTable` 추가됨.

### SurlMappingTable (매핑)

| 항목 | 내용 |
|------|------|
| PK | `shortCode` (String) |
| TableName | 미지정 → 스택 배포 시 자동 생성 이름 사용 |
| 용도 | shortCode → originalUrl 조회 (Redirect), Create 시 PutItem |

- **IAM**: CreateFunction `DynamoDBCrudPolicy`, RedirectFunction `DynamoDBReadPolicy` 적용됨.
- **환경 변수**: 두 함수 모두 `TABLE_NAME: !Ref SurlMappingTable` 사용.

### 요약

- 카운터/매핑 테이블 정의와 Lambda용 IAM·환경 변수는 현재 구성으로 사용 가능.
- Create 람다 구현 시: COUNTER_TABLE_NAME에서 UpdateItem으로 다음 번호 받은 뒤 Base62 인코딩 → TABLE_NAME에 shortCode + originalUrl PutItem.

---

## 현재 템플릿 구조 요약

| 항목 | 내용 |
|------|------|
| Transform | `AWS::Serverless-2016-10-31` (SAM) |
| Globals | Runtime python3.12, Timeout 10s, Memory 256MB |
| SurlCounterTable | PK counter_name (String), TableName: SurlCounter |
| SurlMappingTable | PK shortCode (String) |
| CreateFunction | POST /create, TABLE_NAME + COUNTER_TABLE_NAME, 두 테이블 Crud |
| RedirectFunction | GET /{shortCode}, TABLE_NAME, 매핑 테이블 Read |
| Outputs | ApiEndpoint, CreateFunctionArn, RedirectFunctionArn |

---

## 추후 보완 권장 사항

1. **DynamoDB 테이블 미정의**  
   create/redirect 람다가 실제로 DB를 쓰려면 테이블 리소스를 추가하고, 람다에 `Environment`로 테이블명을 넘겨야 합니다. 현재 람다 코드는 DynamoDB 연동이 TODO 상태이므로, 테이블 추가 후 람다 구현을 마무리해야 합니다.

2. **CORS**  
   브라우저에서 같은 API를 호출할 계획이면 API Gateway 또는 Lambda 응답에 CORS 헤더를 추가해야 합니다. 필요 시 `Globals.Function.Environment` 또는 각 Lambda 응답에 `Access-Control-Allow-Origin` 등을 넣을 수 있습니다.

3. **ApiEndpoint Output**  
   `!Sub '.../Prod/'` 로 끝나므로, 클라이언트는 `{ApiEndpoint}create`, `{ApiEndpoint}{shortCode}` 처럼 경로를 붙여 사용하면 됩니다. 필요하면 설명을 README나 Outputs `Description`에 적어 두면 좋습니다.

4. **리소스 이름**  
   `CreateFunction`, `RedirectFunction` 등은 CloudFormation 리소스 로직명으로 적절합니다. 리소스가 늘어나면 네이밍 규칙(예: `SurlCreateFunction`)을 정해 두면 관리하기 쉽습니다.

---

## 배포 전 체크리스트

- [ ] `aws configure` 완료 (해당 계정에 배포 권한 있음)
- [ ] `sam build` 성공
- [ ] `sam deploy --guided` 로 스택 이름·리전·IAM 생성 허용 확인
- [ ] 배포 후 Outputs에서 ApiEndpoint 확인
- [ ] (선택) POST /create, GET /{shortCode} 로 동작 확인 (DynamoDB 연동 전에는 placeholder 응답)
