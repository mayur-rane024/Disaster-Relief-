# AgentRelief CLI (Disaster Relief Coordination System)

AgentRelief is a Python command-line application that helps coordinate disaster relief operations by:

- **Prioritizing** incoming requests based on urgency and impact
- **Allocating** limited resources optimally (greedy vs dynamic programming)
- **Planning routes** over a road network using graph algorithms
- **Assigning rescue teams** (greedy/backtracking vs optimal branch-and-bound)
- **Generating dispatch plans** that can be replanned as conditions change

This project is intended for learning/demonstration of classic algorithms in an applied scenario.

## Project Structure

```
├── main.py                    # CLI entry point - command router and REPL
├── app.py                     # Streamlit UI for Algorithm Arena
├── data_store.py              # Shared in-memory state (singleton)
├── pyproject.toml             # Project metadata (uv/pip)
├── requirements.txt           # Python dependencies
├── README.md                  # This file
│
├── arena/                     # Algorithm benchmarking & evaluation
│   ├── pipeline.py            # Benchmark pipeline orchestrator
│   ├── evaluator.py           # Algorithm result analysis
│   └── algorithms/            # Core algorithm implementations
│       ├── allocation.py      # Resource allocation (greedy, DP)
│       ├── assignment.py      # Team-to-request assignment
│       ├── prioritization.py  # Request ranking/priority
│       └── routing.py         # Route planning algorithms
│
└── python modules/            # Core agent/manager modules
    ├── priority_agent.py      # Request prioritization engine
    ├── resource_allocator.py  # Resource distribution logic
    ├── route_planner.py       # Graph-based routing
    ├── team_assigner.py       # Team assignment logic
    ├── network_analyzer.py    # All-pairs shortest path cache
    ├── optimizer.py           # Optimization utilities
    └── replanner.py           # Dynamic replanning engine
```

## Installation & Setup

### Prerequisites

