from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from models import Student, Faculty, Subject, Grade, SessionLocal, fill_db_from_csv, Base, engine
from io import StringIO
from jose import JWTError, jwt
from auth_router import router as auth_router
from security import SECRET_KEY, ALGORITHM
from database import get_db, engine
from sqlalchemy.orm import Session
from models import User
from fastapi.security import OAuth2PasswordBearer
import csv

app = FastAPI()
Base.metadata.create_all(bind=engine)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
app.include_router(auth_router)


@app.get("/export-csv")
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

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=exported_students.csv"}
    )


@app.post("/setup")
def setup_db(db: Session = Depends(get_db)):
    fill_db_from_csv("students.csv", db)
    return {"status": "success", "message": "Database populated"}


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


@app.get("/students")
def get_students(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.username}, here are the students."}


@app.post("/students")
def create_student(student_data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    return {"message": "Student created"}


@app.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    return {"message": "Student deleted"}
