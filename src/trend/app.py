"""
트렌드 분석 람다
GET /trend -> SurlClickLogsTable 최근 24시간(기본) 데이터 수집 후 Bedrock AI로 리포트 생성
"""

import json
import os
from decimal import Decimal
from datetime import datetime, timedelta, timezone

import boto3

_DYNAMO = boto3.resource("dynamodb")
_BEDROCK = boto3.client("bedrock-runtime", region_name="ap-northeast-2")


class DecimalEncoder(json.JSONEncoder):
    """DynamoDB 응답의 Decimal 타입을 JSON 직렬화 가능한 타입으로 변환."""
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
    """최근 N분 클릭 로그 조회 (기본 24시간)."""
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
    """Bedrock(Claude)에게 트렌드 분석 요청."""
    try:
        # 시간 단위 변환 (분 -> 시간)
        hours = minutes // 60
        time_desc = f"{hours}시간" if hours > 0 else f"{minutes}분"
        
        prompt = f"""
다음은 지난 {time_desc} 동안 우리 서비스에서 발생한 URL 클릭 카테고리 통계 데이터야:
{json.dumps(stats, ensure_ascii=False)}

이 데이터를 바탕으로 현재 사용자들의 관심 트렌드를 분석해서
1. 가장 인기 있는 분야
2. 클릭 사유 추측
3. 한 줄 요약
을 작성해줘.
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
        text = parsed["content"][0]["text"].strip()
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
        # 1. 최근 24시간(기본) 클릭 로그 조회
        query = event.get("queryStringParameters") or {}
        try:
            # 쿼리 파라미터가 없으면 기본값 1440(24시간) 사용
            minutes = int(query.get("minutes", 1440))
        except (TypeError, ValueError):
            minutes = 1440
        
        # 최소 1분 ~ 최대 7일(10080분) 제한
        minutes = max(1, min(10080, minutes))

        items = _fetch_recent_clicks(minutes=minutes)

        if not items:
            return _response(200, {
                "message": f"최근 {minutes}분 동안의 데이터가 없습니다.",
                "stats": {},
                "ai_analysis": None,
            })

        # 2. 카테고리 통계
        stats = _aggregate_by_category(items)

        # 3. AI 분석
        try:
            ai_analysis = _ask_ai_trend(stats, minutes=minutes)
            
            # [핵심] 대시보드 위젯용 로그 출력
            # 이 형식을 지켜야 CloudWatch Dashboard의 Log 위젯에 표시됩니다.
            print(f"분석 결과: {ai_analysis}")
            
        except Exception as e:
            ai_analysis = f"(AI 분석 실패: {e})"

        return _response(200, {
            "stats": stats,
            "ai_analysis": ai_analysis,
        })

    except Exception as e:
        print(f"DEBUG handler error: {e}")
        return _response(500, {"error": str(e)})