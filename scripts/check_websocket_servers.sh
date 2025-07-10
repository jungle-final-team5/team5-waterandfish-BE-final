#!/bin/bash

# 웹소켓 서버 상태 확인 스크립트
echo "=== 웹소켓 서버 상태 확인 ==="

# 프로세스 상태 확인
echo "1. 실행 중인 프로세스:"
ps aux | grep "sign_classifier_websocket_server.py" | grep -v grep

echo ""
echo "2. 포트 사용 상태:"
ss -tlnp | grep -E "(9001|9002)"

echo ""
echo "3. 최근 로그 (9001 포트):"
if [ -f "logs/websocket_9001.log" ]; then
    tail -5 logs/websocket_9001.log
else
    echo "9001 포트 로그 파일이 존재하지 않습니다."
fi

echo ""
echo "4. 최근 로그 (9002 포트):"
if [ -f "logs/websocket_9002.log" ]; then
    tail -5 logs/websocket_9002.log
else
    echo "9002 포트 로그 파일이 존재하지 않습니다."
fi

echo ""
echo "5. 연결 테스트:"
curl -s -o /dev/null -w "%{http_code}" http://localhost:9001 || echo "9001 포트: 웹소켓 서버 (HTTP 응답 없음은 정상)"
curl -s -o /dev/null -w "%{http_code}" http://localhost:9002 || echo "9002 포트: 웹소켓 서버 (HTTP 응답 없음은 정상)"

echo ""
echo "=== 상태 확인 완료 ==="
