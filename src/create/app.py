"""
URL 단축 생성 람다
POST /create -> 원본 URL을 받아 단축 코드 반환
"""

import json
import os
import sys

# 공통 모듈 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.base62 import encode


def handler(event, context):
    """Lambda 진입점"""
    try:
        body = json.loads(event.get("body", "{}"))
        original_url = body.get("url", "").strip()
        if not original_url:
            return _response(400, {"error": "url is required"})

        # TODO: DynamoDB에 저장 후 ID 기반 Base62 인코딩
        short_id = 1  # placeholder
        short_code = encode(short_id)

        return _response(200, {"shortCode": short_code, "originalUrl": original_url})
    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
