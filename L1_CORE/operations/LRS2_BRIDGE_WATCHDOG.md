# LRS2 bridge publication watchdog

## Scope and status

This monitor checks Pi3's local bridge evidence independently of the daily
orchestrator. It does not run the bridge, update either checkout, inspect
research data, create checkpoints, or transfer research authority.

Source and reference units are provided here. Production installation and
unattended verification are not yet complete.

## Conditions

The latest complete evidence record determines FAILED or EVIDENCE_ERROR.
A valid PASS must include publication identity and false research-authority
flags. After 06:00 America/Los_Angeles, publication must have occurred since
that day's 05:00 scheduled cycle. Before 06:00, the preceding day's cycle
remains acceptable. The default grace is 60 minutes; DST is handled using
the Pacific timezone.

HEALTHY describes current local publication evidence. It does not independently
recheck Pi5 files or guarantee their continued availability. A later successful
attempt supersedes an earlier failed attempt.

## Notifications

Run the monitor every five minutes using the reference systemd timer.
ntfy sends condition changes and recovery notifications. Unchanged conditions
are suppressed after successful delivery. Failed sends are retried on the next
monitor invocation. A failed attempt that is superseded between monitor polls
may not generate a notification.

Healthchecks receives a heartbeat only when publication is healthy and any
required ntfy notification succeeded. Use a dedicated check with a five-minute
period and five-minute grace. Silence can indicate unhealthy publication,
notification failure, or a stopped monitor; inspect monitor logs to distinguish
these conditions. Never reuse either machine-health endpoint.

## Local configuration and deployment boundary

Install the reviewed script outside the checkout at:
`/home/kristo/lrs2_bridge_watchdog/lrs2_bridge_watchdog.py`

Create an owner-only configuration at:
`/home/kristo/lrs2_bridge_watchdog/config.json`

Configuration must be owned by the service user and have mode 600.
Provision the existing ntfy topic and a new dedicated Healthchecks ping URL
locally. Do not commit real configuration or print secrets in chat or logs.
The state directory should be private to kristo (mode 700).

Install reviewed reference units under /etc/systemd/system only after audit.
Activation requires synthetic failure/retry/recovery checks, actual notification
delivery, healthy heartbeat verification, and an unattended timer firing.

The bridge's strict matching-commit requirement remains unchanged. Coordinate
runtime deployments; this watchdog reports failures rather than repairing them.

## Verification

Run:
`python3 -m unittest discover -s L1_CORE/operations -p 'test_lrs2_bridge_watchdog.py' -v`

Tests use synthetic evidence, temporary directories, and mocked network calls.
Production notification delivery and scheduling require separate verification.

## Schedule configuration and alert initialization

`expected_daily_time` and `schedule_timezone` explicitly pair this monitor
with the orchestrator timer. Defaults are 05:00 and America/Los_Angeles.
Whenever the orchestrator schedule changes, update this configuration and
verify the pair before deployment. Automatic schedule-drift detection is
not implemented.

An initial healthy invocation seeds notification state without an ntfy alert.
Initial problems still alert. Recovery alerts require an earlier successfully
notified problem. Loss of notification state follows the same startup rule.

An old FAIL predating the latest due cycle becomes STALE_FAILURE: both the
failed attempt and missing current-cycle evidence need investigation. This
does not prove that the scheduler itself is dead.
