# Research suite summary

Completed: 35/35

All numbers are descriptive; compare matched seeds and equal threat budgets before making claims.
Completed means the process exited and wrote a record; run_health flags loss above 1e6 or non-finite loss.

| Phase | Condition | Runs | Mean final accuracy | Mean ASR | Mean minority false reject | Mean p95 server ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | baseline_backdoor | 1 | 0.1843 | 0.0035 | — | 19.5743 |
| 1 | baseline_ipm | 1 | 0.2720 | — | — | 16.9678 |
| 1 | baseline_none | 1 | 0.3357 | — | — | 18.8341 |
| 1 | triage_backdoor | 1 | 0.3194 | 0.0415 | — | 25.1631 |
| 1 | triage_ipm | 1 | 0.0958 | — | — | 22.5770 |
| 1 | triage_none | 1 | 0.3051 | — | — | 24.9128 |
| 2 | baseline_ipm | 1 | 0.2674 | — | — | 16.8390 |
| 2 | baseline_joint_random | 1 | 0.2376 | — | — | 19.4614 |
| 2 | baseline_joint_timing | 1 | 0.2677 | — | — | 18.6250 |
| 2 | baseline_timed_ipm | 1 | 0.0982 | — | — | 18.2985 |
| 2 | triage_ipm | 1 | 0.0958 | — | — | 22.4979 |
| 2 | triage_joint_random | 1 | 0.3137 | — | — | 23.6906 |
| 2 | triage_joint_timing | 1 | 0.2141 | — | — | 20.5318 |
| 2 | triage_timed_ipm | 1 | 0.1259 | — | — | 22.4081 |
| 3 | baseline_reserved_root | 1 | 0.0958 | — | 0.0000 | 20.3455 |
| 3 | root_fusion_class0_only | 1 | 0.1028 | — | 0.0000 | 49.1929 |
| 3 | root_fusion_n100_noise0.0 | 1 | 0.1028 | — | 0.0000 | 46.3886 |
| 3 | root_fusion_n100_noise0.2 | 1 | 0.1028 | — | 0.0000 | 47.5923 |
| 3 | root_fusion_n20_noise0.0 | 1 | 0.1028 | — | 0.0000 | 40.8249 |
| 3 | root_fusion_n20_noise0.2 | 1 | 0.1028 | — | 0.0000 | 41.7007 |
| 3 | root_only_class0_only | 1 | 0.1000 | — | 0.0000 | 48.7532 |
| 3 | root_only_n100_noise0.0 | 1 | 0.1032 | — | 0.0000 | 45.6749 |
| 3 | root_only_n100_noise0.2 | 1 | 0.0974 | — | 0.0000 | 45.5241 |
| 3 | root_only_n20_noise0.0 | 1 | 0.1032 | — | 0.0000 | 42.4455 |
| 3 | root_only_n20_noise0.2 | 1 | 0.1032 | — | 0.0000 | 42.5478 |
| 4 | anytime_ipm_10ms | 1 | 0.1932 | — | — | 46.7606 |
| 4 | anytime_ipm_2ms | 1 | 0.1817 | — | — | 45.7159 |
| 4 | anytime_ipm_50ms | 1 | 0.1929 | — | — | 46.0561 |
| 4 | anytime_joint_timing_10ms | 1 | 0.1127 | — | — | 42.0426 |
| 4 | anytime_joint_timing_2ms | 1 | 0.1152 | — | — | 39.8163 |
| 4 | anytime_joint_timing_50ms | 1 | 0.0892 | — | — | 40.6869 |
| 4 | baseline_ipm | 1 | 0.2131 | — | — | 38.5014 |
| 4 | baseline_joint_timing | 1 | 0.2396 | — | — | 38.5283 |
| 4 | triage_ipm | 1 | 0.0958 | — | — | 49.1585 |
| 4 | triage_joint_timing | 1 | 0.1946 | — | — | 40.3743 |

## Interpretation notes

- Phase 1: evaluate minority false rejection jointly with clean accuracy and attack damage.
- Phase 2: joint_random and joint_timing share the same vector rule and delay bound; inspect realized staleness before attributing changes to timing choice.
- Phase 3: trusted clients are reserved from ordinary training in every phase-3 condition. Root noise and class coverage are controlled separately.
- Phase 4: the deadline is soft. Report p95 aggregation time, deadline misses and virtual training time together.
- Only backdoor conditions have an ASR. IPM and timing conditions use accuracy degradation and update diagnostics.
