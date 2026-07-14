import re

FAST_MANA = [
    "sol ring", "mana crypt", "mana vault", "grim monolith", "basalt monolith",
    "chrome mox", "mox diamond", "mox opal", "black lotus", "lotus petal",
    "jeweled lotus", "mana geode", "lion's eye diamond", "dark ritual",
    "cabal ritual", "culling the weak", "seething song", "pyretic ritual",
    "desperate ritual", "rite of flame", "channel", "ancient tomb", "city of traitors",
]

COMBO_STAPLES = [
    "thassa's oracle", "demonic consultation", "tainted pact", "isochron scepter",
    "dramatic reversal", "kiki-jiki, mirror breaker", "splinter twin", "walking ballista",
    "heliod, sun-crowned", "ad nauseam", "protean hulk", "food chain", "dockside extortionist",
    "aetherflux reservoir", "laboratory maniac", "jace, wielder of mysteries", "hullbreacher",
    "notion thief", "narset, parter of veils", "drannith magistrate", "opposition agent",
    "the gitrog monster", "doomsday", "bolas's citadel", "necropotence", "vampiric tutor",
    "demonic tutor", "imperial seal", "enlightened tutor", "mystical tutor", "worldly tutor",
    "razaketh, the foulblooded", "rings of brighthearth", "deadeye navigator", "cyclonic rift",
    "rhystic study", "mystic remora", "fierce guardianship", "deflecting swat",
]

FREE_INTERACTION_RE = re.compile(
    r"rather than pay (this spell's|its) mana cost|without paying its mana cost", re.I
)
STAX_RE = re.compile(
    r"players can't|opponent(s)? can't|can't attack|can't block|skip your draw step|costs? \{?\d\}? more to cast",
    re.I,
)
TUTOR_RE = re.compile(r"search your library for", re.I)


def parse_decklist(raw: str) -> list[str]:
    out = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        if re.match(r"^(deck|sideboard|commander|maindeck)\s*:?$", line, re.I):
            continue
        m = re.match(r"^(?:(\d+)\s*x?\s+)?(.+)$", line, re.I)
        if not m:
            continue
        name = re.sub(r"\s*\(.*?\)\s*$", "", m.group(2)).strip()
        if name:
            out.append(name)
    return out


def oracle_of(card: dict) -> str:
    if card.get("oracle_text"):
        return card["oracle_text"]
    if card.get("card_faces"):
        return " \n ".join(f.get("oracle_text", "") for f in card["card_faces"])
    return ""


def price_num(card: dict) -> float:
    prices = card.get("prices") or {}
    val = prices.get("eur") or prices.get("usd")
    try:
        return float(val) if val else 0.0
    except (TypeError, ValueError):
        return 0.0


def analyze_power(cards: list[dict]) -> dict:
    land_count = 0
    nonland_cmc_sum = 0.0
    nonland_count = 0
    fast_mana = tutors = free_interaction = stax = combo = 0
    curve = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, "6+": 0}

    for c in cards:
        name_lc = (c.get("name") or "").lower()
        type_line = (c.get("type_line") or "").lower()
        text = oracle_of(c)
        is_land = "land" in type_line

        if is_land:
            land_count += 1
        else:
            nonland_count += 1
            cmc = c.get("cmc") or 0
            nonland_cmc_sum += cmc
            bucket = "6+" if cmc >= 6 else int(cmc)
            curve[bucket] = curve.get(bucket, 0) + 1

        if any(f in name_lc for f in FAST_MANA):
            fast_mana += 1
        if any(name_lc == f or f in name_lc for f in COMBO_STAPLES):
            combo += 1
        if TUTOR_RE.search(text):
            tutors += 1
        if FREE_INTERACTION_RE.search(text):
            free_interaction += 1
        if STAX_RE.search(text):
            stax += 1

    avg_cmc = (nonland_cmc_sum / nonland_count) if nonland_count else 0.0
    score = (
        2
        + min(fast_mana, 8) * 0.4
        + min(tutors, 10) * 0.28
        + min(free_interaction, 6) * 0.4
        + min(combo, 12) * 0.32
        + min(stax, 6) * 0.22
        + max(0, 2.6 - avg_cmc) * 0.8
    )
    score = max(1.0, min(10.0, score))

    if score < 3.2:
        category = "Casual"
    elif score < 5.6:
        category = "Fringe"
    elif score < 8:
        category = "Optimized"
    else:
        category = "cEDH"

    return {
        "land_count": land_count,
        "nonland_count": nonland_count,
        "avg_cmc": round(avg_cmc, 2),
        "fast_mana": fast_mana,
        "tutors": tutors,
        "free_interaction": free_interaction,
        "stax": stax,
        "combo": combo,
        "curve": curve,
        "score": round(score, 1),
        "category": category,
        "total": len(cards),
    }
