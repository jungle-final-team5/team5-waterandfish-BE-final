#!/bin/bash

# 웹소켓 서버 포트 정리 스크립트
echo "=== 웹소켓 서버 포트 정리 중 ==="

# 9000-9010 포트 범위의 프로세스 확인
for port in {9000..9010}; do
    PID=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$PID" ]; then
        echo "포트 $port에서 실행 중인 프로세스 (PID: $PID) 종료 중..."
        kill -9 $PID 2>/dev/null
        sleep 1
    fi
done

# 웹소켓 서버 프로세스 직접 종료
echo "웹소켓 서버 프로세스 직접 종료 중..."
pkill -f "sign_classifier_websocket_server.py" 2>/dev/null
pkill -f "webrtc_signaling_server.py" 2>/dev/null

echo "=== 포트 정리 완료 ==="

# 포트 사용 상태 확인
echo "=== 현재 포트 사용 상태 ==="
ss -tuln | grep -E ':900[0-9]|:901[0-9]' || echo "웹소켓 포트 사용 없음"
