🚀 AI 기반 지능형 URL 단축 및 분석 시스템 (Surl)

본 프로젝트는 AWS 서버리스 아키텍처를 기반으로 설계된 전문적인 URL 관리 및 분석 솔루션입니다. 단순한 경로 단축 기능을 넘어, AWS Bedrock(Claude 3 Haiku)을 통한 실시간 트래픽 분석과 CloudWatch 기반의 통합 운영 모니터링 체계를 제공합니다.

🌟 주요 기능 (Key Features)

효율적인 URL 관리: 장문의 URL을 고유 코드로 변환하여 관리 효율성을 극대화합니다.

데이터 기반 분석: 하이퍼링크 접근 시 발생하는 모든 이벤트를 데이터베이스에 기록하여 분석을 위한 기초 자료를 생성합니다.

AI 동향 분석 리포트: 수집된 접속 로그를 인공지능이 분석하여 유입 경로와 트렌드를 정성적으로 보고합니다.

통합 운영 대시보드:

Traffic Gauge: 최근 24시간 동안의 누적 트래픽을 가시화하여 운영 현황을 실시간으로 파악합니다.

Latency p90: 상위 90% 백분위 지연 시간을 모니터링하여 서비스 안정성과 사용자 경험을 관리합니다.

실시간 AI 리포트: 분석된 최신 동향 데이터를 표 형식으로 제공하여 의사결정을 지원합니다.

시스템 경보 시스템: 임계치를 초과하는 오류 발생 시 즉각적인 알림을 통해 신속한 장애 대응을 가능케 합니다.

🏗 시스템 아키텍처 (Architecture)

언어 및 환경: Python 3.12 (AWS Lambda)

데이터 저장소: AWS DynamoDB (NoSQL)

인공지능 엔진: AWS Bedrock (Anthropic Claude 3 Haiku)

모니터링 체계: AWS CloudWatch Dashboards & Alarms

배포 프레임워크: AWS SAM (Serverless Application Model)

🛠 배포 및 설치 가이드 (Deployment)

필수 선행 조건

AWS CLI 및 SAM CLI 환경 구성이 필요합니다.

AWS Bedrock 서비스 내 Claude 3 모델에 대한 접근 권한이 활성화되어 있어야 합니다 (서울 리전 권장).

배포 절차

소스 코드 복제

git clone https://github.com/seoulcloud/Surl-project.git


빌드 및 배포 실행

sam build
sam deploy --guided


📊 운영 지침 (Operations)

배포 완료 후 AWS 관리 콘솔의 CloudWatch 메뉴에서 Surl-Integrated-Management-Dashboard를 통해 시스템을 관리할 수 있습니다.

트래픽 분석: 대시보드 내 게이지 위젯은 24시간 기준의 누적 요청량을 합산하여 표기합니다.

성능 최적화: 지연 시간 그래프를 통해 AI 분석 등 고부하 프로세스의 처리 효율을 정기적으로 점검할 수 있습니다.

📝 라이선스 (License)

본 프로젝트는 MIT License를 따르며, 해당 규정에 의거하여 자유로운 복제 및 수정이 가능합니다.
