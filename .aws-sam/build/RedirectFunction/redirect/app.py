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
    """클릭 로그 저장 로직 (상세 디버깅 포함)"""
    try:
        log_table = _get_table("LOG_TABLE_NAME")
        if log_table is None:
            return

        # REST API 구조에서 IP 및 컨텍스트 추출
        request_context = event.get("requestContext", {})
        identity = request_context.get("identity", {})
        ip = identity.get("sourceIp", "unknown")
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        print(f"DEBUG START: Attempting to save log to {log_table.table_name}")
        print(f"DEBUG DATA: shortCode={short_code}, timestamp={timestamp}, category={category}, ip={ip}")

        # DynamoDB 저장 실행
        log_table.put_item(
            Item={
                "shortCode": short_code,
                "timestamp": timestamp,
                "category": category,
                "ip": ip,
            }
        )
        print("DEBUG SUCCESS: Log saved to DynamoDB successfully.")

    except Exception as e:
        # 에러 발생 시 상세 내용을 CloudWatch에 기록
        print(f"DEBUG CRITICAL ERROR in _save_click_log: {str(e)}")

def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }

def _redirect_response(location: str) -> dict:
    return {
        "statusCode": 302,
        "headers": {
            "Location": location,
            "Cache-Control": "no-cache", # 매번 클릭이 기록되도록 캐시 방지
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

        # 2. 매핑 테이블 조회
        mapping_table = _get_table("TABLE_NAME")
        if not mapping_table:
            return _response(500, {"error": "Server configuration error (TABLE_NAME)"})

        resp = mapping_table.get_item(Key={"shortCode": short_code})
        item = resp.get("Item")

        if not item:
            return _response(404, {"error": "URL not found"})

        original_url = item.get("original_url")
        category = item.get("category", "기타")

        # 3. 로그 저장 (비동기 효과를 위해 에러 격리)
        _save_click_log(short_code, category, event)

        # 4. 리다이렉트 응답
        return _redirect_response(original_url)

    except Exception as e:
        print(f"DEBUG HANDLER ERROR: {str(e)}")
        return _response(500, {"error": "Internal Server Error"})