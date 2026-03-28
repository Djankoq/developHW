from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, func
from sqlalchemy.orm import relationship, sessionmaker, DeclarativeBase, Session
import csv
from io import StringIO


DATABASE_URL = "sqlite:///./students.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass


class Faculty(Base):
    __tablename__ = 'faculties'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

    students = relationship("Student", back_populates="faculty")


class Student(Base):
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True)
    last_name = Column(String(100), nullable=False)
    first_name = Column(String(100), nullable=False)
    faculty_id = Column(Integer, ForeignKey('faculties.id'), nullable=False)

    faculty = relationship("Faculty", back_populates="students")
    grades = relationship("Grade", back_populates="student")


class Subject(Base):
    __tablename__ = 'subjects'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

    grades = relationship("Grade", back_populates="subject")


class Grade(Base):
    __tablename__ = 'grades'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    score = Column(Integer, nullable=False)

    student = relationship("Student", back_populates="grades")
    subject = relationship("Subject", back_populates="grades")


def fill_db_from_csv(file_path: str, db: Session):
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            fac = db.query(Faculty).filter(Faculty.name == row['Факультет']).first()
            if not fac:
                fac = Faculty(name=row['Факультет'])
                db.add(fac)
                db.flush()

            sub = db.query(Subject).filter(Subject.name == row['Курс']).first()
            if not sub:
                sub = Subject(name=row['Курс'])
                db.add(sub)
                db.flush()

            stu = db.query(Student).filter(
                Student.first_name == row['Имя'],
                Student.last_name == row['Фамилия'],
                Student.faculty_id == fac.id
            ).first()
            if not stu:
                stu = Student(first_name=row['Имя'], last_name=row['Фамилия'], faculty_id=fac.id)
                db.add(stu)
                db.flush()

            grade = Grade(student_id=stu.id, subject_id=sub.id, score=int(row['Оценка']))
            db.add(grade)

        db.commit()


def get_student(db: Session, student_id: int):
    return db.query(Student).filter(Student.id == student_id).first()


def update_grade(db: Session, grade_id: int, new_score: int):
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if grade:
        grade.score = new_score
        db.commit()
    return grade


def delete_student(db: Session, student_id: int):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student:
        db.delete(student)
        db.commit()


def get_students_by_faculty(db: Session, faculty_name: str):
    return db.query(Student).join(Faculty).filter(Faculty.name == faculty_name).all()


def get_unique_subjects(db: Session):
    return db.query(Subject.name).distinct().all()


def get_low_scorers(db: Session, subject_name: str):
    return db.query(Student).join(Grade).join(Subject) \
        .filter(Subject.name == subject_name, Grade.score < 30).all()


def get_faculty_avg_score(db: Session, faculty_name: str):
    result = db.query(func.avg(Grade.score)) \
        .join(Student, Grade.student_id == Student.id) \
        .join(Faculty, Student.faculty_id == Faculty.id) \
        .filter(Faculty.name == faculty_name).scalar()
    return result or 0
