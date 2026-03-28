from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from models import Student, Faculty, Subject, Grade, SessionLocal, fill_db_from_csv, Base, engine
from io import StringIO
from sqlalchemy.orm import Session
import csv

app = FastAPI()
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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