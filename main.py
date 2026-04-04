"""
main.py — AgentRelief CLI  v2.0
Disaster Relief Coordination System

Command Router
--------------
Commands are dispatched via a routing table (ROUTES dict) where each
key is "group.subcommand" and each value is a handler function.
This mirrors the HTTP-router pattern but runs entirely in-process —
modules communicate through the shared DataStore singleton.

Usage
-----
  python main.py                 — interactive REPL
  python main.py <cmd> [args]    — one-shot CLI

Command groups
--------------
  requests  add | list | rank | show <id> | remove <id>
  resources add | list | allocate [cap] | allocate-dp [cap]
  routes    add-edge [u v km] | plan [from to] | plan-all | network
  teams     add | list | assign | assign-optimal [budget]
  dispatch  run [--bnb] [budget] | replan | status
  demo      load | run | run-bnb
  help | cls | exit
"""
from __future__ import annotations
import sys, os

# ── path setup ───────────────────────────────────────────────────────────
_ROOT    = os.path.dirname(os.path.abspath(__file__))
_MODULES = os.path.join(_ROOT, "python modules")
for p in (_ROOT, _MODULES):
    if p not in sys.path:
        sys.path.insert(0, p)

# ── algorithm imports ─────────────────────────────────────────────────────
from data_store          import store
from priority_agent      import priority_agent   as PriorityAgent
from resource_allocator  import resource_allocator as ResourceAllocator
from route_planner       import Graph, RoutePlanner
from network_analyzer    import NetworkAnalyzer
from team_assigner       import Team, TeamAssigner, _score, _is_compatible
from optimizer           import BranchAndBound
from replanner           import Replanner

# ═══════════════════════════════════════════════════════════════════════════
# ANSI colour helpers
# ═══════════════════════════════════════════════════════════════════════════
R    = "\033[91m"; G    = "\033[92m"; Y    = "\033[93m"
B    = "\033[94m"; M    = "\033[95m"; C    = "\033[96m"
W    = "\033[97m"; DIM  = "\033[2m";  RST  = "\033[0m"
BOLD = "\033[1m"

try:                                         # enable ANSI on Windows
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(
        ctypes.windll.kernel32.GetStdHandle(-11), 7)
except Exception:
    pass

def hdr(txt: str):
    print(f"\n{BOLD}{C}{'─'*56}{RST}\n  {BOLD}{W}{txt}{RST}\n{DIM}{'─'*56}{RST}")

def ok(txt: str):   print(f"  {G}✔{RST} {txt}")
def warn(txt: str): print(f"  {Y}⚠{RST}  {txt}")
def err(txt: str):  print(f"  {R}✘{RST}  {txt}")
def info(txt: str): print(f"  {B}ℹ{RST}  {txt}")

def ask(label: str, default: str = "") -> str:
    val = input(f"  {M}?{RST} {label}"
                + (f" [{default}]" if default else "") + ": ").strip()
    return val or default

def ask_float(label: str, default: float) -> float:
    try: return float(ask(label, str(default)))
    except ValueError: return default

def ask_int(label: str, default: int) -> int:
    try: return int(ask(label, str(default)))
    except ValueError: return default

SEV_OPTS  = ["low", "medium", "high", "critical"]
NEED_OPTS = ["Medical", "Rescue", "Food", "Shelter", "Water", "Search"]
SPEC_OPTS = ["medical", "rescue", "logistics", "general"]

# ═══════════════════════════════════════════════════════════════════════════
# REQUESTS  —  Greedy priority ranking
# ═══════════════════════════════════════════════════════════════════════════

def cmd_requests_add(args):
    hdr("Add Disaster Request")
    req = {
        "id":               store.next_req_id(),
        "location":         ask("Location", "Unknown"),
        "severity":         ask(f"Severity  {SEV_OPTS}", "medium").capitalize(),
        "people_affected":  ask_int("People affected", 50),
        "deadline_hours":   ask_float("Deadline (hours)", 24.0),
        "distance_km":      ask_float("Distance from HQ (km)", 10.0),
        "need_type":        ask(f"Need type  {NEED_OPTS}", "Rescue").capitalize(),
        "status":           "pending",
    }
    store.requests.append(req)
    ok(f"Request {req['id']} added — {req['location']}  "
       f"{req['severity']} / {req['need_type']} / {req['people_affected']} people")


