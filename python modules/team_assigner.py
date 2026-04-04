"""
team_assigner.py
Algorithm: Backtracking with constraint pruning
Purpose  : Assign rescue teams to disaster requests such that:
           • Each team is assigned to at most one request
           • Specialization matches the type of need
           • Team capacity is sufficient for the request
           • Total assignment score is maximised (best-first search)

The backtracking explores all valid permutations but prunes branches that
violate hard constraints early, keeping runtime manageable for typical
disaster-response fleet sizes (< 20 teams, < 20 requests).
"""
from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field


# ── Domain models ─────────────────────────────────────────────────────────

class Team(BaseModel):
    id:             str
    name:           str
    specialization: str    # medical | rescue | logistics | general
    capacity:       int    # max simultaneous victims the team can handle
    available:      bool   = True
    base_location:  str    = "HQ"
    deploy_cost:    float  = 10.0  # budget units consumed when deployed


class Assignment(BaseModel):
    team_id:    str
    team_name:  str
    request_id: str
    score:      float = 0.0


# ── Compatibility table ────────────────────────────────────────────────────
# Maps need_type → acceptable team specializations (in preference order)
SPEC_COMPAT: Dict[str, List[str]] = {
    "Medical":  ["medical",   "general"],
    "Rescue":   ["rescue",    "general"],
    "Food":     ["logistics", "general"],
    "Shelter":  ["logistics", "rescue", "general"],
    "Water":    ["logistics", "general"],
    "Search":   ["rescue",    "general"],
}


# ── Scoring helpers (also imported by optimizer & replanner) ──────────────

def _normalised_need(req: Dict) -> str:
    return req.get("need_type", "General").capitalize()


def _is_compatible(team: Team, req: Dict) -> bool:
    """Hard constraint: specialization match AND capacity >= 10 % of affected."""
    need    = _normalised_need(req)
    allowed = SPEC_COMPAT.get(need, ["general"])
    if team.specialization.lower() not in allowed:
        return False
    min_cap = max(int(req.get("people_affected", 1) * 0.10), 1)
    return team.capacity >= min_cap


def _score(team: Team, req: Dict) -> float:
    """Soft objective: higher is better (specialization bonus × capacity ratio)."""
    need    = _normalised_need(req)
    allowed = SPEC_COMPAT.get(need, ["general"])
    # Perfect-spec bonus
    spec_bonus = 2.0 if team.specialization.lower() == allowed[0] else 1.0
    people     = max(req.get("people_affected", 1), 1)
    cap_ratio  = min(team.capacity / people, 1.0)
    # Urgency multiplier (shorter deadline = more important to get right)
    deadline   = max(req.get("deadline_hours", 24.0), 0.5)
    urgency    = min(24.0 / deadline, 4.0)
    return round(spec_bonus * cap_ratio * urgency * 10, 2)


# ── Backtracking assigner ─────────────────────────────────────────────────

class TeamAssigner:
    """
    Exhaustive backtracking over all request→team pairs.
    Maintains the globally best assignment found so far and prunes
    when the remaining upper bound cannot beat it.
    """

    def __init__(self, teams: List[Team], requests: List[Dict]):
        self.teams    = [t for t in teams if t.available]
        self.requests = requests
        self.best:        List[Assignment] = []
        self.best_score:  float            = -1.0

    # ── upper-bound estimate (greedy relaxation, no sharing) ──────────────
    def _upper_bound(self, req_idx: int, used: Set[str], current_score: float) -> float:
        score = current_score
        for i in range(req_idx, len(self.requests)):
            req  = self.requests[i]
            best = max(
                (_score(t, req) for t in self.teams
                 if t.id not in used and _is_compatible(t, req)),
                default=0.0,
            )
            score += best
        return score

    # ── recursive backtracker ─────────────────────────────────────────────
    def _bt(self, req_idx: int, current: List[Assignment],
            used: Set[str], cur_score: float):

        # base case — all requests processed
        if req_idx == len(self.requests):
            if cur_score > self.best_score:
                self.best_score = cur_score
                self.best       = list(current)
            return

        # prune: can't beat current best even with perfect remaining assignments
        if self._upper_bound(req_idx, used, cur_score) <= self.best_score:
            return

        req = self.requests[req_idx]

        # try assigning each available, compatible team
        for team in sorted(
            (t for t in self.teams if t.id not in used and _is_compatible(t, req)),
            key=lambda t: _score(t, req),
            reverse=True,          # try best candidates first → better pruning
        ):
            sc = _score(team, req)
            a  = Assignment(team_id=team.id, team_name=team.name,
                            request_id=req["id"], score=sc)
            current.append(a)
            used.add(team.id)

            self._bt(req_idx + 1, current, used, cur_score + sc)

            current.pop()
            used.discard(team.id)

        # also explore skipping this request (no team assigned)
        self._bt(req_idx + 1, current, used, cur_score)

    # ── public entry point ────────────────────────────────────────────────
    def assign(self) -> List[Assignment]:
        """Run backtracking; return best assignment list found."""
        self.best       = []
        self.best_score = -1.0
        self._bt(0, [], set(), 0.0)
        return self.best


# ── Quick test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    teams = [
        Team(id="T1", name="MedForce",   specialization="medical",   capacity=200, base_location="HQ"),
        Team(id="T2", name="RescueCrew", specialization="rescue",    capacity=150, base_location="Base South"),
        Team(id="T3", name="LogiTeam",   specialization="logistics", capacity=100, base_location="Depot"),
        Team(id="T4", name="GenForce",   specialization="general",   capacity=80,  base_location="HQ"),
    ]
    requests = [
        {"id": "REQ-001", "need_type": "Medical", "people_affected": 150, "deadline_hours": 6},
        {"id": "REQ-002", "need_type": "Food",    "people_affected": 80,  "deadline_hours": 12},
        {"id": "REQ-003", "need_type": "Rescue",  "people_affected": 210, "deadline_hours": 4},
    ]
    assigner     = TeamAssigner(teams, requests)
    assignments  = assigner.assign()
    print(f"Best score: {assigner.best_score:.2f}")
    for a in assignments:
        print(f"  {a.request_id} → {a.team_id} ({a.team_name})  score={a.score}")
