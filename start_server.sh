#!/bin/bash

echo "========================================="
echo "SeoulLog 백엔드 서버 시작"
echo "========================================="
echo ""

# conda 환경 활성화
source ~/miniconda3/etc/profile.d/conda.sh
conda activate genminute

# FastAPI 의존성 설치 (없으면)
pip install fastapi uvicorn[standard] pydantic python-multipart -q

echo "서버 시작 중..."
echo "http://localhost:8000 에서 접속 가능합니다."
echo ""
echo "서버를 종료하려면 Ctrl+C를 누르세요."
echo "========================================="

# 서버 실행
python backend_server.py
