import boto3
import os
import tempfile
import logging
from urllib.parse import urlparse
from typing import Optional
from dotenv import load_dotenv
import json


logger = logging.getLogger(__name__)

load_dotenv()

class S3Utils:
    def __init__(self):
        """S3 유틸리티 초기화"""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'ap-northeast-2')
        )
    
    def download_file_from_s3(self, s3_url: str, local_path: Optional[str] = None) -> str:
        """
        S3 URL에서 파일을 다운로드합니다.
        
        Args:
            s3_url: S3 URL (예: s3://bucket-name/path/to/file)
            local_path: 로컬 저장 경로 (None이면 임시 파일 생성)
            
        Returns:
            다운로드된 파일의 로컬 경로
        """
        try:
            # S3 URL 파싱
            parsed_url = urlparse(s3_url)
            if parsed_url.scheme != 's3':
                raise ValueError(f"Invalid S3 URL: {s3_url}")
            
            bucket_name = parsed_url.netloc
            key = parsed_url.path.lstrip('/')
            
            # 로컬 경로 설정
            if local_path is None:
                # 임시 파일 생성
                temp_dir = tempfile.gettempdir()
                filename = os.path.basename(key)
                local_path = os.path.join(temp_dir, filename)
            
            # 디렉토리 생성
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            logger.info(f"📥 S3에서 파일 다운로드 중: {s3_url} -> {local_path}")
            
            # 파일 다운로드
            self.s3_client.download_file(bucket_name, key, local_path)
            
            logger.info(f"✅ 파일 다운로드 완료: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"❌ S3 파일 다운로드 실패: {e}")
            raise
    
    def file_exists_in_s3(self, s3_url: str) -> bool:
        """
        S3에 파일이 존재하는지 확인합니다.
        
        Args:
            s3_url: S3 URL
            
        Returns:
            파일 존재 여부
        """
        try:
            parsed_url = urlparse(s3_url)
            if parsed_url.scheme != 's3':
                return False
            
            bucket_name = parsed_url.netloc
            key = parsed_url.path.lstrip('/')
            
            # 파일 존재 확인
            self.s3_client.head_object(Bucket=bucket_name, Key=key)
            return True
            
        except Exception:
            return False
    
    def get_file_size(self, s3_url: str) -> Optional[int]:
        """
        S3 파일의 크기를 반환합니다.
        
        Args:
            s3_url: S3 URL
            
        Returns:
            파일 크기 (바이트), 파일이 없으면 None
        """
        try:
            parsed_url = urlparse(s3_url)
            if parsed_url.scheme != 's3':
                return None
            
            bucket_name = parsed_url.netloc
            key = parsed_url.path.lstrip('/')
            
            response = self.s3_client.head_object(Bucket=bucket_name, Key=key)
            return response['ContentLength']
            
        except Exception:
            return None

    def upload_video_and_label(self, label: str, video_file) -> tuple:
        """
        영상과 라벨 JSON을 S3에 업로드합니다.
        Args:
            label: 라벨명
            video_file: FastAPI UploadFile 객체
        Returns:
            (video_url, label_url)
        """
        bucket = "waterandfish-s3"
        video_key = f"uploaded-src/{label}/{video_file.filename}"
        self.s3_client.upload_fileobj(video_file.file, bucket, video_key)
        video_url = f"s3://{bucket}/{video_key}"

        label_key = f"labels/{label}.json"
        label_data = {"label": label, "video": video_file.filename}
        self.s3_client.put_object(Body=json.dumps(label_data), Bucket=bucket, Key=label_key)
        label_url = f"s3://{bucket}/{label_key}"
        return video_url, label_url

# 전역 인스턴스
s3_utils = S3Utils() 