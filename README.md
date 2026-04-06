# AgentRelief CLI (Disaster Relief Coordination System)

AgentRelief is a Python command-line application that helps coordinate disaster relief operations by:

* prioritizing incoming requests,
* allocating limited resources,
* planning routes over a road network,
* assigning rescue teams (greedy/backtracking vs optimal B&B), and
* generating a single, end-to-end dispatch plan that can be replanned as conditions change.

This project is intended for learning/demonstration of classic algorithms in an applied scenario.

## Quick start (Windows)

1) Create and activate a virtual environment.

2) Install dependencies.

3) Run the demo scenario.

```powershell
pip install uv
uv sync
source .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# one-shot demo
python main.py demo run
```

If your PowerShell execution policy blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

## Run modes

### Interactive REPL

```bash
python main.py
```

Inside the REPL:

* `help` shows all commands
* `cls` clears the screen
* `exit` quits

### One-shot command

```bash
python main.py <group> <subcommand> [args]
```

Examples:

```bash
python main.py demo load
python main.py requests list
python main.py routes plan HQ "Village A"
python main.py dispatch run --bnb --dp 200
```

## Command reference

Commands are routed via the `ROUTES` table in `main.py` (keys look like `group.subcommand`).

### Requests (Greedy priority scoring)

* `requests add` — interactively add a disaster request
* `requests list` — show all requests sorted by priority score
* `requests rank` — alias for `requests list`
* `requests show <id>` — show full details for a request
* `requests remove <id>` — remove a request

### Resources (Fractional knapsack / 0/1 knapsack DP)

* `resources add` — add a resource to the pool
* `resources list` — list resources with value/weight ratios
* `resources allocate [cap]` — fractional knapsack allocation (greedy)
* `resources allocate-dp [cap]` — 0/1 knapsack via DP (integer items)

### Routes (Dijkstra / Floyd–Warshall)

* `routes add-edge [u v km]` — add a bidirectional road edge
* `routes plan [from] [to]` — shortest path via Dijkstra
* `routes plan-all` — all-pairs shortest paths via Floyd–Warshall
* `routes network` — print the current road network

### Teams (Backtracking / Branch & Bound)

* `teams add` — add a rescue team
* `teams list` — list all teams
* `teams assign` — assign teams using backtracking
* `teams assign-optimal [budget]` — optimize assignments via Branch & Bound

### Dispatch (end-to-end pipeline)

* `dispatch run [--bnb] [--dp] [budget]` — run the full 6-stage pipeline
  * `--bnb` uses Branch & Bound for team assignment (otherwise backtracking)
  * `--dp` uses 0/1 knapsack DP for resource allocation (otherwise fractional knapsack)
  * `budget` is a number (deployment units); default is `1000`
* `dispatch status` — print the current dispatch plan summary
* `dispatch replan` — re-run the pipeline using the current state

### Demo

* `demo load` — load a pre-built scenario into the in-memory store
* `demo run` — load + show requests/resources/teams + compute routes + run dispatch
* `demo run-bnb` — run demo dispatch with B&B and a fixed budget

## Project layout

* `main.py` — CLI + REPL, command routing, demo scenario
* `data_store.py` — shared in-memory state (singleton)
* `python modules/`
  * `priority_agent.py` — request ranking
  * `resource_allocator.py` — knapsack allocators
  * `route_planner.py` — graph + route planning
  * `network_analyzer.py` — all-pairs matrix + connectivity report
  * `team_assigner.py` — team assignment logic
  * `optimizer.py` — Branch & Bound optimizer
  * `replanner.py` — orchestrates the full dispatch pipeline

## Notes

* State is kept in memory for the current run. If you restart the program, run `demo load` again (or add data interactively).
* On Windows terminals, ANSI colors are enabled automatically where possible.
