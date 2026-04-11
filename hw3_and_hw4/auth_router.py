from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
from models import User
from security import get_password_hash, verify_password, create_access_token, create_refresh_token
from pydantic import BaseModel
import traceback

router = APIRouter(prefix="/auth", tags=["auth"])


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "read_only"


@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.username == user.username).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")

        hashed_pwd = get_password_hash(user.password)
        new_user = User(username=user.username, hashed_password=hashed_pwd, role=user.role)
        db.add(new_user)
        db.commit()
        return {"message": "User created successfully"}

    except Exception as e:
        error_details = traceback.format_exc()
        return {"ОШИБКА": str(e), "ДЕТАЛИ": error_details}

@router.post("/test-pydantic")
def test_pydantic(user: UserCreate):
    return {"message": f"Супер! Pydantic работает, логин: {user.username}"}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.username})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout():
    return {"message": "Successfully logged out. Please delete your token on the client side."}