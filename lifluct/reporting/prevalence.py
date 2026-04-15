"""Failure-flag prevalence helpers for regime-family reports."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Sequence

from lifluct.types import FailureModeObservation


def failure_flag_prevalence(
    run_payloads: Sequence[dict[str, Any]],
    *,
    group_by: str = "model_type",
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for payload in run_payloads:
        metadata = payload.get("metadata", {})
        key = str(metadata.get(group_by, metadata.get("model_type", payload["config"].baseline_type)))
        grouped[key].append(payload)

    rows: list[dict[str, Any]] = []
    for key, members in grouped.items():
        flag_counts: Counter[tuple[str, str]] = Counter()
        pair_counts: Counter[tuple[str, str]] = Counter()
        total_flags = 0
        critical_runs = 0
        for payload in members:
            names = []
            critical_here = False
            for mode in payload.get("failure_modes", []):
                if isinstance(mode, FailureModeObservation):
                    flag_counts[(mode.mode, mode.severity)] += 1
                    names.append(mode.mode)
                    critical_here = critical_here or mode.severity == "critical"
                else:
                    flag_counts[(str(mode), "warning")] += 1
                    names.append(str(mode))
            total_flags += len(names)
            if critical_here:
                critical_runs += 1
            for index, left in enumerate(sorted(set(names))):
                for right in sorted(set(names))[index + 1 :]:
                    pair_counts[(left, right)] += 1
        top_pair = ""
        if pair_counts:
            (left, right), count = pair_counts.most_common(1)[0]
            top_pair = f"{left}+{right}:{count}"
        for (flag_name, severity), count in flag_counts.items():
            rows.append(
                {
                    group_by: key,
                    "failure_flag": flag_name,
                    "severity": severity,
                    "fraction_of_runs": count / len(members),
                    "avg_failure_flags_per_run": total_flags / len(members),
                    "critical_fraction": critical_runs / len(members),
                    "top_cooccurring_pair": top_pair,
                }
            )
    return rows
