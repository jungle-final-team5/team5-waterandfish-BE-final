#!/usr/bin/env python3

import json
import subprocess
import sys
import os
import argparse
from pathlib import Path

def load_server_config():
    """서버 설정 로드"""
    config_path = "/home/ubuntu/team5-waterandfish-BE/config/websocket_servers.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def run_command(cmd, check=True):
    """명령어 실행"""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False

def install_systemd_service():
    """systemd 서비스 템플릿 설치"""
    service_file = "/home/ubuntu/team5-waterandfish-BE/scripts/websocket-server@.service"
    target_file = "/etc/systemd/system/websocket-server@.service"
    
    print("Installing systemd service template...")
    
    # 서비스 파일 복사
    success = run_command(["sudo", "cp", service_file, target_file])
    if not success:
        return False
    
    # systemd 리로드
    return run_command(["sudo", "systemctl", "daemon-reload"])

def enable_services(start_port=None, end_port=None, ports=None):
    """서비스 활성화"""
    config = load_server_config()
    
    if ports:
        target_ports = ports
    else:
        target_ports = []
        for server in config['servers']:
            port = server['port']
            if server['enabled']:
                if start_port and port < start_port:
                    continue
                if end_port and port > end_port:
                    continue
                target_ports.append(port)
    
    print(f"Enabling services for ports: {target_ports}")
    
    success_count = 0
    for port in target_ports:
        service_name = f"websocket-server@{port}"
        if run_command(["sudo", "systemctl", "enable", service_name], check=False):
            success_count += 1
        else:
            print(f"Failed to enable service for port {port}")
    
    print(f"Successfully enabled {success_count}/{len(target_ports)} services")
    return success_count == len(target_ports)

def start_services(start_port=None, end_port=None, ports=None):
    """서비스 시작"""
    config = load_server_config()
    
    if ports:
        target_ports = ports
    else:
        target_ports = []
        for server in config['servers']:
            port = server['port']
            if server['enabled']:
                if start_port and port < start_port:
                    continue
                if end_port and port > end_port:
                    continue
                target_ports.append(port)
    
    print(f"Starting services for ports: {target_ports}")
    
    success_count = 0
    for port in target_ports:
        service_name = f"websocket-server@{port}"
        if run_command(["sudo", "systemctl", "start", service_name], check=False):
            success_count += 1
        else:
            print(f"Failed to start service for port {port}")
    
    print(f"Successfully started {success_count}/{len(target_ports)} services")
    return success_count == len(target_ports)

def stop_services(start_port=None, end_port=None, ports=None):
    """서비스 중지"""
    config = load_server_config()
    
    if ports:
        target_ports = ports
    else:
        target_ports = []
        for server in config['servers']:
            port = server['port']
            if start_port and port < start_port:
                continue
            if end_port and port > end_port:
                continue
            target_ports.append(port)
    
    print(f"Stopping services for ports: {target_ports}")
    
    success_count = 0
    for port in target_ports:
        service_name = f"websocket-server@{port}"
        if run_command(["sudo", "systemctl", "stop", service_name], check=False):
            success_count += 1
        else:
            print(f"Failed to stop service for port {port}")
    
    print(f"Successfully stopped {success_count}/{len(target_ports)} services")

def status_services(start_port=None, end_port=None, ports=None):
    """서비스 상태 확인"""
    config = load_server_config()
    
    if ports:
        target_ports = ports
    else:
        target_ports = []
        for server in config['servers']:
            port = server['port']
            if start_port and port < start_port:
                continue
            if end_port and port > end_port:
                continue
            target_ports.append(port)
    
    print(f"Checking status for ports: {target_ports[:10]}{'...' if len(target_ports) > 10 else ''}")
    
    active_count = 0
    for port in target_ports:
        service_name = f"websocket-server@{port}"
        result = subprocess.run(
            ["sudo", "systemctl", "is-active", service_name],
            capture_output=True, text=True
        )
        
        status = result.stdout.strip()
        if status == "active":
            active_count += 1
            print(f"  Port {port}: ✅ {status}")
        else:
            print(f"  Port {port}: ❌ {status}")
    
    print(f"\nSummary: {active_count}/{len(target_ports)} services are active")

def main():
    parser = argparse.ArgumentParser(description='Manage WebSocket systemd services')
    parser.add_argument('action', choices=['install', 'enable', 'start', 'stop', 'status', 'restart'])
    parser.add_argument('--start-port', type=int, help='Start port range')
    parser.add_argument('--end-port', type=int, help='End port range')
    parser.add_argument('--ports', nargs='*', type=int, help='Specific ports')
    
    args = parser.parse_args()
    
    if args.action == 'install':
        success = install_systemd_service()
        sys.exit(0 if success else 1)
    
    elif args.action == 'enable':
        success = enable_services(args.start_port, args.end_port, args.ports)
        sys.exit(0 if success else 1)
    
    elif args.action == 'start':
        success = start_services(args.start_port, args.end_port, args.ports)
        sys.exit(0 if success else 1)
    
    elif args.action == 'stop':
        stop_services(args.start_port, args.end_port, args.ports)
    
    elif args.action == 'restart':
        stop_services(args.start_port, args.end_port, args.ports)
        success = start_services(args.start_port, args.end_port, args.ports)
        sys.exit(0 if success else 1)
    
    elif args.action == 'status':
        status_services(args.start_port, args.end_port, args.ports)

if __name__ == "__main__":
    main()
