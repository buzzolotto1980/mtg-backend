import math
import random
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ProbaRequest(BaseModel):
    deck_size: int
    sources: int
    hand_size: int = 7
    turn: int = 3
    on_play: bool = True
    min_sources: int = 3
    target_pct: float = 90


class ProbaResponse(BaseModel):
    analytic_pct: float
    empirical_pct: float
    draws: int
    suggestion: str


def hyper_at_least(N: int, K: int, n: int, min_k: int) -> float:
    denom = math.comb(N, n)
    if denom == 0:
        return 0.0
    total = sum(math.comb(K, k) * math.comb(N - K, n - k) for k in range(min_k, min(n, K) + 1))
    return total / denom


@router.post("/probability", response_model=ProbaResponse)
def compute_probability(req: ProbaRequest):
    N, K = req.deck_size, req.sources
    draws = req.hand_size + (req.turn - 1 if req.on_play else req.turn)
    n = min(draws, N)
    target = req.target_pct / 100
    analytic = hyper_at_least(N, K, n, req.min_sources)

    # Simulazione Monte Carlo reale su 10.000 mani
    deck = [1] * K + [0] * (N - K)
    hits = 0
    trials = 10000
    for _ in range(trials):
        sample = random.sample(deck, n)
        if sum(sample) >= req.min_sources:
            hits += 1
    empirical = hits / trials

    if analytic < target:
        best_k = K
        for test_k in range(K, N + 1):
            if hyper_at_least(N, test_k, n, req.min_sources) >= target:
                best_k = test_k
                break
        if best_k > K:
            suggestion = (
                f"Per raggiungere ~{req.target_pct:.0f}% servono circa {best_k} fonti di mana "
                f"totali (attualmente {K}): aggiungi {best_k - K} terre o land-fetcher/rampa."
            )
        else:
            suggestion = "Anche aumentando le fonti oltre la dimensione del mazzo non si raggiunge il target."
    else:
        min_ok = K
        for test_k in range(K, -1, -1):
            if hyper_at_least(N, test_k, n, req.min_sources) < target:
                min_ok = test_k + 1
                break
            min_ok = test_k
        suggestion = (
            f"Obiettivo già raggiunto. Potresti scendere fino a circa {min_ok} fonti di mana "
            f"mantenendo il target, tagliando {K - min_ok} terre in eccesso a favore di spelli."
        )

    return ProbaResponse(
        analytic_pct=round(analytic * 100, 1),
        empirical_pct=round(empirical * 100, 1),
        draws=n,
        suggestion=suggestion,
    )
