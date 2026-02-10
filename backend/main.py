import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional

# Import everything from your clean models file
from models import (
    Base, UserDB, TaskDB, 
    UserCreate, TaskCreate, TaskUpdate, 
    LoginRequest, DeleteRequest, 
    LocationUpdate, ItemSearch
)
from store_logic import find_nearby_deals

# --- DATABASE SETUP ---
# Render provides DATABASE_URL, otherwise use local SQLite file
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nextoyou.db")

# Fix for Render's postgres:// vs sqlalchemy's postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"status": "NextToYou Server is Online (SQL Active)"}

# --- AUTH ENDPOINTS ---
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    new_user = UserDB(
        username=user.username,
        password=user.password,
        active_start_hour=user.active_start_hour,
        active_end_hour=user.active_end_hour,
        notification_radius=user.notification_radius
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered", "user": user}

@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == req.username).first()
    if not user or user.password != req.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_data = {
        "username": user.username,
        "active_start_hour": user.active_start_hour,
        "active_end_hour": user.active_end_hour,
        "notification_radius": user.notification_radius,
        "password": user.password
    }
    return {"message": "Login successful", "user": user_data}

@app.post("/delete-account")
def delete_account(req: DeleteRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == req.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.password != req.password:
        raise HTTPException(status_code=401, detail="Wrong password")

    db.delete(user)
    db.query(TaskDB).filter(TaskDB.user_id == req.username).delete()
    db.commit()
    return {"message": "Account deleted"}

# --- TASK ENDPOINTS ---
@app.get("/tasks/{user_id}")
def get_tasks(user_id: str, db: Session = Depends(get_db)):
    tasks = db.query(TaskDB).filter(TaskDB.user_id == user_id).all()
    return [{"id": str(t.id), "title": t.title, "category": t.category, "is_completed": t.is_completed} for t in tasks]

@app.post("/tasks")
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    new_task = TaskDB(
        title=task.title,
        category=task.category,
        is_completed=task.is_completed,
        user_id=task.user_id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return {"id": str(new_task.id), "title": new_task.title, "category": new_task.category}

@app.put("/tasks/{task_id}")
def update_task(task_id: str, update: TaskUpdate, db: Session = Depends(get_db)):
    try:
        t_id = int(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Task ID")

    task = db.query(TaskDB).filter(TaskDB.id == t_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if update.title:
        task.title = update.title
    if update.category:
        task.category = update.category
        
    db.commit()
    db.refresh(task)
    return {"id": str(task.id), "title": task.title, "category": task.category}

@app.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    try:
        t_id = int(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Task ID")
        
    task = db.query(TaskDB).filter(TaskDB.id == t_id).first()
    if task:
        db.delete(task)
        db.commit()
    return {"status": "deleted"}

# --- PROXIMITY ---
@app.post("/check-proximity")
def check_proximity(loc: LocationUpdate, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == loc.user_id).first()
    radius = user.notification_radius if user else 50

    tasks = db.query(TaskDB).filter(TaskDB.user_id == loc.user_id, TaskDB.is_completed == False).all()
    user_task_titles = [t.title for t in tasks]
    
    if not user_task_titles:
        return {"message": "No active tasks."}

    deals = find_nearby_deals(loc.latitude, loc.longitude, user_task_titles, radius=radius)
    return {"nearby": deals}

@app.post("/search-item")
def search_item(search: ItemSearch):
    deals = find_nearby_deals(search.latitude, search.longitude, [search.item_name], radius=20000)
    return {"results": deals}