- Python ≥ 3.11
- pip and [uv](https://github.com/astral-sh/uv) (recommended for faster installs)

### Quick Start (Windows)

**Step 1: Clone and navigate to the project**

```powershell
cd c:\DAA-mini-project\Relief-Disaster\Disaster-Relief-
```

**Step 2: Set PowerShell execution policy (if needed)**

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

**Step 3: Create and activate virtual environment**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Step 4: Install dependencies**

```powershell
# Using uv (fastest)
pip install uv
uv sync

# OR using pip directly
pip install -r requirements.txt
```

**Step 5: Verify installation**

```powershell
python main.py help
```

## Run Modes

### 1. CLI Demo (One-Shot Execution)

Run the complete demo scenario with default data:

```powershell
# Standard greedy dispatch
python main.py demo run

# With branch-and-bound team assignment (optimal but slower)
python main.py demo run --bnb
```

### 2. Interactive REPL

Launch the command-line interface for manual data entry and testing:

```powershell
python main.py
```

Inside the REPL, available commands:

**Request Management**

```
requests add <priority> <location> <description>  # Add a relief request
requests list                                      # Show all requests
requests rank                                      # Rank by priority
requests show <id>                                 # View request details
requests remove <id>                               # Delete a request
```

**Resource Management**

```
resources add <name> <qty> <location>       # Add a resource
resources list                               # Show all resources
resources allocate [cap]                     # Greedy allocation (capacity cap)
resources allocate-dp [cap]                  # DP-based allocation
```

**Route/Network Management**

```
routes add-edge <node1> <node2> <km>  # Add road segment
routes plan <from> <to>               # Find shortest path
routes plan-all                        # Plan routes for all assignments
routes network                         # Show network stats
```

**Team Management**

```
teams add <name> <skills>              # Register a rescue team
teams list                             # Show all teams
teams assign                           # Greedy team-to-request assignment
teams assign-optimal [budget]          # Branch-and-bound assignment (with pruning budget)
```

**Dispatch & Replanning**

```
dispatch run [--bnb] [budget]    # Run full dispatch (generate plan)
dispatch replan                   # Replan if conditions change
dispatch status                   # Show current dispatch state
```

**Utility**

```
help  # Show all commands
cls   # Clear screen
exit  # Quit REPL
```

### 3. Streamlit Algorithm Arena (Interactive UI)

Benchmark and visualize different algorithms side-by-side:

```powershell
streamlit run app.py
```

Opens a web interface (default: http://localhost:8501) with:

- Algorithm comparison charts
- Performance metrics
- Resource allocation visualizations
- Route planning visualization
- Interactive scenario builder

## Example Workflow

### Via CLI Demo

```powershell
python main.py demo run
# Outputs: Full dispatch plan with team assignments, routes, resource allocations, and timing
```

### Via Interactive REPL

```powershell
python main.py

# Inside REPL:
> requests add 9 "Downtown Hospital" "Critical medical supplies needed"
> resources add "Medical Kit" 50 "Distribution Center"
> teams add "Alpha" "medical,transport"
> resources allocate
> teams assign
> dispatch run
> routes plan-all
> dispatch status
> exit
```

## Key Algorithms

| Component           | Algorithm                              | Location                             |
| ------------------- | -------------------------------------- | ------------------------------------ |
| Prioritization      | Weighted scoring (urgency × impact)    | `arena/algorithms/prioritization.py` |
| Resource Allocation | Greedy matching, Dynamic Programming   | `arena/algorithms/allocation.py`     |
| Team Assignment     | Greedy, Backtracking, Branch-and-Bound | `arena/algorithms/assignment.py`     |
| Route Planning      | Dijkstra's / Floyd-Warshall            | `arena/algorithms/routing.py`        |
| Replanning          | Dynamic check and reassign             | `python modules/replanner.py`        |

## Configuration

- **Algorithm parameters**: Edit `pyproject.toml` for package configuration
- **Data persistence**: Uses in-memory `DataStore` singleton (no database)
- **Dependencies**: See `requirements.txt` for all packages

## Troubleshooting

| Issue                    | Solution                                                                                     |
| ------------------------ | -------------------------------------------------------------------------------------------- |
| "ModuleNotFoundError"    | Ensure `.venv` is activated and dependencies installed via `pip install -r requirements.txt` |
| PowerShell blocks script | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`                       |
| Streamlit not found      | Run `pip install streamlit plotly pandas`                                                    |
| Port 8501 already in use | `streamlit run app.py --server.port 8502`                                                    |

## Development Notes

- **Path handling**: The project auto-adds the root and `python modules/` directories to `sys.path`
- **Module imports**: Core modules are in `python modules/` (space in directory name)
- **Singleton pattern**: `DataStore` ensures all modules share state
- **Testing**: Run individual commands via CLI demo or REPL

## Requirements

See [requirements.txt](requirements.txt):

- `pydantic>=2.12.5` – Data validation
- `streamlit>=1.35.0` – Web UI framework
- `plotly>=5.20.0` – Interactive visualizations
- `pandas>=2.0.0` – Data manipulation

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

- `requests add` — interactively add a disaster request
- `requests list` — show all requests sorted by priority score
- `requests rank` — alias for `requests list`
- `requests show <id>` — show full details for a request
- `requests remove <id>` — remove a request

### Resources (Fractional knapsack / 0/1 knapsack DP)

- `resources add` — add a resource to the pool
- `resources list` — list resources with value/weight ratios
- `resources allocate [cap]` — fractional knapsack allocation (greedy)
- `resources allocate-dp [cap]` — 0/1 knapsack via DP (integer items)

### Routes (Dijkstra / Floyd–Warshall)

- `routes add-edge [u v km]` — add a bidirectional road edge
- `routes plan [from] [to]` — shortest path via Dijkstra
- `routes plan-all` — all-pairs shortest paths via Floyd–Warshall
- `routes network` — print the current road network

### Teams (Backtracking / Branch & Bound)

- `teams add` — add a rescue team
- `teams list` — list all teams
- `teams assign` — assign teams using backtracking
- `teams assign-optimal [budget]` — optimize assignments via Branch & Bound

### Dispatch (end-to-end pipeline)

- `dispatch run [--bnb] [--dp] [budget]` — run the full 6-stage pipeline
  - `--bnb` uses Branch & Bound for team assignment (otherwise backtracking)
  - `--dp` uses 0/1 knapsack DP for resource allocation (otherwise fractional knapsack)
  - `budget` is a number (deployment units); default is `1000`
- `dispatch status` — print the current dispatch plan summary
- `dispatch replan` — re-run the pipeline using the current state

### Demo

- `demo load` — load a pre-built scenario into the in-memory store
- `demo run` — load + show requests/resources/teams + compute routes + run dispatch
- `demo run-bnb` — run demo dispatch with B&B and a fixed budget

## Project layout

- `main.py` — CLI + REPL, command routing, demo scenario
- `data_store.py` — shared in-memory state (singleton)
- `python modules/`
  - `priority_agent.py` — request ranking
  - `resource_allocator.py` — knapsack allocators
  - `route_planner.py` — graph + route planning
  - `network_analyzer.py` — all-pairs matrix + connectivity report
  - `team_assigner.py` — team assignment logic
  - `optimizer.py` — Branch & Bound optimizer
  - `replanner.py` — orchestrates the full dispatch pipeline

## Notes

- State is kept in memory for the current run. If you restart the program, run `demo load` again (or add data interactively).
- On Windows terminals, ANSI colors are enabled automatically where possible.
