"""
URL 단축 생성 람다
POST /create -> 원본 URL을 받아 단축 코드 반환
"""

import json
import os
import sys
import boto3
from botocore.exceptions import ClientError

# 공통 모듈 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from common.base62 import encode
except ImportError:
    # 빌드 환경에 따라 경로가 달라질 수 있음을 대비
    from base62 import encode

# 1. 전역 변수 설정: 람다 컨테이너 재사용 시 커넥션 유지 (성능 최적화)
DYNAMO = boto3.resource("dynamodb")
COUNTER_TABLE_NAME = os.environ.get("COUNTER_TABLE_NAME")
MAPPING_TABLE_NAME = os.environ.get("TABLE_NAME")
_COUNTER_KEY = "url_id"

def _get_next_id() -> int:
    """카운터 테이블에서 원자적으로 다음 ID(1부터 순차) 획득"""
    if not COUNTER_TABLE_NAME:
        raise ValueError("COUNTER_TABLE_NAME 환경변수가 설정되지 않았습니다.")
    
    table = DYNAMO.Table(COUNTER_TABLE_NAME)
    # Atomic Counter 업데이트 로직
    resp = table.update_item(
        Key={"counter_name": _COUNTER_KEY},
        UpdateExpression="SET #seq = if_not_exists(#seq, :zero) + :inc",
        ExpressionAttributeNames={"#seq": "seq"},
        ExpressionAttributeValues={":zero": 0, ":inc": 1},
        ReturnValues="UPDATED_NEW",
    )
    return int(resp["Attributes"]["seq"])

def _save_mapping(short_code: str, original_url: str) -> None:
    """매핑 테이블에 shortCode -> original_url 저장"""
    if not MAPPING_TABLE_NAME:
        raise ValueError("TABLE_NAME 환경변수가 설정되지 않았습니다.")
    
    table = DYNAMO.Table(MAPPING_TABLE_NAME)
    table.put_item(
        Item={
            "shortCode": short_code,
            "original_url": original_url,
        }
    )

def handler(event, context):
    """Lambda 진입점"""
    try:
        # 1. 입력값 검증
        body = json.loads(event.get("body", "{}"))
        original_url = body.get("url", "").strip()
        
        if not original_url:
            return _response(400, {"error": "url 필드가 필요합니다."})

        # 2. 다음 순번의 ID 가져오기 (Atomic Counter)
        short_id = _get_next_id()
        
        # 3. 숫자를 Base62 코드로 변환
        short_code = encode(short_id)
        
        # 4. DynamoDB에 매핑 정보 저장
        _save_mapping(short_code, original_url)

        # 5. 성공 응답
        return _response(200, {
            "shortCode": short_code, 
            "originalUrl": original_url,
            "counter": short_id
        })

    except ClientError as e:
        # AWS 리소스 관련 에러 (권한, 테이블 부재 등)
        print(f"AWS Error: {e.response['Error']['Message']}")
        return _response(500, {"error": "Internal Database Error"})
    except Exception as e:
        # 기타 모든 예외
        print(f"Unexpected Error: {str(e)}")
        return _response(500, {"error": str(e)})

def _response(status_code: int, body: dict) -> dict:
    """API Gateway 응답 포맷 유틸리티"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"  # CORS 대응용
        },
        "body": json.dumps(body),
    }