def cmd_requests_list(args):
    if not store.requests:
        warn("No requests. Run 'demo load' or 'requests add'.")
        return
    hdr("Disaster Requests  (Greedy Priority Ranking)")
    ranked = PriorityAgent().rank_requests(store.requests)
    store.ranked_requests = ranked

    print(f"  {BOLD}{'#':<4}{'ID':<10}{'Location':<18}"
          f"{'Severity':<12}{'Need':<12}{'People':<9}{'Score'}{RST}")
    print(f"  {DIM}{'─'*68}{RST}")
    SEV_COLOR = {"critical": R, "high": Y, "medium": B, "low": G}
    for i, r in enumerate(ranked, 1):
        sc = SEV_COLOR.get(r.severity.lower(), W)
        print(
            f"  {i:<4}{r.id:<10}{r.location:<18}"
            f"{sc}{r.severity:<12}{RST}{r.need_type:<12}"
            f"{r.people_affected:<9}{Y}{r.score:.2f}{RST}"
        )


def cmd_requests_rank(args):
    cmd_requests_list(args)


def cmd_requests_show(args):
    rid = (args[0] if args else ask("Request ID", "")).upper()
    req = store.get_request(rid)
    if not req:
        err(f"Request '{rid}' not found."); return
    hdr(f"Request  {req['id']}")
    for k, v in req.items():
        print(f"  {B}{k:<22}{RST}{v}")


def cmd_requests_remove(args):
    rid = (args[0] if args else ask("Request ID to remove", "")).upper()
    before = len(store.requests)
    store.requests = [r for r in store.requests if r["id"] != rid]
    if len(store.requests) < before:
        ok(f"Request {rid} removed.")
    else:
        err(f"Request {rid} not found.")


# ═══════════════════════════════════════════════════════════════════════════
# RESOURCES  —  Fractional Knapsack + 0/1 Knapsack DP
# ═══════════════════════════════════════════════════════════════════════════

def cmd_resources_add(args):
    hdr("Add Resource")
    res = {
        "id":       store.next_res_id(),
        "name":     ask("Resource name", "Supply"),
        "weight":   ask_float("Weight per unit (kg)", 5.0),
        "value":    ask_float("Priority value", 100.0),
        "quantity": ask_float("Quantity", 10.0),
    }
    store.resources.append(res)
    ok(f"Resource {res['id']} ({res['name']}) added.")


def cmd_resources_list(args):
    if not store.resources:
        warn("No resources. Run 'demo load' or 'resources add'."); return
    hdr("Available Resources")
    print(f"  {BOLD}{'ID':<10}{'Name':<22}{'Wt/u':>7}{'Value':>8}"
          f"{'Qty':>8}{'V/W':>8}{'Total Wt':>10}{RST}")
    print(f"  {DIM}{'─'*66}{RST}")
    for r in store.resources:
        vw = round(r["value"] / max(r["weight"], 1e-9), 2)
        tw = r["weight"] * r["quantity"]
        print(
            f"  {r['id']:<10}{r['name']:<22}"
            f"{r['weight']:>7.1f}{r['value']:>8.0f}"
            f"{r['quantity']:>8.0f}{vw:>8.2f}{tw:>10.1f} kg"
        )


def _run_allocate(args, use_dp: bool):
    if not store.resources:
        warn("No resources available."); return
    cap = float(args[0]) if args else ask_float("Carrier capacity (kg)", 200.0)
    mode = "0/1 Knapsack DP" if use_dp else "Fractional Knapsack"
    hdr(f"Resource Allocation  [{mode}]  cap={cap} kg")
    ra = ResourceAllocator(store.resources, cap, use_dp=use_dp)
    ra.print_allocated_resources()


def cmd_resources_allocate(args):    _run_allocate(args, use_dp=False)
def cmd_resources_allocate_dp(args): _run_allocate(args, use_dp=True)


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES  —  Dijkstra + Floyd-Warshall
# ═══════════════════════════════════════════════════════════════════════════

