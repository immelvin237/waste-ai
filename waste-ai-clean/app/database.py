import os
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "waste.db")

engine = create_engine("sqlite:///" + DB_PATH, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
Base = declarative_base()


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    class_detected = Column(String)
    confidence = Column(Float)
    image_filename = Column(String, nullable=True)
    is_synced = Column(Boolean, default=False)

    def dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "class_detected": self.class_detected,
            "confidence": self.confidence,
            "image_filename": self.image_filename,
            "is_synced": self.is_synced,
        }


def init_db():
    Base.metadata.create_all(engine)


def db_size():
    return os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
