"""Failure notifications for Airflow tasks.

Always logs the failure. When ALERT_WEBHOOK_URL is set, also POSTs a
Slack-compatible JSON body ({"text": ...}); Slack, Mattermost, Google Chat and
Microsoft Teams workflow webhooks accept this shape.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request

log = logging.getLogger(__name__)


def failure_message(context: dict) -> str:
    ti = context["task_instance"]
    run = context.get("run_id", "?")
    url = getattr(ti, "log_url", "")
    error = context.get("exception")
    lines = [
        f":red_circle: Airflow task failed: {ti.dag_id}.{ti.task_id}",
        f"run: {run} · try {ti.try_number}",
    ]
    if error:
        lines.append(f"error: {str(error)[:500]}")
    if url:
        lines.append(f"log: {url}")
    return "\n".join(lines)


def notify_failure(context: dict) -> None:
    message = failure_message(context)
    log.error(message)
    webhook = os.getenv("ALERT_WEBHOOK_URL")
    if not webhook:
        return
    request = urllib.request.Request(
        webhook,
        data=json.dumps({"text": message}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            pass
    except Exception:  # an alerting outage must not mask the task failure
        log.exception("Failed to deliver failure alert")