def _build_graph() -> Graph:
    g = Graph()
    for u, v, w in store.graph_edges:
        g.add_edge(str(u), str(v), float(w))
    return g


def cmd_routes_add_edge(args):
    if len(args) >= 3:
        u, v, w = args[0], args[1], float(args[2])
    else:
        hdr("Add Road / Edge")
        u = ask("From location", "HQ")
        v = ask("To location", "Village A")
        w = ask_float("Distance (km)", 10.0)

    store.graph_edges.append((u, v, w))
    for n in (u, v):
        if n not in store.graph_nodes:
            store.graph_nodes.append(n)
    ok(f"Road  {u}  ↔  {v}  ({w} km)  added.")


def cmd_routes_plan(args):
    if not store.graph_edges:
        warn("No road network. Use 'routes add-edge' or 'demo load'."); return
    if len(args) >= 2:
        src, dst = args[0], args[1]
    else:
        hdr("Plan Route  (Dijkstra)")
        src = ask("From", "HQ")
        dst = ask("To",   "Village A")
    g = _build_graph()
    planner = RoutePlanner(g)
    dist, path = planner.shortest_path(src, dst)
    hdr(f"Dijkstra: {src} → {dst}")
    if dist == float("inf"):
        err(f"No path found between '{src}' and '{dst}'.")
    else:
        ok(f"Distance : {dist:.1f} km")
        ok(f"Path     : {' → '.join(path)}")


def cmd_routes_plan_all(args):
    if not store.graph_edges:
        warn("No road network."); return
    hdr("Floyd-Warshall: All-Pairs Shortest Paths")
    na = NetworkAnalyzer(store.graph_nodes, store.graph_edges)
    store.all_pairs = na
    print()
    print(na.distance_matrix_str())
    print()
    rep = na.connectivity_report()
    info(f"Nodes: {rep['nodes']}  |  "
         f"Reachable pairs: {rep['reachable_pairs']} / {rep['max_reachable']}  |  "
         f"Isolated: {rep['isolated_nodes'] or 'none'}")
    ok("All-pairs matrix cached for replanner.")


def cmd_routes_network(args):
    if not store.graph_edges:
        warn("No road network."); return
    hdr("Road Network")
    print(f"  {BOLD}{'From':<22}{'To':<22}{'Distance'}{RST}")
    print(f"  {DIM}{'─'*52}{RST}")
    for u, v, w in store.graph_edges:
        print(f"  {u:<22}{v:<22}{w} km")
    print(f"\n  {len(store.graph_nodes)} nodes  |  {len(store.graph_edges)} edges")


# ═══════════════════════════════════════════════════════════════════════════
# TEAMS  —  Backtracking + Branch & Bound
# ═══════════════════════════════════════════════════════════════════════════

def cmd_teams_add(args):
    hdr("Add Rescue Team")
    t = {
        "id":             store.next_team_id(),
        "name":           ask("Team name", "Team Alpha"),
        "specialization": ask(f"Specialization  {SPEC_OPTS}", "general").lower(),
        "capacity":       ask_int("Capacity (people)", 50),
        "available":      True,
        "base_location":  ask("Base location", "HQ"),
        "deploy_cost":    ask_float("Deploy cost (units)", 10.0),
    }
    store.teams.append(t)
    ok(f"Team {t['id']} ({t['name']})  [{t['specialization']}]  "
       f"cap={t['capacity']}  base={t['base_location']}")


def cmd_teams_list(args):
    if not store.teams:
        warn("No teams. Run 'demo load' or 'teams add'."); return
    hdr("Rescue Teams")
    print(f"  {BOLD}{'ID':<10}{'Name':<20}{'Spec':<14}"
          f"{'Cap':>6}{'Cost':>7}  {'Base':<16}{'Avail'}{RST}")
    print(f"  {DIM}{'─'*74}{RST}")
    for t in store.teams:
        av = f"{G}Yes{RST}" if t.get("available", True) else f"{R}No{RST}"
        print(
            f"  {t['id']:<10}{t['name']:<20}{t['specialization']:<14}"
            f"{t['capacity']:>6}{t['deploy_cost']:>7.0f}  "
            f"{t['base_location']:<16}{av}"
        )


