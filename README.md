# LIFLUCT

Pronounced: `"li-fluct"`

> Open policy lab for adversarial liquidity systems

LIFLUCT is an open-source simulation and adjudication stack for evaluating AMM liquidity policies under adversarial flow.

Instead, the current focus is narrower and more practical:

- search for strong fixed or semi-fixed liquidity policies
- compare them fairly against strong baselines
- stress-test them across adverse regimes
- surface failure modes rather than hiding them
- support guarded deployment decisions

## Whitepaper

- [English whitepaper](https://github.com/zotanika/lifluct/blob/main/docs/whitepaper_en.md)
- [한국어 백서](https://github.com/zotanika/lifluct/blob/main/docs/whitepaper_ko.md)

## For Readers New To Crypto

If you are coming from economics, finance, computer science, or policy rather than from day-to-day crypto operations, a few terms matter:

- `smart contract`: code deployed onto a blockchain network that can hold and move assets according to predefined rules
- `devnet`: a controlled development network used for early testing
- `testnet`: a public test network where systems can be exercised without meaningful real capital
- `mainnet`: the live blockchain network where real assets, real users, and real losses exist
- `deployment`: the act of publishing code or activating parameters where users or capital can actually interact with them

In AMM systems, money does not move in the abstract. It moves between traders, liquidity providers, arbitrageurs, and sometimes protocol treasuries. A policy that looks elegant on paper can still fail badly once real users, latency, and adversarial flow appear.

That is why LIFLUCT emphasizes pre-deployment review, guarded rollout reasoning, monitoring, and rollback criteria rather than just attractive simulation charts.

## What LIFLUCT Is

LIFLUCT is a policy lab for onchain liquidity systems.

It is designed to help answer questions like:

- does a proposed policy outperform a strong single-strategy baseline?
- does the result hold up under different volatility and oracle conditions?
- does performance come at unacceptable trader-cost or failure risk?
- what breaks first when the environment turns adversarial?

## What LIFLUCT Is Not

LIFLUCT is not:

- a proof that any strategy is profitable in production
- a black-box alpha engine
- a live self-modifying AMM product
- a claim that attributed loss is exact ground truth

This repository exists to make mechanism claims easier to audit, reject, refine, or cautiously support.

## Why This Repo Is Open

Mechanism research is easy to overstate when:

- baselines are weak
- failure cases are buried
- attribution choices are opaque
- results are cherry-picked

LIFLUCT is open because the useful part of this work depends on:

- inspectable assumptions
- reproducible runs
- visible failure regimes
- fair comparisons

## Current Thesis

LIFLUCT studies whether liquidity policies survive strong comparison and adverse conditions.

The public focus today is:

- offline policy search
- best-fixed and semi-fixed strategy evaluation
- adversarial stress testing
- attribution robustness
- explicit failure reporting
- guarded deployment and rollback reasoning

## Core Capabilities

- deterministic simulation for 2-asset CPMM-style pools
- static and dynamic single-strategy baselines
- best-fixed single-policy search
- regime-family comparison
- train/test evaluation
- attribution robustness analysis
- failure-flag reporting
- plots, markdown reports, and aggregate outputs

## Key Design Principles

### 1. Strong baselines first

If a well-tuned fixed policy can match or beat a more adaptive mechanism, then the adaptive mechanism does not deserve extra complexity by default.

### 2. Negative results matter

This repository is designed to show failure cases, not just wins.

### 3. Heuristics should be labeled honestly

Attributed loss, trader-cost proxies, and some failure diagnostics are useful heuristics, not perfect economic truth.

### 4. Regimes matter more than anecdotes

A few runs are not evidence. Family-level comparisons across multiple regimes and seeds matter more than a good-looking single chart.

## Repository Structure

```text
lifluct/
  README.md
  pyproject.toml
  requirements.txt
  lifluct/
    core/
    baselines/
    reporting/
    orchestration/
    cli/
    configs/
  notebooks/
  docs/
  tests/
```

The exact folder names may evolve, but the intended public shape is:

- `core/` for simulation, policy evaluation, and diagnostics
- `baselines/` for fair comparator models
- `reporting/` for reports, tables, plots, and adjudication
- `orchestration/` for large experiment scheduling and retention modes
- `cli/` for reproducible runs and report generation

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Run a smoke example:

```bash
python -m lifluct.cli.run_simulation --config lifluct/configs/baseline_dynamic.yaml
```

Run a best-fixed search:

```bash
python -m lifluct.cli.run_best_fixed_search \
  --manifest lifluct/configs/best_fixed_smoke.yaml
```

Run a family-level comparison:

```bash
python -m lifluct.cli.run_regime_family \
  --family-config lifluct/configs/phase42/no_lysis_regime_family.yaml \
  --best-fixed-config runs/phase42/best_fixed_search/best_candidate_config.yaml
```

## Outputs

Depending on retention mode, a run or family can produce:

- run summary
- epoch summaries
- cell snapshots
- aggregate statistics
- markdown reports
- comparison tables
- failure-flag prevalence summaries
- plots for LP outcome, trader cost, concentration, lysis, and attribution stability

## What Remains Heuristic

The following remain heuristic or approximate by design:

- attributed loss
- trader-cost proxy
- some adversary models
- some failure-flag triggers
- lysis as a practical circuit-breaker approximation

These are kept because they can still be useful for disciplined evaluation, but they are not presented as exact truth.

## Why Best-Fixed Matters

LIFLUCT treats best-fixed single-policy search as a first-class baseline.

If a mechanism cannot beat or at least meaningfully justify itself against a strong fixed policy, then it may not deserve live complexity.

## Why Failure Cases Are First-Class

A policy can look attractive on LP outcome while still being weak because of:

- trader-cost deterioration
- oracle fragility
- lysis cascades
- concentration collapse
- dead-volume behavior

This repository is designed to surface those regimes explicitly.

## Intended Use

LIFLUCT is best used for:

- mechanism research
- pre-deployment policy review
- treasury or POL strategy evaluation
- stress testing under stylized adversarial regimes
- comparing candidate mechanisms against disciplined baselines
- teaching and critical review

Open source does not mean "non-commercial" or "purely academic." In this domain, practical value often appears through hosted experiment infrastructure, deployment review, policy audits, monitoring rules, and operational support built around an open evaluation core.

Typical charging models in this kind of stack are not mysterious: subscription access to hosted compute, usage-based batch experimentation, fixed-scope pre-deployment reviews, and ongoing monitoring or incident-support retainers.

## Not Included

This repository does not aim to provide:

- mainnet contract code
- concentrated liquidity design
- governance/token systems
- trader-facing frontend UX
- proof of real-world profitability

## Public Roadmap

Near-term public goals:

1. make the repo cleaner and easier to reproduce
2. improve best-fixed and policy-selection workflows
3. strengthen report quality and negative-result visibility
4. package the stack so external reviewers can run it without internal context

## License

TBD. A permissive license such as Apache-2.0 is a likely default if the project is released as an open policy lab.

## Citation / Attribution

If you use the repository for research or protocol evaluation, cite the repo and state clearly:

- which configs were used
- whether results were in-sample or out-of-sample
- what attribution mode was used
- what failure cases were observed

## Final Note

LIFLUCT is not trying to make liquidity policy look smarter than it is.

The goal is simpler:

> make it easier to evaluate, challenge, and deploy liquidity policies honestly under adverse conditions
