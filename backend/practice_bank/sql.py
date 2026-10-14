"""SQL problems (SQLite). Each test case is a dataset of INSERT statements run
against the problem's schema; expected rows come from the reference query."""

from datetime import date, timedelta

from practice_bank.common import E, H, M, JudgeMode, problem, rng

HR_SCHEMA = """\
CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER REFERENCES departments(id),
    salary INTEGER NOT NULL,
    manager_id INTEGER REFERENCES employees(id)
);"""

SHOP_SCHEMA = """\
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT,
    email TEXT
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    amount REAL NOT NULL,
    ordered_on TEXT NOT NULL  -- ISO date, e.g. '2026-03-14'
);"""

LOGIN_SCHEMA = """\
CREATE TABLE logins (
    user_id INTEGER NOT NULL,
    login_date TEXT NOT NULL  -- ISO date; a user may log in several times a day
);"""

FIRST = ["Asha", "Ben", "Chen", "Dina", "Eli", "Farah", "Gopal", "Hana", "Ivan", "Jia", "Kofi", "Lena",
         "Maya", "Nikhil", "Omar", "Priya", "Quinn", "Ravi", "Sara", "Tomas", "Uma", "Vik", "Wen", "Yusuf", "Zoe"]
DEPTS = ["Engineering", "Finance", "Marketing", "Operations", "Research", "Sales", "Support"]
CITIES = ["Pune", "Leeds", "Austin", "Osaka", None]


def sql_value(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, str):
        return "'" + v.replace("'", "''") + "'"
    return repr(v)


def inserts(table: str, cols: list[str], rows: list[tuple]) -> str:
    if not rows:
        return ""
    values = ",\n  ".join("(" + ", ".join(sql_value(v) for v in row) + ")" for row in rows)
    return f"INSERT INTO {table} ({', '.join(cols)}) VALUES\n  {values};"


def hr(departments: list[tuple], employees: list[tuple]) -> str:
    return "\n".join(filter(None, [
        inserts("departments", ["id", "name"], departments),
        inserts("employees", ["id", "name", "department_id", "salary", "manager_id"], employees),
    ]))


def shop(customers: list[tuple], orders: list[tuple]) -> str:
    return "\n".join(filter(None, [
        inserts("customers", ["id", "name", "city", "email"], customers),
        inserts("orders", ["id", "customer_id", "amount", "ordered_on"], orders),
    ]))


def random_hr(n_depts: int, n_emps: int, salary_choices: list[int] | None = None) -> str:
    depts = [(i + 1, DEPTS[i % len(DEPTS)] + ("" if i < len(DEPTS) else f" {i}")) for i in range(n_depts)]
    emps = []
    for i in range(1, n_emps + 1):
        dept = rng.choice([d[0] for d in depts] + [None]) if depts else None
        salary = rng.choice(salary_choices) if salary_choices else rng.randint(30, 150) * 1000
        manager = rng.randint(1, i - 1) if i > 1 and rng.random() < 0.8 else None
        emps.append((i, f"{rng.choice(FIRST)} {i}", dept, salary, manager))
    return hr(depts, emps)


def random_shop(n_customers: int, n_orders: int) -> str:
    customers = [
        (i, f"{rng.choice(FIRST)} {i}", rng.choice(CITIES), f"user{rng.randint(1, n_customers // 2 + 1)}@mail.test")
        for i in range(1, n_customers + 1)
    ]
    start = date(2025, 1, 1)
    orders = [
        (i, rng.randint(1, n_customers), round(rng.uniform(5, 500), 2), (start + timedelta(days=rng.randint(0, 540))).isoformat())
        for i in range(1, n_orders + 1)
    ]
    return shop(customers, orders)


def random_logins(n_users: int, days: int) -> str:
    start = date(2026, 1, 1)
    rows = []
    for user in range(1, n_users + 1):
        for d in range(days):
            if rng.random() < 0.45:
                rows.extend([(user, (start + timedelta(days=d)).isoformat())] * rng.randint(1, 2))
    rng.shuffle(rows)
    return inserts("logins", ["user_id", "login_date"], rows)


