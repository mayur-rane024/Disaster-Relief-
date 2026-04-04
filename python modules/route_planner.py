"""
route_planner.py
Algorithm: Dijkstra's Shortest Path  (O((V + E) log V))
Purpose  : Find the optimal road route for a rescue team from its base
           to a disaster site.  Returns both distance and the ordered
           waypoint list so the replanner can display the full path.
"""
from __future__ import annotations
import heapq
from typing import Dict, List, Optional, Set, Tuple


class Graph:
    """Weighted undirected / directed adjacency-list graph."""

    def __init__(self):
        self.nodes: Set[str] = set()
        self.adj:   Dict[str, List[Tuple[str, float]]] = {}

    def add_node(self, name: str):
        self.nodes.add(name)
        self.adj.setdefault(name, [])

    def add_edge(self, u: str, v: str, w: float, bidirectional: bool = True):
        for n in (u, v):
            self.add_node(n)
        self.adj[u].append((v, w))
        if bidirectional:
            self.adj[v].append((u, w))

    def neighbours(self, node: str) -> List[Tuple[str, float]]:
        return self.adj.get(node, [])

    def __contains__(self, node: str) -> bool:
        return node in self.nodes


class RoutePlanner:
    """Dijkstra-based route planner operating on a Graph."""

    def __init__(self, graph: Graph):
        self.graph = graph

    # ── core Dijkstra ────────────────────────────────────────────────────
    def dijkstra(
        self, source: str
    ) -> Tuple[Dict[str, float], Dict[str, Optional[str]]]:
        """
        Single-source shortest paths from `source`.
        Returns (dist_map, prev_map).
        dist_map[v]  = shortest distance from source to v (∞ if unreachable)
        prev_map[v]  = predecessor of v on the shortest path
        """
        if source not in self.graph:
            return {}, {}

        dist: Dict[str, float] = {n: float("inf") for n in self.graph.nodes}
        prev: Dict[str, Optional[str]] = {n: None for n in self.graph.nodes}
        dist[source] = 0.0

        # min-heap: (distance, node)
        pq: List[Tuple[float, str]] = [(0.0, source)]
        visited: Set[str] = set()

        while pq:
            d, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)

            for v, w in self.graph.neighbours(u):
                nd = d + w
                if nd < dist.get(v, float("inf")):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))

        return dist, prev

    # ── path reconstruction ───────────────────────────────────────────────
    def shortest_path(
        self, src: str, dst: str
    ) -> Tuple[float, List[str]]:
        """
        Returns (distance_km, [src, ..., dst]).
        Returns (inf, []) if no path exists.
        """
        if src not in self.graph or dst not in self.graph:
            return float("inf"), []

        dist, prev = self.dijkstra(src)

        if dist.get(dst, float("inf")) == float("inf"):
            return float("inf"), []

        path: List[str] = []
        node: Optional[str] = dst
        while node is not None:
            path.append(node)
            node = prev[node]
        path.reverse()

        return dist[dst], path

    # ── convenience: nearest candidate ───────────────────────────────────
    def nearest_reachable(
        self, src: str, candidates: List[str]
    ) -> Tuple[Optional[str], float]:
        """Find the closest reachable node among `candidates` from `src`."""
        dist, _ = self.dijkstra(src)
        best_node: Optional[str] = None
        best_dist = float("inf")
        for c in candidates:
            d = dist.get(c, float("inf"))
            if d < best_dist:
                best_dist, best_node = d, c
        return best_node, best_dist

    def all_shortest_from(self, src: str) -> Dict[str, Tuple[float, List[str]]]:
        """Return {node: (distance, path)} for every reachable node."""
        dist, prev = self.dijkstra(src)
        result = {}
        for dst in self.graph.nodes:
            if dst == src or dist.get(dst, float("inf")) == float("inf"):
                continue
            path: List[str] = []
            node: Optional[str] = dst
            while node is not None:
                path.append(node)
                node = prev[node]
            result[dst] = (dist[dst], list(reversed(path)))
        return result


# ── Quick test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    g = Graph()
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
    for u, v, w in edges:
        g.add_edge(u, v, w)

    planner = RoutePlanner(g)
    for dst in ["Village A", "Hospital B", "Village C", "Village B"]:
        d, path = planner.shortest_path("HQ", dst)
        print(f"HQ → {dst:<15} {d:.1f} km   {'→'.join(path)}")
