"""
resource_allocator.py
Algorithms:
  • Fractional Knapsack  (greedy, O(n log n)) — default, fast, good for divisible goods
  • 0/1 Knapsack DP      (exact,  O(n·W))     — set use_dp=True for indivisible items

Purpose : Determine which resources to load onto a carrier given a weight
          capacity limit, maximising total value.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List


class resource_schema(BaseModel):
    id:       str   = Field(..., description="Unique resource identifier")
    name:     str   = Field(..., description="Human-readable name")
    weight:   float = Field(..., description="Weight per unit (kg)")
    value:    float = Field(..., description="Value / priority of resource")
    quantity: float = Field(..., description="Available quantity")


class resource_allocator:
    """
    Loads a subset of resources onto a transport carrier within a weight cap.
    Default mode: Fractional Knapsack (greedy).
    DP mode     : 0/1 Knapsack — treats each resource type as take-all-or-none.
    """

    allocated_resources: List[resource_schema]

    def __init__(self, resources: List[dict], capacity: float, use_dp: bool = False):
        self.allocated_resources = []
        self.capacity = capacity
        self.use_dp   = use_dp
        resource_list = [resource_schema(**r) for r in resources]

        if use_dp:
            self._knapsack_01(resource_list, capacity)
        else:
            self._fractional(resource_list, capacity)

    # ── Fractional Knapsack (greedy) ──────────────────────────────────────
    def _fractional(self, resources: List[resource_schema], capacity: float):
        resources.sort(key=lambda r: r.value / max(r.weight, 1e-9), reverse=True)
        remaining = capacity

        for res in resources:
            if remaining <= 0:
                break
            total_w = res.weight * res.quantity
            if total_w <= remaining:
                self.allocated_resources.append(res)
                remaining -= total_w
            else:
                fraction = remaining / max(res.weight, 1e-9)
                self.allocated_resources.append(
                    resource_schema(
                        id=res.id, name=res.name,
                        weight=res.weight, value=res.value,
                        quantity=round(fraction, 3)
                    )
                )
                remaining = 0.0

    # ── 0/1 Knapsack DP ──────────────────────────────────────────────────
    # Each resource type is treated as one item (take ALL quantity or NONE).
    # Weights are scaled ×10 and cast to int so the DP table stays tractable.
    def _knapsack_01(self, resources: List[resource_schema], capacity: float):
        SCALE = 10                                  # 1 decimal precision
        W     = int(round(capacity * SCALE))        # integer capacity

        items: List[resource_schema] = resources
        n     = len(items)
        weights = [int(round(r.weight * r.quantity * SCALE)) for r in items]
        values  = [r.value * r.quantity                       for r in items]

        # dp[i][w] = max value using items 0..i-1 with int-capacity w
        # space-optimised: 1-D rolling array
        dp = [0.0] * (W + 1)
        for i in range(n):
            wi, vi = weights[i], values[i]
            for w in range(W, wi - 1, -1):          # iterate right-to-left
                dp[w] = max(dp[w], dp[w - wi] + vi)

        # Back-track selected items
        selected = []
        w = W
        for i in range(n - 1, -1, -1):
            wi, vi = weights[i], values[i]
            if w >= wi and dp[w] == dp[w - wi] + vi:
                selected.append(items[i])
                w -= wi

        self.allocated_resources = selected

    # ── helpers ──────────────────────────────────────────────────────────
    def total_weight(self) -> float:
        return sum(r.weight * r.quantity for r in self.allocated_resources)

    def total_value(self) -> float:
        return sum(r.value * r.quantity for r in self.allocated_resources)

    def print_allocated_resources(self):
        mode = "0/1 Knapsack DP" if self.use_dp else "Fractional Knapsack"
        print(f"Allocated Resources  [{mode}]  capacity={self.capacity} kg:")
        for res in self.allocated_resources:
            print(
                f"  ID={res.id}  Name={res.name:<20} "
                f"Qty={res.quantity:.2f}  "
                f"Weight={res.weight * res.quantity:.2f} kg  "
                f"Value={res.value * res.quantity:.2f}"
            )
        print(f"  ── Total weight: {self.total_weight():.2f} kg  "
              f"| Total value: {self.total_value():.2f}")


# ── Quick test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    resources = [
        {"id": "r1", "name": "Water",    "weight": 10, "value": 100, "quantity": 5},
        {"id": "r2", "name": "Food",     "weight": 20, "value": 200, "quantity": 3},
        {"id": "r3", "name": "Medicine", "weight": 5,  "value": 150, "quantity": 10},
        {"id": "r4", "name": "Tents",    "weight": 15, "value": 90,  "quantity": 4},
    ]
    cap = 200
    print("=== Fractional Knapsack ===")
    resource_allocator(resources, cap, use_dp=False).print_allocated_resources()
    print("\n=== 0/1 Knapsack DP ===")
    resource_allocator(resources, cap, use_dp=True).print_allocated_resources()