SMALL_HR = hr(
    [(1, "Engineering"), (2, "Sales"), (3, "Research")],
    [(1, "Asha", 1, 95000, None), (2, "Ben", 1, 70000, 1), (3, "Chen", 2, 52000, 1),
     (4, "Dina", 2, 48000, 3), (5, "Eli", 1, 95000, 1), (6, "Farah", None, 61000, 1)],
)


def sql_problem(**kw):
    problem(judge_mode=JudgeMode.SQL, starter_code={"sql": "-- Write a single SQLite SELECT statement.\nSELECT\n"}, **kw)


# ---------------------------------------------------------------- EASY

sql_problem(
    slug="sql-high-earners", title="High Earners (SQL)", difficulty=E, tags=["sql", "filtering", "sorting"],
    statement="Return the `name` of every employee whose `salary` is **greater than 50000**, sorted by `name` in ascending order.",
    hints=["`WHERE` filters rows; `ORDER BY name` sorts them."],
    sql_schema=HR_SCHEMA, compare="exact",
    reference="SELECT name FROM employees WHERE salary > 50000 ORDER BY name;",
    sql_samples=[(SMALL_HR, "Dina (48000) is excluded; the rest are sorted by name.")],
    sql_hidden=[hr([(1, "A")], []), hr([(1, "A")], [(1, "Zed", 1, 50000, None)]), random_hr(5, 300)],
)

sql_problem(
    slug="sql-customers-without-orders", title="Customers Without Orders (SQL)", difficulty=E, tags=["sql", "join", "subquery"],
    statement="Return the `name` of every customer who has **never placed an order**. Any row order is accepted.",
    hints=["A `LEFT JOIN` keeps customers with no matching order; their order columns are NULL."],
    sql_schema=SHOP_SCHEMA, compare="unordered",
    reference="SELECT c.name FROM customers c LEFT JOIN orders o ON o.customer_id = c.id WHERE o.id IS NULL;",
    sql_samples=[(shop([(1, "Asha", "Pune", "a@x.test"), (2, "Ben", "Leeds", None), (3, "Chen", None, "c@x.test")],
                       [(1, 1, 20.0, "2026-01-02"), (2, 1, 35.5, "2026-01-09")]), "Only Asha has ordered.")],
    sql_hidden=[shop([(1, "Solo", None, None)], []), random_shop(40, 60), random_shop(200, 120)],
)

sql_problem(
    slug="sql-department-headcount", title="Department Headcount (SQL)", difficulty=E, tags=["sql", "join", "aggregation"],
    statement=(
        "For **every** department (including departments with no employees) return its `name` and the number of employees "
        "in it as `headcount`. Sort by `headcount` descending, then `name` ascending."
    ),
    hints=["`LEFT JOIN` departments to employees and `COUNT(e.id)` — counting a column ignores NULLs."],
    sql_schema=HR_SCHEMA, compare="exact",
    reference=(
        "SELECT d.name, COUNT(e.id) AS headcount FROM departments d "
        "LEFT JOIN employees e ON e.department_id = d.id GROUP BY d.id, d.name ORDER BY headcount DESC, d.name;"
    ),
    sql_samples=[(SMALL_HR, "Research has nobody; Farah has no department so she isn't counted anywhere.")],
    sql_hidden=[hr([(1, "Empty")], []), random_hr(7, 80), random_hr(12, 500)],
)

sql_problem(
    slug="sql-total-spent", title="Total Spent per Customer (SQL)", difficulty=E, tags=["sql", "join", "aggregation"],
    statement=(
        "For each customer who has placed at least one order, return `name` and `total` — the sum of their order amounts "
        "rounded to 2 decimals. Sort by `total` descending, then `name` ascending."
    ),
    hints=["`GROUP BY` the customer and `ROUND(SUM(amount), 2)`."],
    sql_schema=SHOP_SCHEMA, compare="exact",
    reference=(
        "SELECT c.name, ROUND(SUM(o.amount), 2) AS total FROM customers c JOIN orders o ON o.customer_id = c.id "
        "GROUP BY c.id, c.name ORDER BY total DESC, c.name;"
    ),
    sql_samples=[(shop([(1, "Asha", "Pune", None), (2, "Ben", None, None), (3, "Chen", "Osaka", None)],
                       [(1, 1, 20.25, "2026-01-02"), (2, 2, 99.0, "2026-01-03"), (3, 1, 30.5, "2026-02-01")]), None)],
    sql_hidden=[shop([(1, "Solo", None, None)], []), random_shop(30, 200), random_shop(150, 1500)],
)

