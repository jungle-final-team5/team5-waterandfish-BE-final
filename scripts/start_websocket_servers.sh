#!/bin/bash

# 웹소켓 서버 시작 스크립트
echo "=== 웹소켓 서버 시작 중 ==="

# 프로젝트 디렉토리로 이동
cd /home/ubuntu/team5-waterandfish-BE

# 가상환경 활성화
source venv/bin/activate

# 기존 프로세스 정리
./scripts/cleanup_websocket_ports.sh

# 로그 디렉토리 생성
mkdir -p logs

# 웹소켓 서버 1 시작 (포트 9001)
echo "9001 포트에서 웹소켓 서버 시작 중..."
python3 src/services/sign_classifier_websocket_server.py \
    --port 9001 \
    --env "model-info-20250704_150939.json" \
    --log-level INFO \
    > logs/websocket_9001.log 2>&1 &

# 웹소켓 서버 2 시작 (포트 9002)
echo "9002 포트에서 웹소켓 서버 시작 중..."
python3 src/services/sign_classifier_websocket_server.py \
    --port 9002 \
    --env "model-info-20250704_150423.json" \
    --log-level INFO \
    > logs/websocket_9002.log 2>&1 &

# 서버 시작 대기
echo "서버 시작 대기 중..."
sleep 5

# 서버 상태 확인
echo "=== 서버 상태 확인 ==="
ps aux | grep "sign_classifier_websocket_server.py" | grep -v grep
ss -tlnp | grep -E "(9001|9002)"

echo "=== 웹소켓 서버 시작 완료 ==="
echo "9001 포트 로그: logs/websocket_9001.log"
echo "9002 포트 로그: logs/websocket_9002.log"
