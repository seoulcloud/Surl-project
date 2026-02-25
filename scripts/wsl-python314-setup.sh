#!/bin/bash
# WSL에서 Windows에 설치된 Python 3.14를 python3.14 로 쓰기 위한 설정
# 사용법: bash scripts/wsl-python314-setup.sh  (프로젝트 루트에서)
# 또는: source scripts/wsl-python314-setup.sh

WIN_PY314="/mnt/c/Users/JAESHIN/AppData/Local/Python/bin/python3.14.exe"
BASHRC="$HOME/.bashrc"
MARKER="# Use Windows Python 3.14 (surl-project)"

if [ ! -x "$WIN_PY314" ]; then
  echo "경로에 실행 파일이 없습니다: $WIN_PY314"
  exit 1
fi

if grep -q "$MARKER" "$BASHRC" 2>/dev/null; then
  echo "이미 설정되어 있습니다. (python3.14 alias)"
  exit 0
fi

echo "" >> "$BASHRC"
echo "$MARKER" >> "$BASHRC"
echo "alias python3.14=\"$WIN_PY314\"" >> "$BASHRC"
echo "설정 추가됨. 아래 명령으로 적용하세요:"
echo "  source ~/.bashrc"
echo "이후: python3.14 -V"
