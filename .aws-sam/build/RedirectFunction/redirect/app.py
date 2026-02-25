import json
import os
from datetime import datetime, timezone
import boto3

# 전역 리소스 초기화
_DYNAMO = boto3.resource("dynamodb")

def _get_table(env_name):
    """환경변수로부터 테이블 객체 안전하게 로드"""
    table_name = os.environ.get(env_name)
    if not table_name:
        print(f"DEBUG ERROR: Environment variable {env_name} is missing!")
        return None
    return _DYNAMO.Table(table_name)

def _save_click_log(short_code: str, category: str, event: dict) -> None:
    """클릭 로그 저장 로직"""
    try:
        # 템플릿의 변수명 LOG_TABLE_NAME 사용
        log_table = _get_table("LOG_TABLE_NAME")
        if log_table is None:
            return

        # IP 추출
        request_context = event.get("requestContext", {})
        identity = request_context.get("identity", {})
        ip = identity.get("sourceIp", "unknown")
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # DynamoDB 저장
        log_table.put_item(
            Item={
                "shortCode": short_code,
                "timestamp": timestamp,
                "category": category,
                "ip": ip,
            }
        )
        print(f"DEBUG SUCCESS: Log saved for {short_code}")

    except Exception as e:
        print(f"DEBUG ERROR in _save_click_log: {str(e)}")

def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body),
    }

def _redirect_response(location: str) -> dict:
    return {
        "statusCode": 302,
        "headers": {
            "Location": location,
            "Cache-Control": "no-cache",
        },
        "body": "",
    }

def handler(event, context):
    """Lambda 진입점"""
    try:
        # 1. Path Parameter 추출
        path_params = event.get("pathParameters") or {}
        short_code = path_params.get("shortCode", "").strip()
        
        if not short_code:
            return _response(400, {"error": "shortCode is required"})

        # 2. 매핑 테이블 조회 (환경변수명 MAPPING_TABLE_NAME으로 수정)
        mapping_table = _get_table("MAPPING_TABLE_NAME")
        if not mapping_table:
            return _response(500, {"error": "Server configuration error"})

        resp = mapping_table.get_item(Key={"shortCode": short_code})
        item = resp.get("Item")

        if not item:
            return _response(404, {"error": "URL not found"})

        # [중요] create/app.py의 저장 필드명과 일치시킴
        original_url = item.get("originalUrl") 
        category = item.get("category", "기타")

        if not original_url:
            return _response(404, {"error": "Original URL missing in record"})

        # 3. 로그 저장
        _save_click_log(short_code, category, event)

        # 4. 리다이렉트 응답
        return _redirect_response(original_url)

    except Exception as e:
        print(f"DEBUG HANDLER ERROR: {str(e)}")
        return _response(500, {"error": "Internal Server Error", "details": str(e)})