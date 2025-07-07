# 멀티스테이지 빌드: 빌드 스테이지
FROM --platform=linux/amd64 python:3.11-slim as builder

# 빌드 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Poetry 설치
RUN pip install poetry

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일들만 먼저 복사 (레이어 캐싱 최적화)
COPY pyproject.toml poetry.lock ./

# 가상환경 생성 및 의존성 설치
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-root --no-interaction --no-ansi --extras "linux"

# 런타임 스테이지
FROM --platform=linux/amd64 python:3.11-slim

# 런타임 의존성만 설치
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 빌드 스테이지에서 가상환경 복사
COPY --from=builder /app/.venv /app/.venv

# 환경 변수 설정
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src

# 애플리케이션 코드 복사
COPY ./src ./src
COPY .env.production .env

# 포트 오픈
EXPOSE 8000

# FastAPI 앱 실행
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]