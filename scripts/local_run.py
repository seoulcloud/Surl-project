#!/usr/bin/env python3
"""
로컬 URL 단축 확인용 스크립트 (AWS 없이 SQLite + Python만 사용)

사용법:
  python3 scripts/local_run.py create "https://긴주소.com"
  python3 scripts/local_run.py get <short_code>
"""

import argparse
import os
import sqlite3
import sys
from typing import Optional

# 프로젝트 루트의 src 폴더를 경로에 추가 (base62 임포트용)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SRC = os.path.join(_PROJECT_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from common.base62 import encode, decode

# SQLite DB 파일 위치 (프로젝트 루트에 생성됨)
DB_PATH = os.path.join(_PROJECT_ROOT, "local_links.db")


def get_connection():
    """DB 연결 반환"""
    return sqlite3.connect(DB_PATH)


def init_db(conn):
    """처음 실행 시 테이블 생성"""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_url TEXT NOT NULL
        )
        """
    )
    conn.commit()


def create_short_url(url: str) -> str:
    """
    URL을 DB에 저장하고 짧은 코드(short_code)를 만들어 반환합니다.
    """
    url = (url or "").strip()
    if not url:
        raise ValueError("URL을 입력해 주세요.")

    conn = get_connection()
    try:
        init_db(conn)
        cursor = conn.execute("INSERT INTO links (original_url) VALUES (?)", (url,))
        conn.commit()
        row_id = cursor.lastrowid
        short_code = encode(row_id)
        print(f"  [Base62 인코딩] DB ID {row_id} → short_code \"{short_code}\"")
        return short_code
    finally:
        conn.close()


def get_original_url(short_code: str) -> Optional[str]:
    """
    short_code로 DB를 조회해 원본 URL을 반환합니다.
    없으면 None을 반환합니다.
    """
    short_code = (short_code or "").strip()
    if not short_code:
        return None

    try:
        row_id = decode(short_code)
        print(f"  [Base62 디코딩] short_code \"{short_code}\" → DB ID {row_id}")
    except (ValueError, KeyError):
        return None

    conn = get_connection()
    try:
        init_db(conn)
        row = conn.execute(
            "SELECT original_url FROM links WHERE id = ?", (row_id,)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="로컬 URL 단축: create(저장) / get(조회)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # create: URL 저장 후 short_code 출력
    p_create = sub.add_parser("create", help="URL을 저장하고 short_code를 받습니다")
    p_create.add_argument("url", help="단축할 원본 URL (따옴표로 감싸서 입력)")

    # get: short_code로 원본 URL 조회
    p_get = sub.add_parser("get", help="short_code로 원본 URL을 조회합니다")
    p_get.add_argument("short_code", help="단축 코드 (예: 1, 2, 1Z)")

    args = parser.parse_args()

    if args.command == "create":
        try:
            code = create_short_url(args.url)
            print(f"short_code: {code}")
        except ValueError as e:
            print(f"오류: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "get":
        url = get_original_url(args.short_code)
        if url is None:
            print("찾을 수 없습니다.", file=sys.stderr)
            sys.exit(1)
        print(url)


if __name__ == "__main__":
    main()
