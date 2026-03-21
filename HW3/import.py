import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Faculty, Student, Subject, Grade

engine = create_engine('sqlite:///students_db.db')
Session = sessionmaker(bind=engine)
session = Session()

df = pd.read_csv('students.csv')

for _, row in df.iterrows():
    faculty = session.query(Faculty).filter_by(name=row['Факультет']).first()
    if not faculty:
        faculty = Faculty(name=row['Факультет'])
        session.add(faculty)
        session.flush()

    student = session.query(Student).filter_by(
        last_name=row['Фамилия'],
        first_name=row['Имя'],
        faculty_id=faculty.id
    ).first()
    if not student:
        student = Student(last_name=row['Фамилия'], first_name=row['Имя'], faculty_id=faculty.id)
        session.add(student)
        session.flush()

    subject = session.query(Subject).filter_by(name=row['Курс']).first()
    if not subject:
        subject = Subject(name=row['Курс'])
        session.add(subject)
        session.flush()

    grade = Grade(student_id=student.id, subject_id=subject.id, score=row['Оценка'])
    session.add(grade)

session.commit()
print("Данные успешно загружены!")