from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def _safe_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_numeric(values: List[str]) -> bool:
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return False
    return sum(1 for v in non_empty if _safe_float(v) is not None) / len(non_empty) >= 0.8


def _field_stats(values: List[str]) -> Dict[str, Any]:
    non_empty = [v for v in values if v.strip()]
    total = len(values)
    missing = total - len(non_empty)
    stats: Dict[str, Any] = {
        "count": total,
        "missing": missing,
        "missing_pct": round(missing / total * 100, 2) if total else 0.0,
        "unique": len(set(non_empty)),
    }
    if _is_numeric(non_empty):
        nums = sorted(float(v) for v in non_empty if _safe_float(v) is not None)
        n = len(nums)
        if n:
            mean = sum(nums) / n
            stats["type"] = "numeric"
            stats["min"] = nums[0]
            stats["max"] = nums[-1]
            stats["mean"] = round(mean, 4)
            stats["std"] = round(math.sqrt(sum((x - mean) ** 2 for x in nums) / n), 4)
            mid = n // 2
            stats["median"] = nums[mid] if n % 2 else (nums[mid - 1] + nums[mid]) / 2
    else:
        stats["type"] = "categorical"
        freq: Dict[str, int] = {}
        for v in non_empty:
            freq[v] = freq.get(v, 0) + 1
        top = sorted(freq.items(), key=lambda x: -x[1])[:5]
        stats["top_values"] = [{"value": k, "count": c} for k, c in top]
    return stats
