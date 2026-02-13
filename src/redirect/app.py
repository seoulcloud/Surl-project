import json
import os
from datetime import datetime, timezone
import boto3

# [개선] 전역 변수 레벨에서 리소스 초기화 (Cold Start 성능 최적화)
_DYNAMO = boto3.resource("dynamodb")
_MAPPING_TABLE_NAME = os.environ.get("TABLE_NAME", "")
_LOG_TABLE_NAME = os.environ.get("LOG_TABLE_NAME", "")

# 테이블 객체 미리 로드
_MAPPING_TABLE = _DYNAMO.Table(_MAPPING_TABLE_NAME) if _MAPPING_TABLE_NAME else None
_LOG_TABLE = _DYNAMO.Table(_LOG_TABLE_NAME) if _LOG_TABLE_NAME else None

def _get_mapping_item(short_code: str) -> dict | None:
    """DynamoDB에서 shortCode에 해당하는 매핑 아이템 조회."""
    if not _MAPPING_TABLE:
        raise ValueError("TABLE_NAME is not set in environment variables")
    resp = _MAPPING_TABLE.get_item(Key={"shortCode": short_code})
    return resp.get("Item")

def _save_click_log(short_code: str, category: str, event: dict) -> None:
    """클릭 로그를 SurlClickLogsTable에 개별 Row로 저장."""
    # [수정] 위에서 정의한 전역 변수 _LOG_TABLE 사용
    if not _LOG_TABLE:
        return
    
    source = event.get("requestContext", {})
    identity = source.get("identity", {})
    ip = identity.get("sourceIp", "")
    
    _LOG_TABLE.put_item(
        Item={
            "shortCode": short_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "ip": ip,
        }
    )

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
            "Cache-Control": "no-cache",
        },
        "body": "",
    }

def handler(event, context):
    try:
        short_code = (event.get("pathParameters") or {}).get("shortCode", "").strip()
        if not short_code:
            return _response(400, {"error": "shortCode is required"})

        item = _get_mapping_item(short_code)
        if not item:
            return _response(404, {"error": "URL not found"})
        
        original_url = item.get("original_url")
        if not original_url:
            return _response(404, {"error": "URL not found"})
            
        category = item.get("category", "기타")

        # 로그 저장 프로세스 (메인 로직과 분리)
        try:
            _save_click_log(short_code, category, event)
        except Exception as log_error:
            print(f"Logging Failed: {log_error}") # 디버깅을 위해 에러 로그만 남김

        return _redirect_response(original_url)

    except Exception as e:
        print(f"Handler Error: {e}")
        return _response(500, {"error": "Internal Server Error"})