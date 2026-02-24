"""
트렌드 분석 람다
AI 분석 결과를 대시보드 파싱에 최적화된 형식으로 출력하도록 수정 및 안정성 강화
"""

import json
import os
from decimal import Decimal
from datetime import datetime, timedelta, timezone

import boto3

# 전역 리소스 초기화 (리전 명시)
_DYNAMO = boto3.resource("dynamodb")
_BEDROCK = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "ap-northeast-2"))


class DecimalEncoder(json.JSONEncoder):
    """DynamoDB의 Decimal 타입을 JSON으로 변환하기 위한 인코더"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def _get_log_table():
    """환경 변수로부터 로그 테이블 객체 로드"""
    try:
        name = os.environ.get("LOG_TABLE_NAME", "SurlClickLogsTable").strip()
        return _DYNAMO.Table(name)
    except Exception as e:
        print(f"DEBUG _get_log_table error: {e}")
        return None


def _fetch_recent_clicks(minutes: int = 1440) -> list:
    """최근 N분간의 클릭 로그를 Scan하여 가져옴"""
    try:
        table = _get_log_table()
        if not table:
            return []
            
        # UTC 기준 시간 계산
        since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        items = []
        
        # 필터링 파라미터 (timestamp는 예약어일 수 있으므로 #ts 사용)
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
    """카테고리별 클릭 횟수 집계"""
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
    """Bedrock Claude 3 Haiku를 사용하여 트렌드 분석 요청"""
    try:
        hours = minutes // 60
        time_desc = f"{hours}시간" if hours > 0 else f"{minutes}분"
        
        # 대시보드 파싱용 로그를 위한 엄격한 형식 지정
        prompt = f"""
다음은 지난 {time_desc} 동안의 URL 클릭 통계 데이터입니다:
{json.dumps(stats, ensure_ascii=False)}

위 데이터를 분석해서 반드시 아래의 형식을 엄격히 지켜서 한 줄로 답변하세요.
형식: [분야] 인기분야명 [사유] 분석사유 [요약] 전체트렌드요약
"""
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
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
        return f"[분야] 오류 [사유] {str(e)} [요약] 분석을 수행할 수 없습니다."


def _response(status_code: int, body_obj: dict) -> dict:
    """표준 API 응답 및 CORS 설정"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body_obj, ensure_ascii=False, cls=DecimalEncoder),
    }


def handler(event, context):
    """Trend Lambda 메인 핸들러"""
    try:
        query = event.get("queryStringParameters") or {}
        try:
            minutes = int(query.get("minutes", 1440))
        except (TypeError, ValueError):
            minutes = 1440
        
        # 분석 범위 제한 (1분 ~ 1주일)
        minutes = max(1, min(10080, minutes))
        
        # 1. 로그 데이터 수집
        items = _fetch_recent_clicks(minutes=minutes)

        if not items:
            return _response(200, {
                "message": "데이터 없음", 
                "stats": {}, 
                "ai_analysis": "[분야] 없음 [사유] 로그 데이터 부족 [요약] 현재 집계된 클릭 데이터가 없습니다."
            })

        # 2. 카테고리별 집계
        stats = _aggregate_by_category(items)

        # 3. AI 트렌드 분석
        ai_analysis = _ask_ai_trend(stats, minutes=minutes)
        
        # [중요] CloudWatch Logs에 대시보드 위젯이 파싱할 수 있는 마커 출력
        print(f"REPORT_DATA: {ai_analysis}")

        return _response(200, {
            "stats": stats, 
            "ai_analysis": ai_analysis,
            "count": len(items)
        })

    except Exception as e:
        print(f"DEBUG handler error: {e}")
        return _response(500, {"error": "Internal Server Error", "details": str(e)})