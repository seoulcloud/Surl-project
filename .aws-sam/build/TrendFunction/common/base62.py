"""
Base62 인코딩/디코딩 (URL 단축용)
문자集: 0-9, a-z, A-Z (62자)
"""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)


def encode(num: int) -> str:
    """정수 -> Base62 문자열"""
    if num == 0:
        return ALPHABET[0]
    result = []
    while num > 0:
        result.append(ALPHABET[num % BASE])
        num //= BASE
    return "".join(reversed(result))


def decode(s: str) -> int:
    """Base62 문자열 -> 정수"""
    num = 0
    for char in s:
        num = num * BASE + ALPHABET.index(char)
    return num
