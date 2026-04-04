"""
data_store.py — Shared in-memory state for AgentRelief.
All CLI routes read/write through this singleton DataStore so modules
can communicate without file I/O or sockets.
"""
from __future__ import annotations
from typing import Dict, List, Tuple, Any, Optional


class DataStore:
    _instance: Optional["DataStore"] = None

    def __new__(cls) -> "DataStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    # ── internal init (also called by reset) ─────────────────────────────
    def _init(self):
        self.requests:        List[Dict]  = []   # raw request dicts
        self.resources:       List[Dict]  = []   # raw resource dicts
        self.teams:           List[Dict]  = []   # raw team dicts
        self.graph_nodes:     List[str]   = []   # location names
        self.graph_edges:     List[Tuple] = []   # (u, v, km)
        self.ranked_requests: List[Any]   = []   # output of priority_agent
        self.assignments:     List[Dict]  = []   # team → request assignments
        self.allocations:     Dict[str, List] = {}  # req_id → allocated resources
        self.dispatch_plan:   Dict        = {}   # full replanner output
        self.all_pairs:       Any         = None  # NetworkAnalyzer instance cache
        self._req_ctr   = 0
        self._res_ctr   = 0
        self._team_ctr  = 0

    # ── ID generators ────────────────────────────────────────────────────
    def next_req_id(self) -> str:
        self._req_ctr += 1
        return f"REQ-{self._req_ctr:03d}"

    def next_res_id(self) -> str:
        self._res_ctr += 1
        return f"RES-{self._res_ctr:03d}"

    def next_team_id(self) -> str:
        self._team_ctr += 1
        return f"TEAM-{self._team_ctr:02d}"

    # ── look-ups ─────────────────────────────────────────────────────────
    def get_request(self, req_id: str) -> Optional[Dict]:
        return next((r for r in self.requests if r["id"] == req_id), None)

    def get_resource(self, res_id: str) -> Optional[Dict]:
        return next((r for r in self.resources if r["id"] == res_id), None)

    def get_team(self, team_id: str) -> Optional[Dict]:
        return next((t for t in self.teams if t["id"] == team_id), None)

    # ── reset (used by 'demo load') ───────────────────────────────────────
    def reset(self):
        type(self)._instance = None   # allow fresh singleton
        self._init()


# module-level singleton — import this everywhere
store = DataStore()
