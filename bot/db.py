"""Робота з Supabase через його REST API (PostgREST)."""
from datetime import datetime, timezone

import httpx

STATUSES = ("new", "applied", "interview", "rejected")


class DB:
    def __init__(self, url: str, key: str):
        self.http = httpx.AsyncClient(
            base_url=f"{url.rstrip('/')}/rest/v1",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=15,
        )

    async def close(self) -> None:
        await self.http.aclose()

    async def add(self, row: dict) -> dict:
        r = await self.http.post(
            "/vacancies", json=row, headers={"Prefer": "return=representation"}
        )
        r.raise_for_status()
        return r.json()[0]

    async def get(self, user_id: int, vacancy_id: int | None = None) -> dict | None:
        """Вакансія за id або остання, якщо id не задано."""
        params = {"user_id": f"eq.{user_id}", "order": "created_at.desc", "limit": "1"}
        if vacancy_id is not None:
            params["id"] = f"eq.{vacancy_id}"
        r = await self.http.get("/vacancies", params=params)
        r.raise_for_status()
        rows = r.json()
        return rows[0] if rows else None

    async def recent(self, user_id: int, limit: int = 10) -> list[dict]:
        r = await self.http.get(
            "/vacancies",
            params={
                "user_id": f"eq.{user_id}",
                "select": "id,company,role,status",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )
        r.raise_for_status()
        return r.json()

    async def set_status(self, user_id: int, vacancy_id: int, status: str) -> dict | None:
        if status not in STATUSES:
            raise ValueError(f"Невідомий статус: {status}")
        r = await self.http.patch(
            "/vacancies",
            params={"id": f"eq.{vacancy_id}", "user_id": f"eq.{user_id}"},
            json={
                "status": status,
                "status_updated_at": datetime.now(timezone.utc).isoformat(),
            },
            headers={"Prefer": "return=representation"},
        )
        r.raise_for_status()
        rows = r.json()
        return rows[0] if rows else None

    async def status_counts(self, user_id: int) -> dict[str, int]:
        r = await self.http.get(
            "/vacancies", params={"user_id": f"eq.{user_id}", "select": "status"}
        )
        r.raise_for_status()
        counts = dict.fromkeys(STATUSES, 0)
        for row in r.json():
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        return counts
