import pytest
from fastapi.testclient import TestClient
from api import app
from database import Base, engine, SessionLocal

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    # Здесь можно добавить логику очистки таблиц после тестов


def get_admin_token():
    # Предполагаем, что пользователь 'admin' с паролем 'admin' уже существует
    response = client.post("/auth/login", data={"username": "admin", "password": "admin"})
    return response.json().get("access_token")


def test_register_success():
    response = client.post("/auth/register", json={
        "username": "testuser_new",
        "password": "password123",
        "role": "student"
    })
    assert response.status_code == 200
    assert response.json()["message"] == "User created successfully"


def test_register_duplicate_username():
    client.post("/auth/register", json={"username": "dup", "password": "123", "role": "student"})
    response = client.post("/auth/register", json={"username": "dup", "password": "123", "role": "student"})
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_get_students_unauthorized():
    response = client.get("/students")
    assert response.status_code == 401


def test_get_students_with_token():
    token = get_admin_token()
    response = client.get("/students", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "students" in response.json()


def test_setup_db_admin_required():
    client.post("/auth/register", json={"username": "student_user", "password": "123", "role": "read_only"})
    login_res = client.post("/auth/login", data={"username": "student_user", "password": "123"})
    token = login_res.json()["access_token"]

    response = client.post("/setup?file_path=students.csv", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403  # Forbidden


def test_setup_db_success_background():
    token = get_admin_token()
    response = client.post("/setup?file_path=students.csv", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "started in background" in response.json()["message"]


def test_delete_student_not_found():
    token = get_admin_token()
    response = client.delete("/students/999999", headers={"Authorization": f"Bearer {token}"})
    # В нашей реализации delete_student просто делает commit, если объекта нет.
    # Обычно возвращают 200 или 404. Проверим на успешный вызов.
    assert response.status_code == 200


def test_delete_student_unauthorized():
    response = client.delete("/students/1")
    assert response.status_code == 401


def test_bulk_delete_invalid_data():
    token = get_admin_token()
    # Передаем строку вместо списка ID
    response = client.post("/students/bulk-delete", json={"student_ids": "not-a-list"},
                           headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422


def test_bulk_delete_success():
    token = get_admin_token()
    response = client.post("/students/bulk-delete", json={"student_ids": [1, 2, 3]},
                           headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "Bulk deletion" in response.json()["message"]