def _get_ranked_dicts():
    """Return ranked request dicts, running ranking if needed."""
    if store.ranked_requests:
        return [r.dict() if hasattr(r, "dict") else r for r in store.ranked_requests]
    ranked = PriorityAgent().rank_requests(store.requests)
    store.ranked_requests = ranked
    return [r.dict() for r in ranked]


def cmd_teams_assign(args):
    if not store.teams:
        warn("No teams. Run 'demo load' or 'teams add'."); return
    if not store.requests:
        warn("No requests."); return
    hdr("Backtracking Team Assignment")
    teams      = [Team(**t) for t in store.teams if t.get("available", True)]
    reqs_dicts = _get_ranked_dicts()
    assigner   = TeamAssigner(teams, reqs_dicts)
    assignments = assigner.assign()
    store.assignments = [a.dict() for a in assignments]

    if not assignments:
        warn("No valid assignment found (check team specs vs request needs).")
        return

    print(f"  {BOLD}{'Request':<12}{'Team':<12}{'Score':>7}{RST}")
    print(f"  {DIM}{'─'*34}{RST}")
    for a in assignments:
        print(f"  {a.request_id:<12}{a.team_id:<12}{Y}{a.score:>7.2f}{RST}")
    total = sum(a.score for a in assignments)
    ok(f"{len(assignments)} assignments  |  total score: {total:.2f}")


def cmd_teams_assign_optimal(args):
    if not store.teams or not store.requests:
        warn("Need both teams and requests."); return
    budget = float(args[0]) if args else ask_float("Budget (deployment units)", 1000.0)
    hdr(f"Branch & Bound Optimal Assignment  (budget={budget})")
    reqs_dicts = _get_ranked_dicts()
    teams      = [Team(**t) for t in store.teams if t.get("available", True)]

    vm   = [[_score(t, r) if _is_compatible(t, r) else 0.0 for t in teams]
            for r in reqs_dicts]
    costs    = [t.deploy_cost for t in teams]
    req_ids  = [r["id"] for r in reqs_dicts]
    team_ids = [t.id  for t in teams]

    bnb = BranchAndBound(vm, costs, budget, team_ids, req_ids)
    best_val, assignment = bnb.optimize()

    if not assignment:
        warn("No feasible assignment within budget."); return

    print(f"  {BOLD}{'Request':<12}{'Team':<12}{RST}")
    print(f"  {DIM}{'─'*26}{RST}")
    for req_id, team_id in assignment.items():
        print(f"  {req_id:<12}{team_id:<12}")
    ok(f"Optimal total value: {best_val:.2f}  (budget used ≤ {budget})")


# ═══════════════════════════════════════════════════════════════════════════
# DISPATCH  —  Mixed Replanner (full pipeline)
# ═══════════════════════════════════════════════════════════════════════════

def cmd_dispatch_run(args):
    if not store.requests:
        warn("No requests. Run 'demo load' first."); return
    use_bnb   = "--bnb"   in args
    use_dp    = "--dp"    in args
    budget    = next((float(a) for a in args
                      if a.replace(".", "", 1).lstrip("-").isdigit()), 1000.0)
    capacity  = 500.0

    hdr("Full Dispatch Pipeline")
    _pipeline_banner(use_bnb, use_dp, budget, capacity)

    replanner = Replanner(store)
    plan = replanner.run(
        budget=budget, capacity=capacity,
        use_bnb=use_bnb, use_dp_knap=use_dp,
    )
    print()
    print(plan.summary())


def _pipeline_banner(use_bnb, use_dp, budget, capacity):
    steps = [
        "Stage 1  Greedy priority ranking",
        "Stage 2  Floyd-Warshall all-pairs pre-computation",
        "Stage 3  Dijkstra per-route planning",
        f"Stage 4  {'Branch & Bound' if use_bnb else 'Backtracking'} team assignment"
        f"  (budget={budget})",
        f"Stage 5  {'0/1 Knapsack DP' if use_dp else 'Fractional Knapsack'} resource load"
        f"  (cap={capacity} kg)",
        "Stage 6  Assembling dispatch plan",
    ]
    for s in steps:
        info(s)


