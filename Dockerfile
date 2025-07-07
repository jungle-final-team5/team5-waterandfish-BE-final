FROM --platform=linux/amd64 python:3.11-slim

RUN apt-get update && apt-get install -y gcc python3-dev

# 1. 작업 디렉토리 설정
WORKDIR /app

# 2. Poetry 설치
RUN pip install poetry

# 3. pyproject.toml, README.md 복사
COPY pyproject.toml README.md ./

# 4. 루트 패키지 포함 전체 의존성 설치 (리눅스 extras 사용)
RUN poetry config virtualenvs.create false \
  && poetry lock --no-cache --no-interaction \
  && poetry install --no-root --no-interaction --no-ansi --extras "linux"

COPY .env.production .env
# 5. 실제 코드 복사입니다
COPY ./src ./src

ENV PYTHONPATH=/app/src

# 6. 포트 오픈
EXPOSE 8000

# 7. FastAPI 앱 실행
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]