# Liquid Research

Liquid Research is an independent software and quantitative-research project for building reproducible market-data pipelines and testing market hypotheses with explicit methodology, validation, and research-integrity controls.

The repository combines data engineering, research infrastructure, market-domain logic, and independent research engines. The governing principle is simple: **measure first, preserve evidence, and do not promote a hypothesis beyond what the data supports.**

> **Status:** Active research and engineering project. Liquid Research is not a live trading system and does not claim a validated profitable strategy.

## [Architecture](L0_PLATFORM/zARCHITECTURE.md)

Liquid Research uses an ownership-based L0-L4 structure:

| Layer | Responsibility |
|---|---|
| `L0_PLATFORM/` | Platform governance, architecture, roadmap, and canonical operating authority |
| `L1_CORE/` | Shared infrastructure, orchestration, and market-data platform components |
| `L2_DOMAINS/` | Domain-specific market acquisition, selection, publication, and research context |
| `L3_RESEARCH_ENGINES/` | Independent research engines with isolated hypotheses and methodology |
| `L4_KNOWLEDGE/` | Shared findings, open questions, hypotheses, and future research concepts |

The architecture separates **data/domain ownership** from **research-engine ownership** so downstream research can consume documented interfaces without silently reconstructing upstream decisions.

## Current Research Systems

### [Market Selection](L3_RESEARCH_ENGINES/market_selection/zMISSION_CONTROL.md)

Prediction-market selection and paper-research infrastructure for studying whether measurable market characteristics are associated with different outcomes.

### [Market Microstructure](L3_RESEARCH_ENGINES/market_microstructure/zREADME.md)

Order-book research including Order Book Imbalance, Micro-Price, Near-Book Depth Imbalance, divergence analysis, and stability tracking.

### [Market Data / Crypto Trade Flow](L2_DOMAINS/crypto/zREADME.md)

Shared market-data infrastructure plus crypto trade-flow research using Coinbase BTC-USD and ETH-USD data. Work includes trade and depth collection, instrument-identity validation, causal data-boundary design, duplicate-event analysis, and reproducible historical experiments.

### [Market Regimes](L3_RESEARCH_ENGINES/market_regime_intelligence/README.md)

An independent regime-research engine studying whether pre-defined market states provide useful explanatory or conditioning information. Methodology changes are controlled through explicit freeze and supersession rules before outcome-dependent analysis is authorized.

## Runtime Infrastructure

Runtime placement is separate from research ownership:

- **Pi3 (`liquid-pi`)** is the authoritative live market-data collector and
  canonical persistence node.
- **Pi5 (`liquid-pi5`)** hosts heavier analytical workloads. The implemented
  LRS2 bridge supplies verified, bounded snapshots for local analysis.

Cross-node research inputs should be immutable, provenance-bearing snapshots.
Pi5's analytical role does not transfer live-writer authority or imply that
every engine's data-transfer workflow has been deployed.

See the [runtime architecture](L0_PLATFORM/zARCHITECTURE.md) for the governing
constraints. Runtime availability must be established from current monitoring,
not inferred from this README.

## Automation and Monitoring

Automate repeatable operational work and documented threshold checks as part
of completing the workflow. Research judgment and methodology changes remain
with the owning research engine.

Shared operations include:

- Scheduled orchestration and service supervision.
- Independent five-minute machine-health watchdogs on Pi3 and Pi5.
- LRS2 bridge publication monitoring for failed or overdue snapshot delivery.
- Checkpoint alerts driven by thresholds documented by the owning engine.

**ntfy** provides problem, recovery, and milestone notifications.
**Healthchecks.io** detects missing healthy heartbeats. Independent monitors
use separate checks so one healthy process cannot mask another's silence.
Notification secrets remain in host-local configuration, outside Git.

Shared implementations and operating notes live in
[`L1_CORE/operations/`](L1_CORE/operations/). A checkpoint alert requests review;
it does not establish statistical significance, profitability, or a validated
research finding.

## Engineering Principles

Liquid Research follows several project-wide rules:

- **Evidence over assumptions.**
- Reproduce and measure before promoting a finding.
- Treat unusually strong results as potential bugs until independently checked.
- Freeze experiment methodology before evaluating the outcomes it governs.
- Keep independent experiments isolated to reduce methodological contamination.
- Fail loudly when required data or identity assumptions are invalid.
- Preserve incident records and superseded research when they remain necessary for provenance.
- Prefer stable producer/consumer contracts over coupling research to internal files.
- Separate observed results from claims of predictive or trading value.

## Engineering Scope

The repository includes work involving:

- Python
- REST and WebSocket market-data acquisition
- CSV, JSON, and Parquet data pipelines
- Pandas, NumPy, and PyArrow
- deterministic validation and data-quality checks
- historical and incremental research workflows
- automated tests
- Linux and Raspberry Pi deployment
- systemd services and scheduled orchestration
- Git/GitHub version control
- reproducible quantitative research documentation

## Repository Map

```text
Liquid Research/
├── L0_PLATFORM/
│   ├── zARCHITECTURE.md
│   ├── zHANDOFF.md
│   └── zROADMAP.md
├── L1_CORE/
│   ├── market_data_platform/
│   ├── operations/
│   └── orchestrator.py
├── L2_DOMAINS/
│   ├── crypto/
│   └── prediction_markets/
├── L3_RESEARCH_ENGINES/
│   ├── market_microstructure/
│   ├── market_regime_intelligence/
│   ├── market_selection/
│   └── wallet_intelligence/
└── L4_KNOWLEDGE/
```

Individual research engines maintain their own methodology, implementation, tests, state, and research artifacts where appropriate. Shared findings and open questions belong in `L4_KNOWLEDGE/`.

## Research Integrity

A result being statistically interesting does not by itself establish causality, predictive value, executable profitability, or suitability for live trading.

Liquid Research deliberately preserves distinctions between:

1. an observation,
2. a hypothesis,
3. a reproducible result,
4. a validated research finding,
5. an executable trading edge.

Those stages are not treated as interchangeable.

## Operating Documentation

- [Architecture](L0_PLATFORM/zARCHITECTURE.md) — ownership, runtime roles,
  boundaries, and data contracts.
- [Operating manual](L0_PLATFORM/zHANDOFF.md) — project principles and workflow.
- [Roadmap](L0_PLATFORM/zROADMAP.md) — portfolio priorities and planned work.

Engine-specific control documents govern methodology, experiment state,
readiness, and authorized research access. Infrastructure capability does not
itself authorize production execution or access to sealed research outcomes.

## Project Status

The repository is under active development. Some historical documents and research artifacts intentionally preserve terminology, paths, or assumptions from earlier project phases because they are part of the research record.

Current operational and architectural documentation is being consolidated around the L0-L4 structure while historical evidence is preserved rather than silently rewritten.

## License

No open-source license is currently granted for this repository. All rights are reserved unless explicitly stated otherwise.
