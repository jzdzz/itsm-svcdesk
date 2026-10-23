---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 80% - analysis of DORA edge cases and Goodhart's law demonstration -->

# Edge cases in the practice event log

## E1 - clock skew produces a negative lead time

- What the log contains: Three instances where commit timestamps occur strictly after the deployment timestamp that included them due to unsynchronized system clocks.
- What a default definition would have done: Naive implementations either drop these pairs entirely or calculate a negative duration that distorts the aggregate median.
- Why the rule is defensible: Clamping negative values to zero ensures the delivery event is acknowledged without skewing the distribution with mathematically invalid negative intervals.

## E2 - a revert of a revert

- What the log contains: Two revert commits that target previous revert commits, resolving cyclically back to the original change identifier.
- What a default definition would have done: Typical parsers treat each revert commit as an independent unit of work, erroneously inflating the total change count by three.
- Why the rule is defensible: Resolving revert chains transitively attributes all related actions to a single original change, preserving accurate change accounting.

## E3 - a hotfix that never touched `main`

- What the log contains: Four distinct production commits delivered directly from topic or release branches that were never merged into the main branch.
- What a default definition would have done: Filtering changes strictly by branch name (e.g., branch equals main) omits these emergency fixes from throughput statistics.
- Why the rule is defensible: Every commit reaching production constitutes an active release regardless of branching strategy, so omitting off-main commits misrepresents delivery frequency.

## E4 - a deployment with zero linked commits

- What the log contains: Four production deployments whose commit arrays are empty, representing operational rollbacks, environment checks, or pipeline verifications.
- What a default definition would have done: Calculations that divide by commit count cause division-by-zero errors or inappropriately exclude the deployment from failure metrics.
- Why the rule is defensible: An operational deployment alters the state of the production environment, so it must count toward overall deployment frequency and failure baselines.

## E5 - a deployment that failed and never recovered

- What the log contains: One failed production deployment that has no associated incident resolution recorded prior to the closing of the observation window.
- What a default definition would have done: Default algorithms either drop unrecovered deployments from the failure count or invent an arbitrary artificial recovery timestamp.
- Why the rule is defensible: Excluding unresolved failures from the median recovery duration while still counting them in the change failure rate prevents underreporting system instability.

## E6 - overlapping incidents

- What the log contains: Eleven pairs of distinct production incidents whose active remediation intervals overlap concurrently in time.
- What a default definition would have done: Implementations often merge concurrent incidents into a single block or aggregate their wall-clock durations additively.
- Why the rule is defensible: Calculating recovery per failed deployment rather than per incident isolates the actual outage duration experienced by each individual release.

## Gaming demonstration

Under rule R-11, the deployment frequency metric was targeted for artificial inflation. By submitting automated, empty production deployments carrying zero changes and removing commit associations from routine deployments, the calculated deployment frequency rose by 50%, increasing from 2.0 to 3.0 deployments per day. Concurrently, real feature delivery was completely paralyzed, dropping the delivered changes metric from 65 to 0, which decisively satisfies the harm threshold.

In a real engineering organization, teams evaluated primarily on raw release frequency are heavily incentivized to execute decoupled or empty deployments simply to satisfy management activity metrics. Dashboards register an apparent surge in operational agility, which may be rewarded with team bonuses. However, actual customer delivery is compromised because real, value-adding code changes remain unreleased and disconnected from deployment pipelines.