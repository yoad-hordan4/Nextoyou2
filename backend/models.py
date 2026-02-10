from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional

# --- DATABASE MODELS (SQLAlchemy) ---
Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    active_start_hour = Column(Integer, default=8)
    active_end_hour = Column(Integer, default=22)
    notification_radius = Column(Integer, default=50)

class TaskDB(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    category = Column(String, default="Supermarket")
    is_completed = Column(Boolean, default=False)
    user_id = Column(String, index=True)

# --- API SCHEMAS (Pydantic) ---
class UserCreate(BaseModel):
    username: str
    password: str
    active_start_hour: int = 8
    active_end_hour: int = 22
    notification_radius: int = 50

class TaskCreate(BaseModel):
    title: str
    category: str = "Supermarket"
    is_completed: bool = False
    user_id: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class DeleteRequest(BaseModel):
    username: str
    password: str

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float
    user_id: str

class ItemSearch(BaseModel):
    latitude: float
    longitude: float
    item_name: str