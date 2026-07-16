"""
Client server-side per Scryfall: centralizza rate-limiting e caching,
cosi' ne' il frontend web ne' le future app mobile devono parlare
direttamente con Scryfall.
"""
import asyncio
import time
import httpx

SCRYFALL = "https://api.scryfall.com"
_last_call = 0.0
_cache: dict = {}
CACHE_TTL = 3600  # secondi


async def _throttle():
    global _last_call
    now = time.monotonic()
    wait = 0.1 - (now - _last_call)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_call = time.monotonic()


async def _get(path: str, params: dict | None = None):
    key = (path, tuple(sorted((params or {}).items())))
    cached = _cache.get(key)
    if cached and time.time() - cached[0] < CACHE_TTL:
        return cached[1]
    await _throttle()
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(SCRYFALL + path, params=params)
        res.raise_for_status()
        data = res.json()
    _cache[key] = (time.time(), data)
    return data


async def search(query: str, order: str = "edhrec"):
    try:
        data = await _get("/cards/search", {"q": query, "unique": "cards", "order": order})
        return data.get("data", [])
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return []
        raise


async def collection(names: list[str]):
    unique = list(dict.fromkeys(names))
    found, not_found = [], []
    if not unique:
        return found, not_found
    async with httpx.AsyncClient(timeout=15) as client:
        for i in range(0, len(unique), 75):
            chunk = unique[i : i + 75]
            await _throttle()
            res = await client.post(
                SCRYFALL + "/cards/collection",
                json={"identifiers": [{"name": n} for n in chunk]},
            )
            res.raise_for_status()
            data = res.json()
            found.extend(data.get("data", []))
            not_found.extend([x["name"] for x in data.get("not_found", [])])
    return found, not_found


async def sets():
    data = await _get("/sets")
    return data.get("data", [])


async def autocomplete(q: str):
    data = await _get("/cards/autocomplete", {"q": q})
    return data.get("data", [])


async def latest_set():
    all_sets = await sets()
    today = time.strftime("%Y-%m-%d")
    real = [
        s
        for s in all_sets
        if s.get("set_type") in ("expansion", "core", "commander", "draft_innovation", "masters")
        and s.get("released_at")
        and s["released_at"] <= today
    ]
    real.sort(key=lambda s: s["released_at"], reverse=True)
    return real[0] if real else None
