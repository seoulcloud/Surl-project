"""
트렌드 분석 람다
AI 분석 결과를 대시보드 파싱에 최적화된 형식으로 출력하도록 수정
"""

import json
import os
from decimal import Decimal
from datetime import datetime, timedelta, timezone

import boto3

_DYNAMO = boto3.resource("dynamodb")
_BEDROCK = boto3.client("bedrock-runtime", region_name="ap-northeast-2")


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def _get_log_table():
    try:
        name = os.environ.get("LOG_TABLE_NAME", "").strip()
        if not name:
            return None
        return _DYNAMO.Table(name)
    except Exception as e:
        print(f"DEBUG _get_log_table error: {e}")
        return None


def _fetch_recent_clicks(minutes: int = 1440) -> list:
    try:
        table = _get_log_table()
        if not table:
            return []
        since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        items = []
        params = {
            "FilterExpression": "#ts > :since",
            "ExpressionAttributeNames": {"#ts": "timestamp"},
            "ExpressionAttributeValues": {":since": since},
        }
        while True:
            resp = table.scan(**params)
            items.extend(resp.get("Items", []))
            if "LastEvaluatedKey" not in resp:
                break
            params["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
        return items
    except Exception as e:
        print(f"DEBUG _fetch_recent_clicks error: {e}")
        return []


def _aggregate_by_category(items: list) -> dict:
    try:
        stats = {}
        for item in items:
            cat = item.get("category", "기타")
            stats[cat] = stats.get(cat, 0) + 1
        return stats
    except Exception as e:
        print(f"DEBUG _aggregate_by_category error: {e}")
        return {}


def _ask_ai_trend(stats: dict, minutes: int = 1440) -> str:
    """Bedrock에게 엄격한 형식으로 답변 요청."""
    try:
        hours = minutes // 60
        time_desc = f"{hours}시간" if hours > 0 else f"{minutes}분"
        
        # AI에게 구분자(|)를 사용한 한 줄 형식을 강제함
        prompt = f"""
다음은 지난 {time_desc} 동안의 URL 클릭 통계 데이터야:
{json.dumps(stats, ensure_ascii=False)}

위 데이터를 분석해서 반드시 아래의 형식을 엄격히 지켜서 한 줄로 답변해줘. 다른 말은 하지마.
형식: [분야] 인기있는분야내용 [사유] 클릭사유추측내용 [요약] 전체트렌드한줄요약
"""
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        })
        resp = _BEDROCK.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=body,
        )
        parsed = json.loads(resp.get("body").read())
        text = parsed["content"][0]["text"].strip().replace("\n", " ")
        return text
    except Exception as e:
        print(f"DEBUG _ask_ai_trend error: {e}")
        raise


def _response(status_code: int, body_obj: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_obj, ensure_ascii=False, cls=DecimalEncoder),
    }


def handler(event, context):
    try:
        query = event.get("queryStringParameters") or {}
        try:
            minutes = int(query.get("minutes", 1440))
        except (TypeError, ValueError):
            minutes = 1440
        
        minutes = max(1, min(10080, minutes))
        items = _fetch_recent_clicks(minutes=minutes)

        if not items:
            return _response(200, {"message": "데이터 없음", "stats": {}, "ai_analysis": None})

        stats = _aggregate_by_category(items)

        try:
            ai_analysis = _ask_ai_trend(stats, minutes=minutes)
            # 대시보드 파싱용 로그 출력 (구분자 포함)
            print(f"REPORT_DATA: {ai_analysis}")
        except Exception as e:
            ai_analysis = f"AI Error: {e}"

        return _response(200, {"stats": stats, "ai_analysis": ai_analysis})

    except Exception as e:
        print(f"DEBUG handler error: {e}")
        return _response(500, {"error": str(e)})