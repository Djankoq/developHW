import csv
from io import StringIO
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

import redis.asyncio as redis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from database import get_db, engine, SessionLocal
from models import Base, User, Student, Faculty, Subject, Grade, fill_db_from_csv, delete_student
from auth_router import router as auth_router
from security import SECRET_KEY, ALGORITHM


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = redis.from_url("redis://localhost:6379", encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis_client), prefix="api-cache")
    yield


app = FastAPI(lifespan=lifespan)

Base.metadata.create_all(bind=engine)
app.include_router(auth_router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges. Admin role required."
        )
    return current_user


class BulkDeleteRequest(BaseModel):
    student_ids: list[int]


def bg_fill_db_task(file_path: str):
    """
    Фоновая задача для заполнения БД.
    ВАЖНО: Создается новая сессия SessionLocal(), так как
    сессия из запроса (Depends(get_db)) закроется сразу после ответа пользователю.
    """
    db = SessionLocal()
    try:
        fill_db_from_csv(file_path, db)
    finally:
        db.close()


def bg_delete_students_task(student_ids: list[int]):
    """Фоновая задача для массового удаления записей."""
    db = SessionLocal()
    try:
        for s_id in student_ids:
            delete_student(db, s_id)
    finally:
        db.close()


@app.post("/setup")
def setup_db(file_path: str, background_tasks: BackgroundTasks, current_user: User = Depends(get_admin_user)):
    """Принимает путь к файлу и запускает парсинг в фоне."""
    background_tasks.add_task(bg_fill_db_task, file_path)
    return {"status": "success", "message": f"Database population from '{file_path}' started in background"}


@app.get("/export-csv")
@cache(expire=60)
def export_data_to_csv(db: Session = Depends(get_db)):
    data = db.query(
        Student.last_name,
        Student.first_name,
        Faculty.name.label("faculty"),
        Subject.name.label("subject"),
        Grade.score
    ).join(Faculty).join(Grade).join(Subject).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Фамилия', 'Имя', 'Факультет', 'Курс', 'Оценка'])

    for row in data:
        writer.writerow([row.last_name, row.first_name, row.faculty, row.subject, row.score])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=exported_students.csv"}
    )


@app.get("/students")
@cache(expire=60)
def get_students(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    students = db.query(Student).limit(50).all()
    return {
        "message": f"Hello {current_user.username}, here are the students.",
        "students": [{"id": s.id, "name": f"{s.first_name} {s.last_name}"} for s in students]
    }


@app.post("/students")
def create_student(student_data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    return {"message": "Student created"}


@app.delete("/students/{student_id}")
def delete_single_student(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    delete_student(db, student_id)
    return {"message": f"Student {student_id} deleted"}


@app.post("/students/bulk-delete")
def delete_students_bulk(request: BulkDeleteRequest, background_tasks: BackgroundTasks,
                         current_user: User = Depends(get_admin_user)):
    """Принимает список ID студентов и удаляет их в фоновом режиме."""
    background_tasks.add_task(bg_delete_students_task, request.student_ids)
    return {"status": "success",
            "message": f"Bulk deletion of {len(request.student_ids)} students started in background"}
