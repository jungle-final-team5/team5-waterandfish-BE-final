#!/bin/bash

# 빌드 최적화 스크립트
set -e

echo "🚀 Starting optimized build process..."

# 이전 이미지 캐시 활용
echo "📦 Pulling latest image for cache..."
docker pull team5-waterandfish-be:latest || echo "No previous image found, building from scratch"

# 빌드 캐시 활용하여 이미지 빌드
echo "🔨 Building Docker image with cache optimization..."
docker build \
  --cache-from team5-waterandfish-be:latest \
  --tag team5-waterandfish-be:latest \
  --tag team5-waterandfish-be:$(date +%Y%m%d-%H%M%S) \
  .

echo "✅ Build completed successfully!"

# 선택적: 컨테이너 실행
if [ "$1" = "--run" ]; then
  echo "🐳 Starting container..."
  docker run -d \
    --name waterandfish-backend \
    -p 8000:8000 \
    team5-waterandfish-be:latest
  echo "✅ Container started on port 8000"
fi

echo "🎉 Build process completed!" 