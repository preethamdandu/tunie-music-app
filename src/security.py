"""
Security and telemetry helpers for TuneGenie.

This module provides:
- Optional license enforcement via a remote check endpoint
- Privacy-safe telemetry pings (opt-out) to a user-provided endpoint

All behavior is controlled via environment variables so the repository remains
open-source friendly while allowing owners to restrict usage in their deployments.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

import requests


def _parse_bool_env(var_name: str, default: str = "False") -> bool:
    value = os.getenv(var_name, default)
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _data_dir() -> str:
    directory = os.path.join("data")
    os.makedirs(directory, exist_ok=True)
    return directory


def get_installation_id() -> str:
    """Return a stable, pseudo-anonymous installation id.

    Persists a UUIDv4 in data/installation_id.txt on first run.
    """
    install_id_path = os.path.join(_data_dir(), "installation_id.txt")
    try:
        if os.path.exists(install_id_path):
            with open(install_id_path, "r") as f:
                installation_id = f.read().strip()
                if installation_id:
                    return installation_id
        installation_id = str(uuid.uuid4())
        with open(install_id_path, "w") as f:
            f.write(installation_id)
        return installation_id
    except Exception:
        # Fallback to ephemeral id if filesystem is not writable
        return str(uuid.uuid4())


def telemetry_ping(event_name: str, extra_payload: Optional[Dict] = None) -> None:
    """Send a best-effort telemetry ping if enabled.

    Controlled by:
      - TUNIE_TELEMETRY_OPTOUT: when true, telemetry is disabled
      - TUNIE_TELEMETRY_URL: endpoint to POST JSON payloads to
      - TUNIE_APP_VERSION: optional version string
    """
    if _parse_bool_env("TUNIE_TELEMETRY_OPTOUT", "False"):
        return

    telemetry_url = os.getenv("TUNIE_TELEMETRY_URL")
    if not telemetry_url:
        return

    payload: Dict = {
        "event": event_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "installation_id": get_installation_id(),
        "app_name": os.getenv("TUNIE_APP_NAME", "TuneGenie"),
        "app_version": os.getenv("TUNIE_APP_VERSION", "0.0.0"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
    }

    if extra_payload:
        payload.update(extra_payload)

    try:
        headers = {"Content-Type": "application/json"}
        requests.post(telemetry_url, data=json.dumps(payload), headers=headers, timeout=3)
    except Exception:
        # Never raise: telemetry must be best-effort and non-blocking
        pass


def _license_check_remote(license_key: str) -> Tuple[bool, str]:
    """Validate a license key against a remote endpoint.

    Expects the endpoint to accept JSON POST and return JSON like:
      { "valid": true, "message": "ok" }
    """
    check_url = os.getenv("TUNIE_LICENSE_CHECK_URL")
    if not check_url:
        return False, "License server not configured (TUNIE_LICENSE_CHECK_URL)"

    payload = {
        "license_key": license_key,
        "installation_id": get_installation_id(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "app_name": os.getenv("TUNIE_APP_NAME", "TuneGenie"),
        "app_version": os.getenv("TUNIE_APP_VERSION", "0.0.0"),
    }

    try:
        response = requests.post(check_url, json=payload, timeout=5)
        if response.status_code != 200:
            return False, f"License server error: HTTP {response.status_code}"
        data = response.json()
        valid = bool(data.get("valid"))
        message = str(data.get("message", ""))
        return (True, message) if valid else (False, message or "License invalid")
    except Exception as exc:
        return False, f"License check failed: {exc}"


def check_license() -> Tuple[bool, str]:
    """Check license according to environment configuration.

    Controlled by:
      - TUNIE_ENFORCE_LICENSE: when true, require valid license
      - TUNIE_LICENSE_KEY: the license string to validate
      - TUNIE_LICENSE_CHECK_URL: remote validation endpoint
    """
    if not _parse_bool_env("TUNIE_ENFORCE_LICENSE", "False"):
        return True, "License enforcement disabled"

    license_key = os.getenv("TUNIE_LICENSE_KEY", "").strip()
    if not license_key:
        return False, "Missing TUNIE_LICENSE_KEY"

    return _license_check_remote(license_key)


def initialize_security() -> Tuple[bool, str]:
    """Initialize telemetry and license checks.

    Returns:
        (ok, message) where ok is True if app can proceed.
    """
    telemetry_ping("app_started")
    ok, message = check_license()
    if not ok:
        telemetry_ping("license_denied", {"reason": message})
        return False, message
    telemetry_ping("license_ok")
    return True, message


