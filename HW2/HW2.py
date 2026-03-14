from datetime import datetime
from typing import List, Union, Optional
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, ValidationError


class UserRegistration(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=20,
        pattern=r'^[a-zA-Z0-9_]+$',
        description="Только латинские буквы, цифры и подчеркивание"
    )
    email: EmailStr
    password: str = Field(min_length=8)
    password_confirm: str = Field(exclude=True)

    age: int = Field(ge=18, le=120)

    registration_date: datetime = Field(default_factory=datetime.now)

    real_name: str = Field(min_length=2)
    phone_number: str = Field(pattern=r'^\+\d-\d{3}-\d{2}-\d{2}$')

    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.islower() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        return v

    @field_validator('real_name')
    @classmethod
    def validate_real_name(cls, v: str) -> str:
        if not v[0].isupper():
            raise ValueError('Имя должно начинаться с заглавной буквы')
        return v

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'UserRegistration':
        if self.password != self.password_confirm:
            raise ValueError('Пароли не совпадают')
        return self


def register_user(data: dict) -> Union[UserRegistration, List[dict]]:
    try:
        user = UserRegistration(**data)
        return user
    except ValidationError as e:
        # Возвращаем список ошибок в читаемом формате
        return e.errors()


if __name__ == "__main__":
    registration_data = {
        "username": "backend_dev",
        "email": "dev@example.com",
        "password": "SecurePassword1",
        "password_confirm": "SecurePassword1",
        "age": 25,
        "real_name": "Алексей",
        "phone_number": "+7-999-123-45-67"
    }

    result = register_user(registration_data)

    if isinstance(result, UserRegistration):
        print("Пользователь успешно зарегистрирован:")
        print(result.model_dump_json(indent=4))
    else:
        print("Ошибки валидации:", result)