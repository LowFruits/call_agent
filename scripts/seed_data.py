"""Seed test data: appointment types + doctor availability rules."""
from __future__ import annotations

import argparse
import asyncio

import httpx

DEFAULT_BASE_URL = "https://scheduling-simulation-api.onrender.com"
CLINIC_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"

APPOINTMENT_TYPES = [
    {"name": "ביקור ראשון", "duration_minutes": 30},
    {"name": "ביקור חוזר", "duration_minutes": 15},
    {"name": "ייעוץ", "duration_minutes": 20},
    {"name": "בדיקה", "duration_minutes": 45},
]


async def seed(base_url: str) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # 1. Create appointment types
        print("=== Creating appointment types ===")
        for at in APPOINTMENT_TYPES:
            resp = await client.post(
                "/appointment-types/",
                json={"clinic_id": CLINIC_ID, **at},
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                print(f"  Created: {data['name']} ({data['duration_minutes']} min) — {data['id']}")
            else:
                print(f"  Failed: {at['name']} — {resp.status_code}: {resp.text}")

        # 2. Fetch all doctors
        print("\n=== Fetching doctors ===")
        resp = await client.get("/doctors/", params={"clinic_id": CLINIC_ID})
        resp.raise_for_status()
        doctors = resp.json()
        print(f"  Found {len(doctors)} doctors")

        # 3. Seed availability for each doctor
        print("\n=== Seeding availability rules (Sun-Thu 09:00-17:00) ===")
        for doc in doctors:
            doc_id = doc["id"]
            name = f"{doc['first_name']} {doc['last_name']}"
            resp = await client.post(
                "/availability-rules/seed-defaults",
                params={"doctor_id": doc_id},
            )
            if resp.status_code in (200, 201):
                rules = resp.json()
                print(f"  {name}: {len(rules)} rules created")
            else:
                print(f"  {name}: Failed — {resp.status_code}: {resp.text}")

    print("\nDone!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed test data")
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL, help="API base URL"
    )
    args = parser.parse_args()
    asyncio.run(seed(args.base_url))
