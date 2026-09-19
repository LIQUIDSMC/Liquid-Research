# Research Vault

## Purpose

This is a permanent home for ideas, leads, observations, and
questions collected from Twitter/X, GitHub, blog posts, papers,
YouTube, Reddit, Discord, wallet observations, API discoveries,
Claude conversations, and anything else encountered during
development.

Nothing in this folder is active engineering work. Nothing here
is promised, scheduled, or assumed correct. This is a parking lot,
not a backlog.

## Roadmap vs. Research Vault

`L0_PLATFORM/zROADMAP.md` is the canonical portfolio roadmap. It
governs portfolio-level priorities and promotion decisions.

`L4_KNOWLEDGE/` is the shared Research Vault for unreviewed or
partially reviewed ideas, hypotheses, observations, questions,
archived research state, and future concepts.

Material moves from the Research Vault into active portfolio or
engine work only after deliberate review and an explicit promotion
decision, never automatically.

The roadmap is not a changelog. Git history records completed work,
while engine- and domain-specific documents record detailed
methodology, experiment state, and operational checkpoints.

## Implementation vs. Hypothesis

A hypothesis is an untested claim. Implementation is code that has
been built, tested, and verified against real data, per the
Research Integrity Principles in `L0_PLATFORM/zROADMAP.md`.
Material in this vault may be a finding, hypothesis, lead,
question, note, or archived research state. None of it is
implementation. No code. No automation. No scanners.

## Research Integrity Rules

These are non-negotiable, regardless of how confident a source
sounds.

A screenshot is not evidence.
A tweet is not evidence.
A GitHub repository is not evidence.
A YouTube video is not evidence.
An AI-generated answer is not evidence.

Evidence requires verification, meaning it was checked directly,
not taken on faith. Evidence requires reproduction, meaning the
result shows up again under the same conditions. Evidence requires
measurable results, meaning a number, a comparison, or a real
outcome.

A claim with none of these stays in twitter_leads.md,
github_repositories.md, and similar files as an unreviewed lead.
A claim with all three earns a place in validated_findings.md.

## The Research Funnel

Every entry in this vault moves along one of three paths.

Path one: Unreviewed, then Reviewing, then Rejected.

Path two: Unreviewed, then Reviewing, then Archived.

Path three: Unreviewed, then Reviewing, then Experiment, then
Roadmap.

Default assumption: most ideas are noise. Most never become
roadmap items. That is expected, not a failure of the process.

Rough distribution to expect over time: most ideas end up
Rejected. Some ideas end up Archived, meaning interesting but not
now. Fewer ideas become controlled Experiments. Very few
Experiments become Roadmap items. Even fewer Roadmap items become
a genuine, measured edge.

The vault's job is preservation, not validation. It exists so a
potentially useful idea is never lost just because it wasn't
reviewed the day it was found, and so a bad idea is never
re-investigated twice because nobody remembered rejecting it once.

## Naming Conventions

Use kebab-case or plain sentence fragments for entry titles.
Consistency matters less than clarity.

Dates always in YYYY-MM-DD format.

Wallet addresses always written in full, lowercase, exactly as
returned by the API.

Status field values are always exactly one of: Unreviewed,
Reviewing, Rejected, Archived, Experiment, Promoted.

Every entry gets a date. No undated entries.

## Files in This Vault

twitter_leads.md holds claims and ideas found on Twitter/X.

github_repositories.md holds repos with potentially useful
techniques, data, or architecture ideas.

papers.md holds research papers, articles, and formal writeups.

wallet_observations.md holds interesting wallet behavior not yet
formalized into a hypothesis.

api_discoveries.md holds undocumented or surprising API behavior.

market_hypotheses.md holds testable claims about trader skill or
market mispricing.

future_experiments.md holds ideas specific enough to describe how
they would be tested, not yet scheduled.

validated_findings.md holds discoveries verified against real data.

open_questions.md holds important unanswered questions not yet
tied to a hypothesis, experiment, or roadmap item.

dead_ends.md holds ideas tested or seriously considered that did
not hold up.

archived_ideas.md holds ideas consciously set aside, not rejected.
