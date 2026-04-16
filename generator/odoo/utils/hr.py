import random
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.data import DEPARTMENTS, EMPLOYEES

# DEPARTMENTS = ["Sales", "Finance", "Procurement", "Operations", "Supply Chain"]
# EMPLOYEES = [
#     {"name": "Alice Chen", "job_title": "Sales Manager", "department": "Sales"},
#     ...
# ]


def execute(uid, models, cfg, model, method, args, kwargs=None):
    return models.execute_kw(cfg["db"], uid, cfg["password"], model, method, args, kwargs or {})


def generate_hr(uid, models, cfg):
    print("Creating departments...")
    dept_map = {}
    for dept_name in DEPARTMENTS:
        existing = execute(uid, models, cfg, "hr.department", "search",
            [[["name", "=", dept_name]]],
        )
        if existing:
            dept_map[dept_name] = existing[0]
            print(f"  Department '{dept_name}' already exists, skipping.")
        else:
            dept_id = execute(uid, models, cfg, "hr.department", "create",
                [{"name": dept_name}],
            )
            dept_map[dept_name] = dept_id
            print(f"  Department '{dept_name}': created")

    print("Creating employees...")
    employee_ids = []
    for emp in EMPLOYEES:
        existing = execute(uid, models, cfg, "hr.employee", "search",
            [[["name", "=", emp["name"]]]],
        )
        if existing:
            employee_ids.append(existing[0])
            print(f"  Employee '{emp['name']}' already exists, skipping.")
            continue
        emp_id = execute(uid, models, cfg, "hr.employee", "create", [{
            "name": emp["name"],
            "job_title": emp["job_title"],
            "department_id": dept_map[emp["department"]],
        }])
        employee_ids.append(emp_id)
        print(f"  Employee '{emp['name']}': created")

    print("Creating leave allocations...")
    leave_types = execute(uid, models, cfg, "hr.leave.type", "search_read",
        [[["active", "=", True]]],
        {"fields": ["id", "name"], "limit": 5},
    )
    if not leave_types:
        print("  No leave types found, skipping allocations.")
        return employee_ids

    annual = next((lt for lt in leave_types if "annual" in lt["name"].lower()), None)
    sick = next((lt for lt in leave_types if "sick" in lt["name"].lower()), None)

    for emp_id in employee_ids:
        if annual:
            existing = execute(uid, models, cfg, "hr.leave.allocation", "search",
                [[["employee_id", "=", emp_id], ["holiday_status_id", "=", annual["id"]]]],
            )
            if not existing:
                alloc_id = execute(uid, models, cfg, "hr.leave.allocation", "create", [{
                    "employee_id": emp_id,
                    "holiday_status_id": annual["id"],
                    "number_of_days": random.randint(14, 21),
                    "state": "draft",
                }])
                execute(uid, models, cfg, "hr.leave.allocation", "action_approve", [[alloc_id]])
                print(f"  Annual leave allocation for employee {emp_id}: approved")

        if sick:
            existing = execute(uid, models, cfg, "hr.leave.allocation", "search",
                [[["employee_id", "=", emp_id], ["holiday_status_id", "=", sick["id"]]]],
            )
            if not existing:
                alloc_id = execute(uid, models, cfg, "hr.leave.allocation", "create", [{
                    "employee_id": emp_id,
                    "holiday_status_id": sick["id"],
                    "number_of_days": random.randint(7, 10),
                    "state": "draft",
                }])
                execute(uid, models, cfg, "hr.leave.allocation", "action_approve", [[alloc_id]])
                print(f"  Sick leave allocation for employee {emp_id}: approved")

    print("Creating leave requests...")
    today = date.today()
    for emp_id in employee_ids[:4]:
        if not annual:
            break
        existing = execute(uid, models, cfg, "hr.leave", "search",
            [[["employee_id", "=", emp_id], ["holiday_status_id", "=", annual["id"]]]],
        )
        if existing:
            print(f"  Leave request for employee {emp_id} already exists, skipping.")
            continue
        offset = random.randint(7, 60)
        start = today + timedelta(days=offset)
        end = start + timedelta(days=random.randint(1, 4))
        leave_id = execute(uid, models, cfg, "hr.leave", "create", [{
            "employee_id": emp_id,
            "holiday_status_id": annual["id"],
            "date_from": f"{start} 08:00:00",
            "date_to": f"{end} 17:00:00",
        }])
        execute(uid, models, cfg, "hr.leave", "action_approve", [[leave_id]])
        print(f"  Leave request for employee {emp_id} ({start} to {end}): approved")

    print("HR generation complete.")
    return employee_ids
