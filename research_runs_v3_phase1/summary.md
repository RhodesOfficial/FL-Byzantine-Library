# Research suite summary

Completed: 0/18

All numbers are descriptive; compare matched seeds and equal threat budgets before making claims.
Completed means the process exited and wrote a record. High loss (>100) and loss explosion (>1e6 or non-finite) are diagnostic flags.
Condition means are shown only when every planned seed completed; see CSV for individual runs and failures.

| Phase | Condition | Completed / planned | Failures | Mean final accuracy | Mean ASR | Mean minority false reject | Mean p95 server ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | baseline_backdoor | 0/3 | 0 | — | — | — | — |
| 1 | baseline_ipm | 0/3 | 0 | — | — | — | — |
| 1 | baseline_none | 0/3 | 0 | — | — | — | — |
| 1 | triage_backdoor | 0/3 | 0 | — | — | — | — |
| 1 | triage_ipm | 0/3 | 0 | — | — | — | — |
| 1 | triage_none | 0/3 | 0 | — | — | — | — |

## Interpretation notes

- Phase 1: evaluate minority false rejection jointly with clean accuracy and attack damage.
- Phase 2: joint_random and joint_timing share the same vector rule and delay bound; inspect realized staleness before attributing changes to timing choice.
- Phase 3: trusted clients are reserved from ordinary training. With root IDs 2,11, random sampling and label noise also change observed class coverage, so noise and coverage effects are confounded.
- Phase 4: the deadline is soft. Report p95 aggregation time, deadline misses and virtual training time together.
- Only backdoor conditions have an ASR. IPM and timing conditions use accuracy degradation and update diagnostics.
