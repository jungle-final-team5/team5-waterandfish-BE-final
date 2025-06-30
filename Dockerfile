FROM python:3.12-slim

WORKDIR /app

# Poetry 설치
RUN pip install poetry

# pyproject.toml, poetry.lock 복사 및 의존성 설치
COPY pyproject.toml poetry.lock ./
COPY README.md ./
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

# 소스 코드 복사
COPY ./src ./src

EXPOSE 8000

CMD ["uvicorn", "team5_waterandfish_be.main:app", "--host", "0.0.0.0", "--port", "8000"] 