def cmd_dispatch_status(args):
    dp = store.dispatch_plan
    if not dp:
        warn("No dispatch plan. Run 'dispatch run' first."); return
    plan = dp.get("plan")
    if plan:
        print(plan.summary())
    else:
        warn("Dispatch plan is empty.")


def cmd_dispatch_replan(args):
    hdr("Replanning — applying current state")
    cmd_dispatch_run(args)


# ═══════════════════════════════════════════════════════════════════════════
# DEMO  —  pre-loaded scenario
# ═══════════════════════════════════════════════════════════════════════════

DEMO = {
    "requests": [
        {"id": "REQ-001", "location": "Village A",   "severity": "High",     "people_affected": 150, "deadline_hours": 6,  "distance_km": 20, "need_type": "Medical", "status": "pending"},
        {"id": "REQ-002", "location": "Village B",   "severity": "Medium",   "people_affected": 80,  "deadline_hours": 12, "distance_km": 35, "need_type": "Food",    "status": "pending"},
        {"id": "REQ-003", "location": "Village C",   "severity": "Critical", "people_affected": 340, "deadline_hours": 2,  "distance_km": 15, "need_type": "Medical", "status": "pending"},
        {"id": "REQ-004", "location": "Hospital B",  "severity": "High",     "people_affected": 210, "deadline_hours": 4,  "distance_km": 10, "need_type": "Rescue",  "status": "pending"},
        {"id": "REQ-005", "location": "Camp North",  "severity": "Low",      "people_affected": 45,  "deadline_hours": 24, "distance_km": 50, "need_type": "Shelter", "status": "pending"},
        {"id": "REQ-006", "location": "East Hamlet", "severity": "High",     "people_affected": 120, "deadline_hours": 8,  "distance_km": 30, "need_type": "Water",   "status": "pending"},
    ],
    "resources": [
        {"id": "RES-001", "name": "Medicine Kits",  "weight": 2.0,  "value": 150.0, "quantity": 30.0},
        {"id": "RES-002", "name": "Food Rations",   "weight": 5.0,  "value": 80.0,  "quantity": 50.0},
        {"id": "RES-003", "name": "Water Canisters","weight": 10.0, "value": 100.0, "quantity": 20.0},
        {"id": "RES-004", "name": "Stretchers",     "weight": 8.0,  "value": 120.0, "quantity": 10.0},
        {"id": "RES-005", "name": "Tents",          "weight": 15.0, "value": 90.0,  "quantity": 15.0},
        {"id": "RES-006", "name": "Radio Units",    "weight": 1.0,  "value": 200.0, "quantity": 5.0},
        {"id": "RES-007", "name": "Water Purifiers","weight": 3.0,  "value": 130.0, "quantity": 8.0},
    ],
    "teams": [
        {"id": "TEAM-01", "name": "MedForce Alpha",  "specialization": "medical",   "capacity": 200, "available": True, "base_location": "HQ",          "deploy_cost": 20.0},
        {"id": "TEAM-02", "name": "RescueBrigade",   "specialization": "rescue",    "capacity": 150, "available": True, "base_location": "Base South",   "deploy_cost": 25.0},
        {"id": "TEAM-03", "name": "LogiCore",        "specialization": "logistics", "capacity": 100, "available": True, "base_location": "Depot West",   "deploy_cost": 15.0},
        {"id": "TEAM-04", "name": "GenForce",        "specialization": "general",   "capacity": 80,  "available": True, "base_location": "HQ",           "deploy_cost": 10.0},
        {"id": "TEAM-05", "name": "MedForce Beta",   "specialization": "medical",   "capacity": 180, "available": True, "base_location": "Base South",   "deploy_cost": 20.0},
        {"id": "TEAM-06", "name": "AquaLogistics",   "specialization": "logistics", "capacity": 90,  "available": True, "base_location": "Depot West",   "deploy_cost": 12.0},
    ],
    "graph_nodes": [
        "HQ", "Junction X", "Village A", "Village B", "Village C",
        "Hospital B", "Camp North", "Base South", "Depot West", "East Hamlet",
    ],
    "graph_edges": [
        ("HQ",         "Junction X", 8),
        ("Junction X", "Village A",  14),
        ("Junction X", "Village C",  9),
        ("Junction X", "Hospital B", 7),
        ("HQ",         "Depot West", 12),
        ("Depot West", "Village B",  25),
        ("Village B",  "Camp North", 18),
        ("Base South", "Hospital B", 6),
        ("Base South", "Village A",  16),
        ("Base South", "Village C",  12),
        ("HQ",         "Hospital B", 15),
        ("HQ",         "Village A",  20),
        ("Junction X", "East Hamlet",11),
        ("Depot West", "East Hamlet",14),
    ],
}


