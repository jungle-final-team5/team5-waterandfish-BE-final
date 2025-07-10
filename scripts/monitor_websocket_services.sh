#!/bin/bash

# 웹소켓 서비스 모니터링 스크립트
echo "=== 웹소켓 서비스 모니터링 ==="

cd /home/ubuntu/team5-waterandfish-BE

# 활성 서비스 수 확인
ACTIVE_COUNT=$(sudo systemctl list-units --type=service --state=active | grep websocket-server@ | wc -l)
TOTAL_COUNT=$(sudo systemctl list-units --type=service --all | grep websocket-server@ | wc -l)

echo "활성 서비스: $ACTIVE_COUNT/$TOTAL_COUNT"

# 포트 사용 상태 확인
echo ""
echo "포트 사용 상태:"
LISTENING_PORTS=$(ss -tlnp | grep -E "900[0-9]" | wc -l)
echo "리스닝 포트: $LISTENING_PORTS"

# 실패한 서비스 확인
echo ""
echo "실패한 서비스:"
sudo systemctl list-units --type=service --state=failed | grep websocket-server@ || echo "실패한 서비스 없음"

# 메모리 사용량 확인
echo ""
echo "메모리 사용량:"
ps aux | grep "websocket_server_wrapper.py" | grep -v grep | awk '{sum+=$6} END {print "총 메모리 사용량: " sum/1024 " MB"}'

# 최근 로그 에러 확인
echo ""
echo "최근 에러 로그:"
sudo journalctl -u "websocket-server@*" --since "5 minutes ago" --priority err --no-pager | tail -10 || echo "최근 에러 없음"

echo ""
echo "=== 모니터링 완료 ==="
