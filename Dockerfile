FROM python:3.12-slim

# 1. 작업 디렉토리 설정
WORKDIR /app

# 2. Poetry 설치
RUN pip install poetry

# 3. pyproject.toml, poetry.lock, README.md 복사
COPY pyproject.toml poetry.lock README.md ./

# 4. 루트 패키지 포함 전체 의존성 설치
RUN poetry config virtualenvs.create false \
  && poetry install --no-root --no-interaction --no-ansi

# 5. 실제 코드 복사
COPY ./src ./src

ENV PYTHONPATH=/app/src

# 6. 포트 오픈
EXPOSE 8000

# 7. FastAPI 앱 실행
CMD ["uvicorn", "team5_waterandfish_be.main:app", "--host", "0.0.0.0", "--port", "8000"]