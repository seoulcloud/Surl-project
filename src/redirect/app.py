"""
리다이렉트 람다
GET /{shortCode} -> 원본 URL로 302 리다이렉트
"""

import json
import os
import sys

# 공통 모듈 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.base62 import decode


def handler(event, context):
    """Lambda 진입점"""
    try:
        short_code = event.get("pathParameters", {}).get("shortCode", "")
        if not short_code:
            return _response(404, {"error": "shortCode not found"})

        # TODO: DynamoDB에서 shortCode로 원본 URL 조회
        original_url = "https://example.com"  # placeholder

        return {
            "statusCode": 302,
            "headers": {"Location": original_url},
            "body": "",
        }
    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
