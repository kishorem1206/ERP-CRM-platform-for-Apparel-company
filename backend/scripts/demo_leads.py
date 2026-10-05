"""Dummy leads for the lead-intelligence features (scoring, duplicates, assignment,
first contact, won/lost).

Records are created through the real API, so the scoring, duplicate detection,
round-robin assignment and first-contact logic run exactly as they do for real
enquiries. Every person, organization, lead and activity is named with [DEMO].

Run inside the backend container:
    python -m scripts.demo_leads            # add
    python -m scripts.demo_leads --remove   # remove the [DEMO] leads, activities, persons and organizations
"""
import asyncio
import json
import random
import sys
import urllib.error
import urllib.request

from sqlalchemy import text

from app.core.security import create_access_token
from app.api.v1.endpoints.auth import _get_user_permissions
from app.db.session import AsyncSessionLocal
from app.models.user import User

COMPANY_ID = "cfa4e79d-ddd7-4c04-8432-d690a97d1b84"
BASE = "http://localhost:8000/api/v1"
MARK = "[DEMO]"
RNG = random.Random(20261006)

SERVICE_AREAS = [("Tiruppur", "preferred"), ("Coimbatore", "preferred"), ("Chennai", "secondary"), ("Madurai", "non_serviceable")]
CITIES = ["Tiruppur", "Coimbatore", "Chennai", "Madurai", "Bangalore", None]
ORG_NAMES = ["Sunrise Knitwear", "Velvet Threads", "Coastline Apparel", "Maple Garments", "Northwind Fashion", "Kaveri Textiles", "Blue Harbor Wear", "Silverline Exports"]
FIRST = ["Asha", "Ravi", "Meena", "Vikram", "Priya", "Arjun", "Kavya", "Suresh", "Divya", "Karthik", "Lakshmi", "Manoj"]
DESCRIPTIONS = [
    "Need 5000 pcs kids wear OEM with embroidery, please send quotation and price for the next season order",
    "Looking for cotton polo t-shirts, 2000 pieces, send catalogue and price list",
    "Sample request for summer fabric swatches before we confirm the bulk order",
    "price?",
    "",
    "Wholesale enquiry for woven shirts, approx 800 pcs per month, quotation needed",
    "Interested in private label activewear, quantity around 1500 units, want samples first",
    "Checking availability of organic cotton fabric for a boutique line, no quantity yet",
    "Repeat order discussion for last season's denim jackets, 3000 pcs, please share updated quote",
    "hi",
]


def _call(method: str, path: str, token: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()).get("data")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()[:300]}")


async def _token() -> str:
    async with AsyncSessionLocal() as db:
        u = (await db.execute(text("SELECT id FROM users WHERE email='admin@company.com'"))).scalar()
        user = await db.get(User, u)
        perms = await _get_user_permissions(db, user.id)
        return create_access_token({"sub": str(user.id), "company_id": str(user.company_id), "type": "access", "permissions": perms})


async def remove():
    async with AsyncSessionLocal() as db:
        for sql in [
            "DELETE FROM crm_activities WHERE title LIKE '[DEMO]%'",
            "DELETE FROM crm_leads WHERE title LIKE '[DEMO]%' AND company_id = :c",
            "DELETE FROM crm_persons WHERE name LIKE '[DEMO]%' AND company_id = :c",
            "DELETE FROM crm_organizations WHERE name LIKE '[DEMO]%' AND company_id = :c",
        ]:
            res = await db.execute(text(sql), {"c": COMPANY_ID})
            print(sql.split(" WHERE")[0], res.rowcount)
        await db.commit()


