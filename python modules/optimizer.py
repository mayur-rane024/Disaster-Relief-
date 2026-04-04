"""
optimizer.py
Algorithm: Branch and Bound  (maximisation under budget constraint)
Purpose  : Optimally assign rescue teams to requests while respecting a
           hard budget limit.  Extends the backtracking assigner with:
             • explicit cost tracking per team deployment
             • LP-relaxation upper-bound for aggressive pruning
             • returns the globally optimal solution (exact, not heuristic)

Complexity: O(n! / pruned) — exponential worst-case, but the LP upper-bound
prunes the tree drastically for practical problem sizes (≤ 15 req / team).
"""
from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple


class BranchAndBound:
    """
    Solve:  max  Σ V[i][j] · x[i][j]
            s.t. Σ_j x[i][j] ≤ 1   ∀i   (each request gets ≤ 1 team)
                 Σ_i x[i][j] ≤ 1   ∀j   (each team assigned ≤ 1 request)
                 Σ_{i,j} cost[j]·x[i][j] ≤ budget
                 x[i][j] ∈ {0,1}

    Parameters
    ----------
    value_matrix   : V[i][j] — value of assigning team j to request i  (n_req × n_team)
    costs          : cost[j] — deployment cost of team j                (length n_team)
    budget         : total budget (scalar)
    team_ids       : optional list of team ID strings (for named output)
    request_ids    : optional list of request ID strings
    """

    def __init__(
        self,
        value_matrix:  List[List[float]],
        costs:         List[float],
        budget:        float,
        team_ids:      Optional[List[str]] = None,
        request_ids:   Optional[List[str]] = None,
    ):
        self.V          = value_matrix
        self.costs      = costs
        self.budget     = budget
        self.n_req      = len(value_matrix)
        self.n_team     = len(costs)
        self.team_ids   = team_ids   or [str(j) for j in range(self.n_team)]
        self.req_ids    = request_ids or [str(i) for i in range(self.n_req)]

        self.best_val:    float         = 0.0
        self.best_assign: Dict[int,int] = {}   # req_idx → team_idx

    # ── LP relaxation upper bound ─────────────────────────────────────────
    # For each remaining request, greedily pick the highest-value team that
    # still fits in the remaining budget (fractional — relaxing integrality).
    def _upper_bound(
        self, req_idx: int, used_teams: Set[int],
        rem_budget: float, cur_val: float
    ) -> float:
        val = cur_val
        for i in range(req_idx, self.n_req):
            # best feasible team for request i (greedy on value, ignoring sharing)
            best = max(
                (self.V[i][j]
                 for j in range(self.n_team)
                 if j not in used_teams and self.costs[j] <= rem_budget),
                default=0.0,
            )
            val += best
        return val

    # ── recursive B&B ─────────────────────────────────────────────────────
    def _bnb(
        self, req_idx: int, used_teams: Set[int],
        rem_budget: float, cur_val: float,
        cur_assign: Dict[int, int],
    ):
        # leaf node
        if req_idx == self.n_req:
            if cur_val > self.best_val:
                self.best_val   = cur_val
                self.best_assign = dict(cur_assign)
            return

        # pruning: upper bound ≤ current best → no point exploring
        if self._upper_bound(req_idx, used_teams, rem_budget, cur_val) <= self.best_val:
            return

        # branch: try assigning each affordable, unused team to request req_idx
        for j in sorted(
            range(self.n_team),
            key=lambda jj: self.V[req_idx][jj],
            reverse=True,         # try highest-value team first
        ):
            if j in used_teams:
                continue
            cost = self.costs[j]
            if cost > rem_budget:
                continue

            val = self.V[req_idx][j]
            used_teams.add(j)
            cur_assign[req_idx] = j

            self._bnb(
                req_idx + 1, used_teams,
                rem_budget - cost, cur_val + val,
                cur_assign,
            )

            used_teams.discard(j)
            del cur_assign[req_idx]

        # branch: skip this request (no team assigned, no cost incurred)
        self._bnb(req_idx + 1, used_teams, rem_budget, cur_val, cur_assign)

    # ── public entry point ────────────────────────────────────────────────
    def optimize(self) -> Tuple[float, Dict[str, str]]:
        """
        Returns (best_total_value, {req_id: team_id}) for the optimal
        feasible assignment.
        """
        self.best_val    = 0.0
        self.best_assign = {}
        self._bnb(0, set(), self.budget, 0.0, {})

        named: Dict[str, str] = {
            self.req_ids[i]: self.team_ids[j]
            for i, j in self.best_assign.items()
        }
        return self.best_val, named

    # ── diagnostics ───────────────────────────────────────────────────────
    def print_result(self, val: float, assign: Dict[str, str]):
        print(f"B&B Optimal value: {val:.2f}  (budget={self.budget})")
        if not assign:
            print("  No feasible assignment within budget.")
            return
        for req_id, team_id in assign.items():
            print(f"  {req_id} → {team_id}")


# ── Quick test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 3 requests × 4 teams
    value_matrix = [
        [10, 7, 5, 3],   # req 0
        [8,  9, 4, 2],   # req 1
        [5,  6, 8, 7],   # req 2
    ]
    costs  = [20, 25, 15, 10]
    budget = 50.0
    req_ids  = ["REQ-001", "REQ-002", "REQ-003"]
    team_ids = ["TEAM-01", "TEAM-02", "TEAM-03", "TEAM-04"]

    bnb = BranchAndBound(value_matrix, costs, budget, team_ids, req_ids)
    val, assign = bnb.optimize()
    bnb.print_result(val, assign)
