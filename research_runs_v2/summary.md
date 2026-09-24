# Research suite summary

Completed: 75/105

All numbers are descriptive; compare matched seeds and equal threat budgets before making claims.
Completed means the process exited and wrote a record. High loss (>100) and loss explosion (>1e6 or non-finite) are diagnostic flags.
Condition means are shown only when every planned seed completed; see CSV for individual runs and failures.

| Phase | Condition | Completed / planned | Failures | Mean final accuracy | Mean ASR | Mean minority false reject | Mean p95 server ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | baseline_backdoor | 3/3 | 0 | 0.2666 | 0.3060 | — | 63.4289 |
| 1 | baseline_ipm | 1/3 | 2 | — | — | — | — |
| 1 | baseline_none | 3/3 | 0 | 0.2403 | — | — | 59.6386 |
| 1 | triage_backdoor | 3/3 | 0 | 0.3665 | 0.3363 | — | 65.8758 |
| 1 | triage_ipm | 2/3 | 1 | — | — | — | — |
| 1 | triage_none | 3/3 | 0 | 0.2278 | — | — | 66.7234 |
| 2 | baseline_ipm | 0/3 | 3 | — | — | — | — |
| 2 | baseline_joint_random | 2/3 | 1 | — | — | — | — |
| 2 | baseline_joint_timing | 2/3 | 1 | — | — | — | — |
| 2 | baseline_timed_ipm | 2/3 | 1 | — | — | — | — |
| 2 | triage_ipm | 1/3 | 2 | — | — | — | — |
| 2 | triage_joint_random | 2/3 | 1 | — | — | — | — |
| 2 | triage_joint_timing | 3/3 | 0 | 0.2769 | — | — | 75.3722 |
| 2 | triage_timed_ipm | 3/3 | 0 | 0.2514 | — | — | 62.0618 |
| 3 | baseline_reserved_root | 2/3 | 1 | — | — | — | — |
| 3 | root_fusion_class0_only | 3/3 | 0 | 0.0973 | — | 0.0000 | 74.4350 |
| 3 | root_fusion_n100_noise0.0 | 2/3 | 1 | — | — | — | — |
| 3 | root_fusion_n100_noise0.2 | 1/3 | 2 | — | — | — | — |
| 3 | root_fusion_n20_noise0.0 | 2/3 | 1 | — | — | — | — |
| 3 | root_fusion_n20_noise0.2 | 3/3 | 0 | 0.1176 | — | 0.0000 | 68.6388 |
| 3 | root_only_class0_only | 1/3 | 2 | — | — | — | — |
| 3 | root_only_n100_noise0.0 | 3/3 | 0 | 0.5393 | — | 0.0000 | 71.8216 |
| 3 | root_only_n100_noise0.2 | 3/3 | 0 | 0.8266 | — | 0.0000 | 68.8784 |
| 3 | root_only_n20_noise0.0 | 1/3 | 2 | — | — | — | — |
| 3 | root_only_n20_noise0.2 | 3/3 | 0 | 0.4053 | — | 0.0000 | 67.6165 |
| 4 | anytime_ipm_10ms | 1/3 | 2 | — | — | — | — |
| 4 | anytime_ipm_2ms | 2/3 | 1 | — | — | — | — |
| 4 | anytime_ipm_50ms | 2/3 | 1 | — | — | — | — |
| 4 | anytime_joint_timing_10ms | 3/3 | 0 | 0.3442 | — | — | 71.9195 |
| 4 | anytime_joint_timing_2ms | 3/3 | 0 | 0.3241 | — | — | 69.1709 |
| 4 | anytime_joint_timing_50ms | 3/3 | 0 | 0.4919 | — | — | 71.5703 |
| 4 | baseline_ipm | 2/3 | 1 | — | — | — | — |
| 4 | baseline_joint_timing | 3/3 | 0 | 0.3151 | — | — | 68.6130 |
| 4 | triage_ipm | 1/3 | 2 | — | — | — | — |
| 4 | triage_joint_timing | 1/3 | 2 | — | — | — | — |

## Interpretation notes

- Phase 1: evaluate minority false rejection jointly with clean accuracy and attack damage.
- Phase 2: joint_random and joint_timing share the same vector rule and delay bound; inspect realized staleness before attributing changes to timing choice.
- Phase 3: trusted clients are reserved from ordinary training. With root IDs 2,11, random sampling and label noise also change observed class coverage, so noise and coverage effects are confounded.
- Phase 4: the deadline is soft. Report p95 aggregation time, deadline misses and virtual training time together.
- Only backdoor conditions have an ASR. IPM and timing conditions use accuracy degradation and update diagnostics.