# ---------------------------------------------------------------- MEDIUM

sql_problem(
    slug="sql-second-highest-salary", title="Second Highest Salary (SQL)", difficulty=M, tags=["sql", "subquery"],
    statement=(
        "Return a single row with one column `second_highest`: the second highest **distinct** salary. "
        "If there is no such salary, the value must be `NULL` (still exactly one row).\n\n"
        "*The judge runs SQLite 3.36, where `DISTINCT … LIMIT 1 OFFSET 1` inside a subquery is unreliable — "
        "prefer `GROUP BY salary` or a `MAX(...)` comparison.*"
    ),
    hints=["The largest salary that is smaller than the overall maximum is the second highest — and `MAX` of nothing is NULL."],
    sql_schema=HR_SCHEMA, compare="exact",
    reference="SELECT MAX(salary) AS second_highest FROM employees WHERE salary < (SELECT MAX(salary) FROM employees);",
    sql_samples=[(SMALL_HR, "Distinct salaries: 95000, 70000, … — the second is 70000.")],
    sql_hidden=[hr([], []), hr([], [(1, "Only", None, 1000, None)]), hr([], [(1, "A", None, 5, None), (2, "B", None, 5, None)]),
                random_hr(4, 200)],
)

sql_problem(
    slug="sql-department-top-earners", title="Top Earner per Department (SQL)", difficulty=M, tags=["sql", "join", "subquery"],
    statement=(
        "For each department, return the department name as `department`, and the `name` and `salary` of the employee(s) with the "
        "highest salary in it. Include **all** employees tied for the top. Ignore employees without a department. Any row order."
    ),
    hints=["Compare each salary to the department's `MAX(salary)` (a correlated subquery or a joined aggregate)."],
    sql_schema=HR_SCHEMA, compare="unordered",
    reference=(
        "SELECT d.name AS department, e.name, e.salary FROM employees e JOIN departments d ON d.id = e.department_id "
        "WHERE e.salary = (SELECT MAX(salary) FROM employees x WHERE x.department_id = e.department_id);"
    ),
    sql_samples=[(SMALL_HR, "Asha and Eli tie in Engineering, so both are returned.")],
    sql_hidden=[hr([(1, "Empty")], []), random_hr(6, 60, [40000, 50000, 60000]), random_hr(10, 400)],
)

sql_problem(
    slug="sql-earns-more-than-manager", title="Earns More Than Their Manager (SQL)", difficulty=M, tags=["sql", "self-join"],
    statement="Return the `name` of every employee who earns **strictly more** than their manager. Any row order.",
    hints=["Join `employees` to itself: one copy for the employee, one for the manager."],
    sql_schema=HR_SCHEMA, compare="unordered",
    reference="SELECT e.name FROM employees e JOIN employees m ON m.id = e.manager_id WHERE e.salary > m.salary;",
    sql_samples=[(hr([(1, "R&D")], [(1, "Asha", 1, 70000, None), (2, "Ben", 1, 90000, 1), (3, "Chen", 1, 50000, 2)]),
                  "Ben (90000) out-earns his manager Asha (70000).")],
    sql_hidden=[hr([], [(1, "Boss", None, 10, None)]), random_hr(3, 100), random_hr(5, 600)],
)

sql_problem(
    slug="sql-monthly-revenue", title="Monthly Revenue (SQL)", difficulty=M, tags=["sql", "aggregation", "dates"],
    statement=(
        "Return `month` (formatted `YYYY-MM`) and `revenue` (sum of `amount` in that month, rounded to 2 decimals) for every month "
        "that has at least one order, sorted by `month` ascending."
    ),
    hints=["`strftime('%Y-%m', ordered_on)` extracts the month."],
    sql_schema=SHOP_SCHEMA, compare="exact",
    reference=(
        "SELECT strftime('%Y-%m', ordered_on) AS month, ROUND(SUM(amount), 2) AS revenue FROM orders "
        "GROUP BY month ORDER BY month;"
    ),
    sql_samples=[(shop([(1, "Asha", None, None)],
                       [(1, 1, 10.5, "2026-01-05"), (2, 1, 4.5, "2026-01-30"), (3, 1, 100.0, "2026-03-01")]), "February has no orders.")],
    sql_hidden=[shop([(1, "A", None, None)], []), random_shop(20, 100), random_shop(50, 2000)],
)