def cmd_demo_load(args):
    # Hard-reset store via direct attribute writes (avoids singleton quirk)
    store.requests      = list(DEMO["requests"])
    store.resources     = list(DEMO["resources"])
    store.teams         = list(DEMO["teams"])
    store.graph_nodes   = list(DEMO["graph_nodes"])
    store.graph_edges   = [tuple(e) for e in DEMO["graph_edges"]]
    store.ranked_requests = []
    store.assignments   = []
    store.allocations   = {}
    store.dispatch_plan = {}
    store.all_pairs     = None
    store._req_ctr      = len(store.requests)
    store._res_ctr      = len(store.resources)
    store._team_ctr     = len(store.teams)

    hdr("Demo Scenario Loaded")
    ok(f"{len(store.requests)} requests  |  "
       f"{len(store.resources)} resources  |  "
       f"{len(store.teams)} teams  |  "
       f"{len(store.graph_nodes)} locations  |  "
       f"{len(store.graph_edges)} roads")


def cmd_demo_run(args):
    cmd_demo_load([])
    print()
    cmd_requests_list([])
    print()
    cmd_resources_list([])
    print()
    cmd_teams_list([])
    print()
    cmd_routes_plan_all([])
    print()
    cmd_dispatch_run([])


def cmd_demo_run_bnb(args):
    cmd_demo_load([])
    print()
    cmd_dispatch_run(["--bnb", "200"])


# ═══════════════════════════════════════════════════════════════════════════
# COMMAND ROUTER
# ═══════════════════════════════════════════════════════════════════════════

ROUTES: dict = {
    # requests
    "requests.add":            cmd_requests_add,
    "requests.list":           cmd_requests_list,
    "requests.rank":           cmd_requests_rank,
    "requests.show":           cmd_requests_show,
    "requests.remove":         cmd_requests_remove,
    # resources
    "resources.add":           cmd_resources_add,
    "resources.list":          cmd_resources_list,
    "resources.allocate":      cmd_resources_allocate,
    "resources.allocate-dp":   cmd_resources_allocate_dp,
    # routes
    "routes.add-edge":         cmd_routes_add_edge,
    "routes.plan":             cmd_routes_plan,
    "routes.plan-all":         cmd_routes_plan_all,
    "routes.network":          cmd_routes_network,
    # teams
    "teams.add":               cmd_teams_add,
    "teams.list":              cmd_teams_list,
    "teams.assign":            cmd_teams_assign,
    "teams.assign-optimal":    cmd_teams_assign_optimal,
    # dispatch (mixed replanner)
    "dispatch.run":            cmd_dispatch_run,
    "dispatch.status":         cmd_dispatch_status,
    "dispatch.replan":         cmd_dispatch_replan,
    # demo
    "demo.load":               cmd_demo_load,
    "demo.run":                cmd_demo_run,
    "demo.run-bnb":            cmd_demo_run_bnb,
}


def dispatch(raw: str):
    """Parse a raw command string and route it to the correct handler."""
    parts    = raw.strip().split()
    if not parts:
        return

    key_2    = ".".join(parts[:2]) if len(parts) >= 2 else None
    key_1    = parts[0]
    rest     = parts[2:]

    handler = ROUTES.get(key_2) or ROUTES.get(key_1)
    if handler:
        handler(rest if ROUTES.get(key_2) else parts[1:])
    else:
        err(f"Unknown command: '{raw}'")
        print(f"  Type {Y}help{RST} for the command reference.")


# ═══════════════════════════════════════════════════════════════════════════
# HELP
# ═══════════════════════════════════════════════════════════════════════════

