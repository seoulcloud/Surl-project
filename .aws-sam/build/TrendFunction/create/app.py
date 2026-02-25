import json
import os
import boto3
import string
from datetime import datetime
from botocore.exceptions import ClientError

# --- AWS 리소스 초기화 ---
# Bedrock 클라이언트는 리전 설정이 필수입니다.
BEDROCK = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "ap-northeast-2"))
DYNAMO = boto3.resource("dynamodb")

# 환경 변수 로드 (template.yaml에 정의된 변수와 일치해야 함)
MAPPING_TABLE_NAME = os.environ.get("MAPPING_TABLE_NAME", "SurlMappingTable")
COUNTER_TABLE_NAME = os.environ.get("COUNTER_TABLE_NAME", "SurlCounter")
_COUNTER_KEY = "surl_id"

def encode(num):
    """숫자를 Base62 문자열로 변환 (단축 코드 생성용)"""
    chars = string.digits + string.ascii_letters
    if num == 0:
        return chars[0]
    arr = []
    base = len(chars)
    while num:
        num, rem = divmod(num, base)
        arr.append(chars[rem])
    arr.reverse()
    return ''.join(arr)

def _get_ai_analysis(url: str) -> dict:
    """Bedrock Claude 3 Haiku 모델을 호출하여 URL 분석 수행"""
    prompt = f"""
    Analyze the following URL and respond in JSON format.
    URL: {url}
    Result must include:
    - category: (IT, Shopping, Food, Finance, etc)
    - summary: (One-line summary in Korean)
    """

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    })

    try:
        response = BEDROCK.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=body
        )
        response_body = json.loads(response.get("body").read())
        raw_text = response_body['content'][0]['text'].strip()
        
        # 텍스트 내에서 JSON 부분만 추출하는 방어 로직
        if not raw_text.startswith('{'):
            start = raw_text.find('{')
            end = raw_text.rfind('}') + 1
            if start != -1 and end != -1:
                raw_text = raw_text[start:end]
            
        return json.loads(raw_text)
    except Exception as e:
        print(f"AI Analysis Error: {str(e)}")
        return {"category": "기타", "summary": "AI 분석 실패"}

def _get_next_id() -> int:
    """DynamoDB를 이용한 순차적 ID 생성 (Atomic Counter)"""
    table = DYNAMO.Table(COUNTER_TABLE_NAME)
    try:
        resp = table.update_item(
            Key={"counter_name": _COUNTER_KEY},
            UpdateExpression="SET last_id = if_not_exists(last_id, :zero) + :inc",
            ExpressionAttributeValues={":zero": 0, ":inc": 1},
            ReturnValues="UPDATED_NEW",
        )
        return int(resp["Attributes"]["last_id"])
    except Exception as e:
        print(f"Counter Update Error: {str(e)}")
        raise e

def _save_mapping(short_code: str, original_url: str, ai_result: dict) -> None:
    """단축 정보 및 AI 분석 결과를 DynamoDB에 저장"""
    table = DYNAMO.Table(MAPPING_TABLE_NAME)
    table.put_item(
        Item={
            "shortCode": short_code,
            "originalUrl": original_url,
            "category": ai_result.get("category", "기타"),
            "summary": ai_result.get("summary", "분석 없음"),
            "createdAt": datetime.now().isoformat()
        }
    )

def handler(event, context):
    """Lambda 핸들러 메인 함수"""
    print(f"Event: {json.dumps(event)}")
    try:
        # 요청 바디 파싱
        body = json.loads(event.get("body", "{}"))
        original_url = body.get("url", "").strip()
        
        if not original_url:
            return _response(400, {"error": "url 필드가 필요합니다."})

        # 1. 시퀀스 ID 획득 및 인코딩
        short_id = _get_next_id()
        short_code = encode(short_id)

        # 2. Bedrock AI 분석 실행
        ai_result = _get_ai_analysis(original_url)

        # 3. DB에 매핑 정보 저장
        _save_mapping(short_code, original_url, ai_result)

        # 4. 최종 URL 생성 및 응답
        host = event['headers'].get('Host', 'localhost')
        stage = event.get('requestContext', {}).get('stage', 'Prod')
        short_url = f"https://{host}/{stage}/{short_code}"

        return _response(201, {
            "shortCode": short_code, 
            "shortUrl": short_url,
            "originalUrl": original_url,
            "category": ai_result.get("category"),
            "summary": ai_result.get("summary")
        })

    except Exception as e:
        print(f"Execution Error: {str(e)}")
        return _response(500, {"error": "Internal Server Error", "details": str(e)})

def _response(status_code: int, body: dict) -> dict:
    """API Gateway 표준 응답 포맷"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, ensure_ascii=False),
    }