"""
replanner.py — Mixed Replanner / Pipeline Coordinator
Orchestrates every algorithm module into one end-to-end dispatch pipeline:

  Stage 1 ── Greedy priority ranking          (priority_agent)
  Stage 2 ── Floyd-Warshall pre-computation   (network_analyzer)
  Stage 3 ── Dijkstra per-route refinement    (route_planner)
  Stage 4 ── Team assignment
               • Backtracking (default)       (team_assigner)
               • Branch & Bound (--bnb flag)  (optimizer)
  Stage 5 ── Resource allocation per dispatch (resource_allocator)
  Stage 6 ── Assemble & return DispatchPlan

The 'store' (DataStore singleton) is injected so the replanner is
decoupled from global state — it can be unit-tested independently.
"""
from __future__ import annotations
import os, sys

# ensure sibling modules in 'python modules/' are importable
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from typing import Any, Dict, List, Optional, Tuple

from priority_agent    import priority_agent   as PriorityAgent
from resource_allocator import resource_allocator as ResourceAllocator
from route_planner     import Graph, RoutePlanner
from network_analyzer  import NetworkAnalyzer
from team_assigner     import Team, TeamAssigner, Assignment, _score, _is_compatible
from optimizer         import BranchAndBound


# ── Result container ──────────────────────────────────────────────────────

class DispatchEntry:
    """One row of the dispatch plan (one request)."""
    __slots__ = (
        "request_id", "priority_rank", "priority_score",
        "team_id", "team_name",
        "route", "distance_km",
        "resources", "resource_value",
        "assignment_score",
    )

    def __init__(
        self,
        request_id:       str,
        priority_rank:    int,
        priority_score:   float,
        team_id:          Optional[str],
        team_name:        Optional[str],
        route:            List[str],
        distance_km:      float,
        resources:        List[Any],
        resource_value:   float,
        assignment_score: float,
    ):
        self.request_id       = request_id
        self.priority_rank    = priority_rank
        self.priority_score   = priority_score
        self.team_id          = team_id
        self.team_name        = team_name
        self.route            = route
        self.distance_km      = distance_km
        self.resources        = resources
        self.resource_value   = resource_value
        self.assignment_score = assignment_score


class DispatchPlan:
    def __init__(self):
        self.entries:             List[DispatchEntry] = []
        self.unassigned_requests: List[str]           = []
        self.total_assignment_score: float            = 0.0
        self.total_resource_value:   float            = 0.0
        self.pipeline_notes:      List[str]           = []

    def add(self, entry: DispatchEntry):
        self.entries.append(entry)
        self.total_assignment_score += entry.assignment_score
        self.total_resource_value   += entry.resource_value
        if entry.team_id is None:
            self.unassigned_requests.append(entry.request_id)

    def summary(self, use_color: bool = True) -> str:
        R = "\033[91m"; G = "\033[92m"; Y = "\033[93m"
        B = "\033[94m"; C = "\033[96m"; W = "\033[97m"
        DIM = "\033[2m"; RST = "\033[0m"; BOLD = "\033[1m"
        if not use_color:
            R=G=Y=B=C=W=DIM=RST=BOLD=""

        sep  = "=" * 64
        sep2 = "─" * 64
        lines = [
            sep,
            f"{BOLD}{C}  AGENTRELIEF — DISPATCH PLAN{RST}",
            sep,
            f"  {'#':<4}{'Request':<10}{'P-Score':<9}{'Team':<14}"
            f"{'Route':<28}{'Dist':>7}",
            f"  {DIM}{sep2}{RST}",
        ]

        for e in self.entries:
            team_str  = f"{e.team_id}" if e.team_id else f"{R}UNASSIGNED{RST}"
            route_str = " → ".join(e.route) if e.route else "—"
            dist_str  = f"{e.distance_km:.1f} km" if e.distance_km else "—"

            lines.append(
                f"  {e.priority_rank:<4}{e.request_id:<10}"
                f"{Y}{e.priority_score:<9.2f}{RST}"
                f"{team_str:<14}{DIM}{route_str:<28}{RST}{dist_str:>7}"
            )
            if e.resources:
                res_str = ", ".join(
                    f"{r.name}×{r.quantity:.0f}" for r in e.resources[:3]
                )
                if len(e.resources) > 3:
                    res_str += f" +{len(e.resources)-3} more"
                lines.append(f"  {' '*14}{B}Resources:{RST} {res_str}  "
                             f"[value {e.resource_value:.0f}]")

        lines += [
            f"  {DIM}{sep2}{RST}",
            f"  Dispatches          : {len(self.entries)}",
            f"  Unassigned requests : {len(self.unassigned_requests)}"
            + (f"  {R}{self.unassigned_requests}{RST}" if self.unassigned_requests else ""),
            f"  Total assign score  : {Y}{self.total_assignment_score:.2f}{RST}",
            f"  Total resource val  : {G}{self.total_resource_value:.2f}{RST}",
            sep,
        ]
        if self.pipeline_notes:
            lines.append(f"{DIM}  Pipeline: " + " | ".join(self.pipeline_notes) + RST)

        return "\n".join(lines)


# ── Main replanner class ──────────────────────────────────────────────────