def add(token: str):
    pipelines = _call("GET", "/crm/pipelines", token)
    pipeline = next(p for p in pipelines if p["stages"])
    stages = sorted(pipeline["stages"], key=lambda s: s["sort_order"])
    new_stage = stages[0]["id"]
    qualified = next((s["id"] for s in stages if s["name"].lower() == "qualified"), stages[1]["id"])
    sources = [s["id"] for s in _call("GET", "/crm/lead-sources", token)]
    users = [u["id"] for u in _call("GET", "/crm/assignable-users", token)]

    existing_areas = {a["location_name"].lower() for a in (_call("GET", "/crm/service-areas", token) or [])}
    for name, tier in SERVICE_AREAS:
        if name.lower() not in existing_areas:
            _call("POST", "/crm/service-areas", token, {"location_name": name, "tier": tier})

    pool = _call("GET", "/crm/assignment-pool", token) or []
    if not pool:
        for uid in users[:2]:
            _call("POST", "/crm/assignment-pool", token, {"user_id": uid})

    orgs = [_call("POST", "/crm/organizations", token, {"name": f"{MARK} {n}"}) for n in ORG_NAMES]

    persons = []
    for i in range(12):
        city = RNG.choice(["Tiruppur", "Coimbatore", "Chennai", "Madurai", "Bangalore"])
        business = i % 3 != 2
        domain = f"{ORG_NAMES[i % len(ORG_NAMES)].lower().replace(' ', '')}.example" if business else "gmail.com"
        emails = [{"value": f"demo.{i}@{domain}", "label": "work"}] if i % 5 != 4 else []
        phones = [{"value": f"98{RNG.randint(10000000, 99999999)}", "label": "mobile"}] if i % 4 != 3 else []
        persons.append(_call("POST", "/crm/persons", token, {
            "name": f"{MARK} {FIRST[i % len(FIRST)]} {i + 1}",
            "job_title": "Buyer" if business else None,
            "city": city,
            "emails": emails,
            "contact_numbers": phones,
            "organization_id": orgs[i % len(orgs)]["id"] if business else None,
        }))

    leads = []
    for n in range(30):
        person = persons[n % len(persons)]
        description = DESCRIPTIONS[n % len(DESCRIPTIONS)]
        body = {
            "title": f"{MARK} Enquiry {n + 1:02d}",
            "description": description,
            "lead_value": str(RNG.choice([60000, 150000, 420000, 880000, 1500000, 2750000])),
            "temperature": RNG.choice(["hot", "warm", "cold"]),
            "pipeline_id": pipeline["id"],
            "stage_id": new_stage,
            "source_id": RNG.choice(sources) if sources else None,
            "person_id": person["id"],
            "organization_id": person.get("organization_id"),
            "assigned_to": None,
        }
        leads.append(_call("POST", "/crm/leads", token, body))

    # Repeat contacts: two more enquiries from people who already enquired.
    for person in persons[:2]:
        leads.append(_call("POST", "/crm/leads", token, {
            "title": f"{MARK} Repeat enquiry",
            "description": "Following up on earlier enquiry, same requirement with updated quantity of 1200 pcs",
            "lead_value": "300000", "temperature": "warm", "pipeline_id": pipeline["id"], "stage_id": new_stage,
            "source_id": RNG.choice(sources) if sources else None, "person_id": person["id"],
            "organization_id": person.get("organization_id"),
        }))

    # Progress some leads through the real stage and status endpoints.
    for lead in leads[:8]:
        _call("PATCH", f"/crm/leads/{lead['id']}/stage", token, {"stage_id": qualified, "pipeline_id": pipeline["id"]})
    for lead in leads[:3]:
        _call("PATCH", f"/crm/leads/{lead['id']}/status", token, {"status": "won"})
    for lead in leads[3:5]:
        _call("PATCH", f"/crm/leads/{lead['id']}/status", token, {"status": "lost", "lost_reason": "Price too high"})

    # First contact: an activity on each of ten leads, marked done.
    for lead in leads[5:15]:
        act = _call("POST", "/crm/activities", token, {
            "title": f"{MARK} Call back", "type": "call", "lead_id": lead["id"], "is_done": False,
        })
        _call("PATCH", f"/crm/activities/{act['id']}/done", token, {"is_done": True, "outcome": "Discussed requirement"})

    print(f"service areas: {len(SERVICE_AREAS)} · organizations: {len(orgs)} · persons: {len(persons)} · leads: {len(leads)}")


async def main():
    if "--remove" in sys.argv:
        await remove()
        return
    token = await _token()
    add(token)


if __name__ == "__main__":
    asyncio.run(main())
