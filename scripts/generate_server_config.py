#!/usr/bin/env python3

import json
import boto3
import os
from typing import List, Dict

def get_available_models() -> List[str]:
    """S3에서 사용 가능한 모델 목록 조회"""
    try:
        s3 = boto3.client('s3')
        response = s3.list_objects_v2(Bucket='waterandfish-s3', Prefix='model-info/')
        
        models = []
        for obj in response.get('Contents', []):
            key = obj['Key']
            if key.endswith('.json') and key != 'model-info/':
                filename = os.path.basename(key)
                models.append(filename)
        
        return sorted(models)
    except Exception as e:
        print(f"Error fetching models from S3: {e}")
        return []

def generate_server_config(start_port: int = 9001, end_port: int = 9099) -> Dict:
    """서버 설정 파일 생성"""
    models = get_available_models()
    
    if not models:
        print("Warning: No models found in S3")
        return {"servers": []}
    
    servers = []
    port_range = end_port - start_port + 1
    
    for i in range(min(len(models), port_range)):
        port = start_port + i
        servers.append({
            "port": port,
            "model_info": models[i],
            "enabled": True
        })
    
    return {
        "servers": servers,
        "generated_at": "2025-07-09T15:40:00Z",
        "total_models": len(models),
        "assigned_ports": len(servers)
    }

if __name__ == "__main__":
    config = generate_server_config()
    
    # 설정 파일 저장
    config_path = "/home/ubuntu/team5-waterandfish-BE/config/websocket_servers.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Generated configuration for {len(config['servers'])} servers")
    print(f"Configuration saved to: {config_path}")
    
    # 요약 출력
    for server in config['servers'][:5]:  # 처음 5개만 출력
        print(f"  Port {server['port']}: {server['model_info']}")
    
    if len(config['servers']) > 5:
        print(f"  ... and {len(config['servers']) - 5} more servers")