class Replanner:
    """
    Mixed replanner — call run() to execute the full pipeline.

    Parameters
    ----------
    store    : DataStore singleton (injected to avoid global import here)
    """

    def __init__(self, store: Any):
        self.store = store

    def run(
        self,
        budget:       float = 1000.0,
        capacity:     float = 500.0,
        use_bnb:      bool  = False,
        use_dp_knap:  bool  = False,
    ) -> DispatchPlan:
        store = self.store
        plan  = DispatchPlan()

        # ── Validate ─────────────────────────────────────────────────────
        if not store.requests:
            plan.pipeline_notes.append("no requests")
            return plan

        # ── Stage 1: Greedy priority ranking ─────────────────────────────
        pa     = PriorityAgent()
        ranked = pa.rank_requests(store.requests)
        store.ranked_requests = ranked
        ranked_dicts: List[Dict] = [r.dict() for r in ranked]
        plan.pipeline_notes.append("Greedy")

        # ── Stage 2: Floyd-Warshall (pre-compute if graph exists) ─────────
        analyzer: Optional[NetworkAnalyzer] = None
        planner:  Optional[RoutePlanner]    = None

        if store.graph_nodes and store.graph_edges:
            analyzer = NetworkAnalyzer(store.graph_nodes, store.graph_edges)
            store.all_pairs = analyzer
            g = Graph()
            for u, v, w in store.graph_edges:
                g.add_edge(u, v, float(w))
            planner = RoutePlanner(g)
            plan.pipeline_notes.append("Floyd-Warshall")
            plan.pipeline_notes.append("Dijkstra")
        else:
            plan.pipeline_notes.append("no graph — routes skipped")

        # ── Stage 4: Team assignment ──────────────────────────────────────
        teams = [Team(**t) for t in store.teams if t.get("available", True)]
        assignment_map: Dict[str, str] = {}   # req_id → team_id
        assignment_score_map: Dict[str, float] = {}

        if teams:
            if use_bnb:
                # Build value matrix (n_req × n_team)
                vm: List[List[float]] = [
                    [
                        _score(team, req) if _is_compatible(team, req) else 0.0
                        for team in teams
                    ]
                    for req in ranked_dicts
                ]
                costs    = [t.deploy_cost for t in teams]
                req_ids  = [r["id"] for r in ranked_dicts]
                team_ids = [t.id for t in teams]
                bnb      = BranchAndBound(vm, costs, budget, team_ids, req_ids)
                _, assignment_map = bnb.optimize()

                # compute per-assignment scores
                team_by_id = {t.id: t for t in teams}
                for req in ranked_dicts:
                    tid = assignment_map.get(req["id"])
                    if tid and tid in team_by_id:
                        assignment_score_map[req["id"]] = _score(team_by_id[tid], req)

                plan.pipeline_notes.append("BranchBound")
            else:
                assigner    = TeamAssigner(teams, ranked_dicts)
                assignments = assigner.assign()
                assignment_map       = {a.request_id: a.team_id   for a in assignments}
                assignment_score_map = {a.request_id: a.score      for a in assignments}
                plan.pipeline_notes.append("Backtracking")
        else:
            plan.pipeline_notes.append("no teams")

        # ── Stages 3 + 5: Route + Resource per request ───────────────────
        team_by_id = {t.id: t for t in teams}

        for rank_idx, req in enumerate(ranked_dicts, start=1):
            req_id   = req["id"]
            team_id  = assignment_map.get(req_id)
            team_obj = team_by_id.get(team_id) if team_id else None

            # Stage 3: Dijkstra route (prefer live planner; fall back to F-W matrix)
            route: List[str] = []
            dist_km: float   = 0.0

            if team_obj:
                base = team_obj.base_location
                dest = req.get("location", "")

                if planner and base in planner.graph and dest in planner.graph:
                    d, p = planner.shortest_path(base, dest)
                    if d < float("inf"):
                        dist_km, route = d, p
                elif analyzer and base in analyzer.idx and dest in analyzer.idx:
                    d, p = analyzer.path(base, dest)
                    if d < float("inf"):
                        dist_km, route = d, p

            # Stage 5: Fractional (or 0/1) Knapsack resource allocation
            allocated: List[Any]  = []
            res_value: float      = 0.0

            if store.resources:
                ra        = ResourceAllocator(store.resources, capacity, use_dp=use_dp_knap)
                allocated = ra.allocated_resources
                res_value = ra.total_value()

            a_score = assignment_score_map.get(req_id, 0.0)

            plan.add(DispatchEntry(
                request_id       = req_id,
                priority_rank    = rank_idx,
                priority_score   = req.get("score", ranked[rank_idx - 1].score),
                team_id          = team_id,
                team_name        = team_obj.name if team_obj else None,
                route            = route,
                distance_km      = dist_km,
                resources        = allocated,
                resource_value   = res_value,
                assignment_score = a_score,
            ))

        # ── Stage 6: Persist results in store ────────────────────────────
        store.assignments   = [
            {"request_id": req_id, "team_id": tid}
            for req_id, tid in assignment_map.items()
        ]
        store.dispatch_plan = {"plan": plan}

        return plan
