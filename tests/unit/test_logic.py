"""
로컬 유닛 테스트 - Base62 및 핵심 로직 검증
"""

import sys
import os

# src/common 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from common.base62 import encode, decode


def test_encode_decode_roundtrip():
    """encode -> decode 시 원래 숫자로 복원되는지 검증"""
    for num in [0, 1, 61, 62, 100, 1000, 123456]:
        assert decode(encode(num)) == num, f"Failed for num={num}"


def test_encode_specific_values():
    """알려진 값 검증"""
    assert encode(0) == "0"
    assert encode(1) == "1"
    assert encode(61) == "Z"
    assert encode(62) == "10"


def test_decode_specific_values():
    """알려진 문자열 검증"""
    assert decode("0") == 0
    assert decode("1") == 1
    assert decode("Z") == 61
    assert decode("10") == 62


if __name__ == "__main__":
    test_encode_decode_roundtrip()
    test_encode_specific_values()
    test_decode_specific_values()
    print("All tests passed.")
