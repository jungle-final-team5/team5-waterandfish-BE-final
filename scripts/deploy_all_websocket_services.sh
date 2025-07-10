#!/bin/bash

# 모든 웹소켓 서비스 배포 스크립트
echo "=== 웹소켓 서비스 전체 배포 시작 ==="

cd /home/ubuntu/team5-waterandfish-BE

# 1. 기존 프로세스 정리
echo "1. 기존 프로세스 정리 중..."
./scripts/cleanup_websocket_ports.sh

# 2. 가상환경 활성화 및 설정 생성
echo "2. 서버 설정 생성 중..."
source venv/bin/activate
python3 scripts/generate_server_config.py

# 3. systemd 서비스 설치
echo "3. systemd 서비스 설치 중..."
python3 scripts/manage_websocket_services.py install

# 4. 모든 서비스 활성화
echo "4. 모든 서비스 활성화 중..."
python3 scripts/manage_websocket_services.py enable --start-port 9001 --end-port 9099

# 5. 배치로 서비스 시작 (시스템 부하 방지)
echo "5. 서비스 배치 시작 중..."

# 첫 번째 배치 (9001-9020)
echo "  첫 번째 배치 시작 (9001-9020)..."
python3 scripts/manage_websocket_services.py start --start-port 9001 --end-port 9020
sleep 5

# 두 번째 배치 (9021-9040)
echo "  두 번째 배치 시작 (9021-9040)..."
python3 scripts/manage_websocket_services.py start --start-port 9021 --end-port 9040
sleep 5

# 세 번째 배치 (9041-9060)
echo "  세 번째 배치 시작 (9041-9060)..."
python3 scripts/manage_websocket_services.py start --start-port 9041 --end-port 9060
sleep 5

# 네 번째 배치 (9061-9080)
echo "  네 번째 배치 시작 (9061-9080)..."
python3 scripts/manage_websocket_services.py start --start-port 9061 --end-port 9080
sleep 5

# 다섯 번째 배치 (9081-9099)
echo "  다섯 번째 배치 시작 (9081-9099)..."
python3 scripts/manage_websocket_services.py start --start-port 9081 --end-port 9099
sleep 5

# 6. 전체 상태 확인
echo "6. 전체 서비스 상태 확인 중..."
python3 scripts/manage_websocket_services.py status --start-port 9001 --end-port 9099

echo "=== 웹소켓 서비스 전체 배포 완료 ==="
