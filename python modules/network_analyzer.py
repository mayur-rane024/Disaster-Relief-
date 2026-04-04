"""
network_analyzer.py
Algorithm: Floyd-Warshall All-Pairs Shortest Paths  (O(V³))
Purpose  : Pre-compute distances between EVERY pair of locations in the
           disaster area.  The replanner uses this matrix to:
             • instantly look up hub-to-site distances without re-running Dijkstra
             • find the nearest supply depot for any site
             • detect isolated / unreachable nodes (infrastructure damage)
             • display a human-readable distance matrix for operators
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple

INF = float("inf")


class NetworkAnalyzer:
    """Floyd-Warshall all-pairs shortest paths with path reconstruction."""

    def __init__(self, nodes: List[str], edges: List[Tuple[str, str, float]]):
        """
        nodes : list of location names
        edges : list of (u, v, distance_km) — treated as bidirectional
        """
        self.nodes: List[str] = list(nodes)
        self.n:     int       = len(self.nodes)
        self.idx:   Dict[str, int] = {name: i for i, name in enumerate(self.nodes)}

        # dist[i][j]  = shortest distance between nodes i and j
        # nxt[i][j]   = first hop from i toward j on shortest path
        self.dist: List[List[float]]         = [[INF] * self.n for _ in range(self.n)]
        self.nxt:  List[List[Optional[int]]] = [[None] * self.n for _ in range(self.n)]

        self._initialise(edges)
        self._floyd_warshall()

    # ── initialisation ────────────────────────────────────────────────────
    def _initialise(self, edges: List[Tuple[str, str, float]]):
        for i in range(self.n):
            self.dist[i][i] = 0.0

        for u, v, w in edges:
            if u not in self.idx or v not in self.idx:
                continue
            i, j = self.idx[u], self.idx[v]
            if w < self.dist[i][j]:           # keep shortest if duplicates
                self.dist[i][j] = self.dist[j][i] = w
                self.nxt[i][j] = j
                self.nxt[j][i] = i

    # ── Floyd-Warshall ────────────────────────────────────────────────────
    def _floyd_warshall(self):
        dist, nxt, n = self.dist, self.nxt, self.n
        for k in range(n):
            for i in range(n):
                if dist[i][k] == INF:
                    continue
                for j in range(n):
                    nd = dist[i][k] + dist[k][j]
                    if nd < dist[i][j]:
                        dist[i][j] = nd
                        nxt[i][j]  = nxt[i][k]

    # ── public API ────────────────────────────────────────────────────────
    def distance(self, u: str, v: str) -> float:
        """O(1) look-up after pre-computation."""
        if u not in self.idx or v not in self.idx:
            return INF
        return self.dist[self.idx[u]][self.idx[v]]

    def path(self, u: str, v: str) -> Tuple[float, List[str]]:
        """Returns (distance, ordered waypoint list) or (inf, [])."""
        if u not in self.idx or v not in self.idx:
            return INF, []
        i, j = self.idx[u], self.idx[v]
        if self.dist[i][j] == INF:
            return INF, []

        route: List[str] = [u]
        cur = i
        while cur != j:
            nxt_cur = self.nxt[cur][j]
            if nxt_cur is None:
                return INF, []
            cur = nxt_cur
            route.append(self.nodes[cur])
        return self.dist[i][j], route

    def nearest_hub(
        self, location: str, hubs: List[str]
    ) -> Tuple[Optional[str], float]:
        """Find which supply hub is closest to a disaster site."""
        if location not in self.idx:
            return None, INF
        i = self.idx[location]
        best_hub: Optional[str] = None
        best_d = INF
        for h in hubs:
            if h not in self.idx:
                continue
            d = self.dist[i][self.idx[h]]
            if d < best_d:
                best_d, best_hub = d, h
        return best_hub, best_d

    def connectivity_report(self) -> Dict:
        """Summary of network connectivity — useful to spot storm damage."""
        reachable = sum(
            1 for i in range(self.n) for j in range(self.n)
            if i != j and self.dist[i][j] < INF
        )
        isolated = [
            self.nodes[i] for i in range(self.n)
            if all(self.dist[i][j] == INF for j in range(self.n) if j != i)
        ]
        return {
            "nodes":            self.n,
            "reachable_pairs":  reachable,
            "max_reachable":    self.n * (self.n - 1),
            "isolated_nodes":   isolated,
        }

    def distance_matrix_str(self) -> str:
        """Pretty-print the distance matrix for operator inspection."""
        col_w = max(max(len(n) for n in self.nodes), 6) + 2
        header = " " * col_w + "".join(f"{n:>{col_w}}" for n in self.nodes)
        rows   = [header, " " * col_w + "─" * (col_w * self.n)]
        for i, u in enumerate(self.nodes):
            row = f"{u:>{col_w}}"
            for j in range(self.n):
                d = self.dist[i][j]
                cell = "∞" if d == INF else f"{d:.0f}"
                row += f"{cell:>{col_w}}"
            rows.append(row)
        return "\n".join(rows)


# ── Quick test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    nodes = ["HQ", "Junction X", "Village A", "Village C", "Hospital B",
             "Base South", "Depot West", "Village B"]
    edges = [
        ("HQ",        "Junction X", 8),
        ("Junction X","Village A",  14),
        ("Junction X","Village C",  9),
        ("Junction X","Hospital B", 7),
        ("HQ",        "Depot West", 12),
        ("Depot West","Village B",  25),
        ("Base South","Hospital B", 6),
        ("Base South","Village A",  16),
        ("HQ",        "Hospital B", 15),
    ]
    na = NetworkAnalyzer(nodes, edges)
    print(na.distance_matrix_str())
    print()
    d, p = na.path("HQ", "Village A")
    print(f"HQ → Village A: {d} km  via {' → '.join(p)}")
    hub, hd = na.nearest_hub("Village C", ["HQ", "Base South", "Depot West"])
    print(f"Nearest hub to Village C: {hub} ({hd} km)")
    print(na.connectivity_report())
