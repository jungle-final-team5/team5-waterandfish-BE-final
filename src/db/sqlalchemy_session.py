from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from typing import Generator
from ..models.user import Base

# 데이터베이스 URL (환경변수에서 가져오거나 기본값 사용)
DATABASE_URL = "postgresql://user:password@localhost/waterandfish_db"

# 엔진 생성
engine = create_engine(DATABASE_URL)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_sqlalchemy_db() -> Generator[Session, None, None]:
    """SQLAlchemy 데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """데이터베이스 테이블 생성"""
    Base.metadata.create_all(bind=engine) 