def print_help():
    hdr("AgentRelief — Command Reference")
    sections = [
        (f"REQUESTS  {DIM}(algorithm: Greedy priority scoring){RST}", [
            ("requests add",             "Interactively add a disaster request"),
            ("requests list",            "Show all requests sorted by priority score"),
            ("requests show <id>",       "Show full detail for a request"),
            ("requests remove <id>",     "Remove a request from the queue"),
        ]),
        (f"RESOURCES  {DIM}(algorithms: Fractional Knapsack · 0/1 Knapsack DP){RST}", [
            ("resources add",            "Add a resource to the shared pool"),
            ("resources list",           "Show resource pool with value/weight ratios"),
            ("resources allocate [cap]", "Greedy fractional allocation for a carrier"),
            ("resources allocate-dp [cap]","0/1 DP allocation (integer items only)"),
        ]),
        (f"ROUTES  {DIM}(algorithms: Dijkstra · Floyd-Warshall){RST}", [
            ("routes add-edge [u v km]", "Add a bidirectional road"),
            ("routes plan [from] [to]",  "Shortest path via Dijkstra"),
            ("routes plan-all",          "All-pairs matrix via Floyd-Warshall"),
            ("routes network",           "Print current road network"),
        ]),
        (f"TEAMS  {DIM}(algorithms: Backtracking · Branch & Bound){RST}", [
            ("teams add",                "Add a rescue team"),
            ("teams list",               "List all teams"),
            ("teams assign",             "Assign teams — Backtracking (exact)"),
            ("teams assign-optimal [b]", "Assign teams — Branch & Bound with budget b"),
        ]),
        (f"DISPATCH  {DIM}(Mixed Replanner — runs all 6 stages){RST}", [
            ("dispatch run [--bnb] [--dp] [budget]",
                                         "Full pipeline: rank → routes → assign → allocate"),
            ("dispatch replan",          "Replan with current state (dynamic updates)"),
            ("dispatch status",          "Print current dispatch plan"),
        ]),
        ("DEMO", [
            ("demo load",                "Load a pre-built disaster scenario"),
            ("demo run",                 "Load + run full pipeline (Backtracking mode)"),
            ("demo run-bnb",             "Load + run full pipeline (B&B mode, budget=200)"),
        ]),
    ]
    for section, cmds in sections:
        print(f"\n  {BOLD}{Y}{section}{RST}")
        for cmd, desc in cmds:
            print(f"    {C}{cmd:<40}{RST}{DIM}{desc}{RST}")
    print()
    info("Flags:  --bnb  use Branch & Bound for team assignment")
    info("        --dp   use 0/1 Knapsack DP for resource allocation")


# ═══════════════════════════════════════════════════════════════════════════
# BANNER + ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

BANNER = f"""
{BOLD}{R}
   _   ___ ___ _  _ _____ ___  ___ _    ___ ___ ___ 
  /_\\ / __| __| \\| |_   _| _ \\| __| |  |_ _| __| __|
 / _ \\| (_ | _|| .` | | | |   /| _|| |__ | || _|| _| 
/_/ \\_\\\___|___|_|\\_| |_| |_|_\\|___|____|___|___|_|  
{RST}{BOLD}{W}  Disaster Relief Coordination System  v2.0{RST}
{DIM}  Algorithms : Greedy · Fractional Knapsack · 0/1 DP Knapsack
               Dijkstra · Floyd-Warshall · Backtracking · Branch & Bound
  Commands   : type  help  |  quick start: type  demo run{RST}
"""


def main():
    print(BANNER)
    cli_args = sys.argv[1:]
    if cli_args:
        dispatch(" ".join(cli_args))
        return

    while True:
        try:
            raw = input(f"{BOLD}{B}relief>{RST} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Goodbye.{RST}")
            break

        if not raw:
            continue
        if raw.lower() in ("exit", "quit", "q"):
            print(f"{DIM}Goodbye.{RST}")
            break
        if raw.lower() in ("help", "?", "h"):
            print_help()
            continue
        if raw.lower() in ("cls", "clear"):
            os.system("cls" if os.name == "nt" else "clear")
            continue
        dispatch(raw)


if __name__ == "__main__":
    main()
