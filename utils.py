from typing import Sequence
from models import IntervalDict

def merge_adjacent_intervals(intervals: Sequence[IntervalDict]) -> list[IntervalDict]:
    if not intervals:
        return []

    sorted_intervals = sorted(intervals, key=lambda x: x["start"])
    merged = [sorted_intervals[0].copy()]

    for current in sorted_intervals[1:]:
        last = merged[-1]
        if current["type"] == last["type"] and current["start"] <= last["end"]:
            if current["end"] > last["end"]:
                last["end"] = current["end"]
        else:
            merged.append(current.copy())

    return merged
