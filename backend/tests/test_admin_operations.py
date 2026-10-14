"""Admin screens: user provisioning and CSV question import."""

from httpx import AsyncClient

from app.models.user import User, UserRole

from tests.test_exam_engine import auth_header


def _admin(users: list[User]) -> User:
    return next(u for u in users if u.role == UserRole.ADMIN)


async def test_create_user_without_password_returns_temporary_password(async_client: AsyncClient, seed_users):
    admin = _admin(seed_users)
    r = await async_client.post("/api/users", headers=auth_header(admin), json={
        "full_name": "New Student", "email": "new.student@example.edu", "role": "candidate", "batch_year": 2026,
    })
    assert r.status_code == 201, r.text
    temp = r.json()["temporary_password"]
    assert temp and len(temp) >= 12
    assert r.json()["institution_id"] == str(admin.institution_id)
    login = await async_client.post("/api/auth/login", json={"email": "new.student@example.edu", "password": temp})
    assert login.status_code == 200


async def test_create_user_with_password_does_not_echo_it(async_client: AsyncClient, seed_users):
    r = await async_client.post("/api/users", headers=auth_header(_admin(seed_users)), json={
        "full_name": "Proctor Two", "email": "p2@example.edu", "role": "proctor", "password": "ChosenPass123",
    })
    assert r.status_code == 201
    assert r.json()["temporary_password"] is None


async def test_csv_import_accepts_aliases_and_reports_bad_rows(async_client: AsyncClient, seed_users):
    csv_text = (
        "\ufefftitle,content,type,difficulty,points,options,correct_answer\n"
        "Add,What is 1+1?,mcq,easy,2,1|2|3,2\n"
        "Capital,Capital of Japan?,,easy,1,,Tokyo\n"
        "Primes,Pick primes,multi,medium,2,2|4|5,2|5\n"
        ",missing title,mcq,easy,1,a|b,a\n"
        "Bad answer,x,mcq,easy,1,a|b,c\n"
        "Bad type,x,crossword,easy,1,,x\n"
    )
    r = await async_client.post("/api/questions/bulk", headers=auth_header(_admin(seed_users)),
                                files={"file": ("q.csv", csv_text.encode(), "text/csv")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["inserted"] == 3
    assert [e["line"] for e in body["errors"]] == [5, 6, 7]

    listing = (await async_client.get("/api/questions", headers=auth_header(_admin(seed_users)))).json()
    items = listing if isinstance(listing, list) else listing.get("items", [])
    types = {q["title"]: q["type"] for q in items}
    assert types == {"Add": "MCQ_SINGLE", "Capital": "SHORT_ANSWER", "Primes": "MCQ_MULTI"}


async def test_csv_import_with_no_valid_rows_explains_why(async_client: AsyncClient, seed_users):
    r = await async_client.post("/api/questions/bulk", headers=auth_header(_admin(seed_users)),
                                files={"file": ("q.csv", b"title,type,options,correct_answer\nX,mcq,a,a\n", "text/csv")})
    assert r.status_code == 400
    assert "line 2" in r.json()["detail"]