sql_problem(
    slug="sql-shared-emails", title="Shared Email Addresses (SQL)", difficulty=M, tags=["sql", "aggregation", "having"],
    statement="Return each `email` that is used by **more than one** customer. Ignore `NULL` emails. Any row order.",
    hints=["`GROUP BY email HAVING COUNT(*) > 1`."],
    sql_schema=SHOP_SCHEMA, compare="unordered",
    reference="SELECT email FROM customers WHERE email IS NOT NULL GROUP BY email HAVING COUNT(*) > 1;",
    sql_samples=[(shop([(1, "Asha", None, "a@x.test"), (2, "Ben", None, "a@x.test"), (3, "Chen", None, None), (4, "Dina", None, None)], []),
                  "Two customers have no email — NULLs are not a shared address.")],
    sql_hidden=[shop([(1, "A", None, "x@y.test")], []), random_shop(60, 0), random_shop(400, 0)],
)

# ---------------------------------------------------------------- HARD

sql_problem(
    slug="sql-top-three-salaries", title="Top Three Salaries per Department (SQL)", difficulty=H, tags=["sql", "window-functions"],
    statement=(
        "For each department, return the employees whose salary is among the **three highest distinct salaries** in that "
        "department, as `department`, `name`, `salary`. Sort by `department` ascending, then `salary` descending, then `name` ascending. "
        "Ignore employees without a department."
    ),
    hints=["`DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC)` gives tied salaries the same rank."],
    sql_schema=HR_SCHEMA, compare="exact",
    reference=(
        "SELECT department, name, salary FROM ("
        " SELECT d.name AS department, e.name, e.salary,"
        " DENSE_RANK() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS rnk"
        " FROM employees e JOIN departments d ON d.id = e.department_id"
        ") WHERE rnk <= 3 ORDER BY department, salary DESC, name;"
    ),
    sql_samples=[(hr([(1, "Engineering")], [(1, "Asha", 1, 90, None), (2, "Ben", 1, 80, 1), (3, "Chen", 1, 80, 1),
                                            (4, "Dina", 1, 70, 1), (5, "Eli", 1, 60, 1)]),
                  "Ben and Chen share the second-highest salary, so Eli (fourth distinct salary) is excluded.")],
    sql_hidden=[hr([(1, "A")], []), random_hr(4, 50, [10, 20, 30, 40, 50]), random_hr(9, 700)],
)

sql_problem(
    slug="sql-login-streaks", title="Three-Day Login Streaks (SQL)", difficulty=H, tags=["sql", "window-functions", "gaps-and-islands"],
    statement=(
        "Return the `user_id` of every user who logged in on **at least 3 consecutive calendar days**. "
        "A user may log in several times on the same day. Any row order."
    ),
    hints=["Deduplicate days first. For consecutive days, `julianday(login_date) - ROW_NUMBER()` is constant — group by it."],
    sql_schema=LOGIN_SCHEMA, compare="unordered",
    reference=(
        "WITH days AS (SELECT DISTINCT user_id, login_date FROM logins), "
        "grp AS (SELECT user_id, julianday(login_date) - ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS g FROM days) "
        "SELECT DISTINCT user_id FROM grp GROUP BY user_id, g HAVING COUNT(*) >= 3;"
    ),
    sql_samples=[(inserts("logins", ["user_id", "login_date"],
                          [(1, "2026-01-01"), (1, "2026-01-02"), (1, "2026-01-02"), (1, "2026-01-03"),
                           (2, "2026-01-01"), (2, "2026-01-02"), (2, "2026-01-04")]),
                  "User 1 logged in Jan 1–3; user 2's run is broken on Jan 3.")],
    sql_hidden=[inserts("logins", ["user_id", "login_date"], [(9, "2026-02-27"), (9, "2026-02-28"), (9, "2026-03-01")]),
                random_logins(20, 30), random_logins(150, 60)],
)
