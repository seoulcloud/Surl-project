"""
리다이렉트 람다
GET /{shortCode} -> 원본 URL로 302 리다이렉트
"""

import json
import os

import boto3

_DYNAMO = boto3.resource("dynamodb")


def _get_table():
    """매핑 테이블 반환. TABLE_NAME 미설정 시 ValueError."""
    table_name = os.environ.get("TABLE_NAME")
    if not table_name:
        raise ValueError("TABLE_NAME not set")
    return _DYNAMO.Table(table_name)


def _get_original_url(short_code: str) -> str | None:
    """DynamoDB에서 shortCode에 해당하는 원본 URL 조회. 없으면 None."""
    table = _get_table()
    resp = table.get_item(Key={"shortCode": short_code})
    item = resp.get("Item")
    if not item:
        return None
    return item.get("original_url")


def _response(status_code: int, body: dict) -> dict:
    """API Gateway JSON 에러 응답 포맷."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _redirect_response(location: str) -> dict:
    """302 리다이렉트 응답."""
    return {
        "statusCode": 302,
        "headers": {
            "Location": location,
            "Cache-Control": "no-cache",
        },
        "body": "",
    }


def handler(event, context):
    """Lambda 진입점: pathParameter shortCode로 원본 URL 조회 후 302 응답."""
    try:
        short_code = (event.get("pathParameters") or {}).get("shortCode", "").strip()
        if not short_code:
            return _response(400, {"error": "shortCode is required"})

        original_url = _get_original_url(short_code)
        if not original_url:
            return _response(404, {"error": "URL not found"})

        return _redirect_response(original_url)

    except Exception as e:
        return _response(500, {"error": str(e)})
