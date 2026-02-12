import json
import os
import sys
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

# --- Bedrock 설정 ---
BEDROCK = boto3.client("bedrock-runtime", region_name="ap-northeast-2")

def _get_ai_analysis(url: str) -> dict:
    """Bedrock(Claude 3 Haiku)을 사용하여 URL 분석"""
    # 프롬프트를 조금 더 명확하게 수정
    prompt = f"""
    다음 URL의 성격을 분석해서 JSON 형식으로 응답해줘.
    URL: {url}
    결과는 반드시 다음 키를 포함하는 JSON 형태여야 해:
    - category: (IT, 쇼핑, 맛집, 금융, 기타 중 택1)
    - summary: (한 줄 요약)
    """

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1, # 일관성을 위해 온도를 낮춤
    })

    try:
        response = BEDROCK.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=body
        )
        response_body = json.loads(response.get("body").read())
        raw_text = response_body['content'][0]['text'].strip()
        
        # [수정] AI가 보낸 텍스트에서 JSON 부분만 추출하거나 그대로 로드
        # 만약 AI가 텍스트를 섞어 보냈을 경우를 대비해 간단히 정제
        if not raw_text.startswith('{'):
            # 텍스트 내에서 { } 구간을 찾는 로직 (방어적 코드)
            start = raw_text.find('{')
            end = raw_text.rfind('}') + 1
            raw_text = raw_text[start:end]
            
        return json.loads(raw_text)
        
    except Exception as e:
        print(f"AI Analysis Error: {e}")
        # 에러 시 로깅용으로 원본 텍스트 출력 (디버깅용)
        try: print(f"Raw AI Output: {raw_text}")
        except: pass
        return {"category": "기타", "summary": "분석 실패"}

# --- 공통 모듈 설정 ---
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from common.base62 import encode
except ImportError:
    from base62 import encode

# --- 리소스 초기화 ---
DYNAMO = boto3.resource("dynamodb")
COUNTER_TABLE_NAME = os.environ.get("COUNTER_TABLE_NAME")
MAPPING_TABLE_NAME = os.environ.get("TABLE_NAME")
_COUNTER_KEY = "url_id"

def _get_next_id() -> int:
    table = DYNAMO.Table(COUNTER_TABLE_NAME)
    resp = table.update_item(
        Key={"counter_name": _COUNTER_KEY},
        UpdateExpression="SET #seq = if_not_exists(#seq, :zero) + :inc",
        ExpressionAttributeNames={"#seq": "seq"},
        ExpressionAttributeValues={":zero": 0, ":inc": 1},
        ReturnValues="UPDATED_NEW",
    )
    return int(resp["Attributes"]["seq"])

def _save_mapping(short_code: str, original_url: str, ai_result: dict) -> None:
    """매핑 데이터 저장 (AI 결과 포함)"""
    table = DYNAMO.Table(MAPPING_TABLE_NAME)
    table.put_item(
        Item={
            "shortCode": short_code,
            "original_url": original_url,
            "category": ai_result.get("category"),
            "summary": ai_result.get("summary"),
            "created_at": datetime.now().isoformat()
        }
    )

def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        original_url = body.get("url", "").strip()
        
        if not original_url:
            return _response(400, {"error": "url 필드가 필요합니다."})

        # 1. AI 분석 먼저 수행
        ai_result = _get_ai_analysis(original_url)

        # 2. ID 생성 및 코드 변환
        short_id = _get_next_id()
        short_code = encode(short_id)
        
        # 3. DB 저장 (ai_result를 인자로 전달)
        _save_mapping(short_code, original_url, ai_result)

        # 4. 성공 응답 (AI 결과 포함)
        return _response(200, {
            "shortCode": short_code, 
            "originalUrl": original_url,
            "category": ai_result.get("category"),
            "summary": ai_result.get("summary")
        })

    except ClientError as e:
        print(f"AWS Error: {e.response['Error']['Message']}")
        return _response(500, {"error": "Internal Database Error"})
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
        return _response(500, {"error": str(e)})

def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, ensure_ascii=False),
    }