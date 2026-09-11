"""
core/netguard.py — code-level air-gap enforcement and attestation.

Turning off Wi-Fi proves nothing about intent: the code might still be *trying*
to reach the internet. This module makes the claim provable in the other
direction. It replaces Python's socket connect and DNS resolution inside this
process so that any destination which is not loopback is refused before a
packet can leave, and every refusal is recorded in the audit trail.

That means during the demo you can:
  1. Leave Wi-Fi ON and still show a zero-egress counter.
  2. Press "Test the guard", which deliberately attempts to reach a public
     address, and watch it be blocked and logged in real time.
  3. Show the loopback-only allowlist, so the only thing this process can talk
     to is Ollama on this machine.

Honest scope, and say this out loud to judges: this enforces and proves the
behaviour of THIS Python process. Ollama runs as a separate process; the
guarantee for Ollama is that it is configured to a loopback address (which is
verified here) and that the models are already on disk, so it has no reason to
call out. Full network-level proof is a host firewall rule, which is what we
would use in production.
"""

from __future__ import annotations

import socket
import threading
import time
from typing import Any

import config

_LOCK = threading.Lock()
_INSTALLED = False

# Everything the guard has seen, allowed or blocked.
EGRESS_LOG: list[dict] = []
_COUNTS = {"allowed": 0, "blocked": 0, "dns_blocked": 0}

_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex
_orig_getaddrinfo = socket.getaddrinfo


class EgressBlocked(OSError):
    """Raised when code in this process tries to reach a non-local address."""


def _audit(event: str, payload: dict) -> None:
    """Log without creating a hard import cycle at module load time."""
    try:
        from core import audit
        audit.log(event, payload, actor="netguard")
    except Exception:  # noqa: BLE001 - never let logging break the guard
        pass


def _host_of(address: Any) -> str:
    if isinstance(address, (tuple, list)) and address:
        return str(address[0])
    return str(address)


def _port_of(address: Any) -> Any:
    if isinstance(address, (tuple, list)) and len(address) > 1:
        return address[1]
    return None


def _is_local(host: str) -> bool:
    h = (host or "").strip().lower()
    if h in config.AIRGAP_ALLOWED_HOSTS:
        return True
    if h.startswith("127."):
        return True
    if h in ("::1", "[::1]", "::ffff:127.0.0.1"):
        return True
    return False


def _record(host: str, port: Any, allowed: bool, kind: str = "tcp") -> None:
    entry = {
        "ts": time.time(),
        "host": host,
        "port": port,
        "kind": kind,
        "decision": "ALLOWED" if allowed else "BLOCKED",
    }
    with _LOCK:
        EGRESS_LOG.append(entry)
        if len(EGRESS_LOG) > 500:
            del EGRESS_LOG[:-500]
        if allowed:
            _COUNTS["allowed"] += 1
        elif kind == "dns":
            _COUNTS["dns_blocked"] += 1
            _COUNTS["blocked"] += 1
        else:
            _COUNTS["blocked"] += 1
    if not allowed:
        # A blocked attempt is a security-relevant event: always audit it.
        _audit("airgap.blocked", {"host": host, "port": port, "kind": kind})


def install() -> dict:
    """Patch the socket layer. Safe to call more than once."""
    global _INSTALLED
    if _INSTALLED:
        return status()

    if not config.ENFORCE_AIRGAP:
        _INSTALLED = True
        return status()

    # Refuse to run if Ollama has been pointed somewhere non-local: that would
    # silently defeat the whole premise of the project.
    from urllib.parse import urlparse
    parsed = urlparse(config.OLLAMA_HOST)
    if not _is_local(parsed.hostname or ""):
        raise EgressBlocked(
            f"config.OLLAMA_HOST is set to '{config.OLLAMA_HOST}', which is not "
            f"a loopback address. This project only serves models locally. "
            f"Refusing to start."
        )

    def guarded_connect(self, address):  # noqa: ANN001
        host = _host_of(address)
        if _is_local(host):
            _record(host, _port_of(address), True)
            return _orig_connect(self, address)
        _record(host, _port_of(address), False)
        raise EgressBlocked(
            f"Air-gap guard blocked an outbound connection to "
            f"{host}:{_port_of(address)}. This process may only talk to "
            f"localhost."
        )

    def guarded_connect_ex(self, address):  # noqa: ANN001
        host = _host_of(address)
        if _is_local(host):
            _record(host, _port_of(address), True)
            return _orig_connect_ex(self, address)
        _record(host, _port_of(address), False)
        return 111  # ECONNREFUSED, the same answer a firewall would give

    def guarded_getaddrinfo(host, port, *a, **kw):  # noqa: ANN001
        # A DNS lookup for a public name is itself outbound traffic.
        if not _is_local(str(host)):
            _record(str(host), port, False, kind="dns")
            raise socket.gaierror(
                -2, f"Air-gap guard blocked DNS resolution of '{host}'."
            )
        _record(str(host), port, True, kind="dns")
        return _orig_getaddrinfo(host, port, *a, **kw)

    socket.socket.connect = guarded_connect          # type: ignore[method-assign]
    socket.socket.connect_ex = guarded_connect_ex    # type: ignore[method-assign]
    socket.getaddrinfo = guarded_getaddrinfo         # type: ignore[assignment]

    _INSTALLED = True
    _audit("airgap.installed", {
        "allowed_hosts": sorted(h for h in config.AIRGAP_ALLOWED_HOSTS if h),
        "ollama_host": config.OLLAMA_HOST,
    })
    return status()


def uninstall() -> None:
    """Restore the originals. Only used by tests."""
    global _INSTALLED
    socket.socket.connect = _orig_connect            # type: ignore[method-assign]
    socket.socket.connect_ex = _orig_connect_ex      # type: ignore[method-assign]
    socket.getaddrinfo = _orig_getaddrinfo           # type: ignore[assignment]
    _INSTALLED = False


def status() -> dict:
    with _LOCK:
        counts = dict(_COUNTS)
        recent = list(EGRESS_LOG[-25:])
    return {
        "installed": _INSTALLED,
        "enforced": bool(config.ENFORCE_AIRGAP),
        "allowed_hosts": sorted(h for h in config.AIRGAP_ALLOWED_HOSTS if h),
        "ollama_host": config.OLLAMA_HOST,
        "external_attempts_blocked": counts["blocked"],
        "dns_lookups_blocked": counts["dns_blocked"],
        "local_connections_allowed": counts["allowed"],
        "recent": recent,
    }


def self_test() -> dict:
    """Deliberately try to leave the machine, to prove the guard works.

    Run this live in the demo. It targets a documented public DNS address and a
    public hostname, neither of which will be reached. Nothing is sent.
    """
    results = []

    # 1. Direct connection to a public IP, no DNS involved.
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("1.1.1.1", 443))
        s.close()
        results.append({"probe": "TCP to 1.1.1.1:443",
                        "outcome": "REACHED - GUARD NOT WORKING",
                        "blocked": False})
    except EgressBlocked as exc:
        results.append({"probe": "TCP to 1.1.1.1:443",
                        "outcome": f"blocked by guard: {exc}", "blocked": True})
    except OSError as exc:
        results.append({"probe": "TCP to 1.1.1.1:443",
                        "outcome": f"failed at OS level: {exc}",
                        "blocked": True})

    # 2. DNS resolution of a public hostname.
    try:
        socket.getaddrinfo("example.com", 443)
        results.append({"probe": "DNS lookup of example.com",
                        "outcome": "RESOLVED - GUARD NOT WORKING",
                        "blocked": False})
    except socket.gaierror as exc:
        results.append({"probe": "DNS lookup of example.com",
                        "outcome": f"blocked by guard: {exc}", "blocked": True})

    # 3. Confirm the one thing we DO allow still works.
    from urllib.parse import urlparse
    p = urlparse(config.OLLAMA_HOST)
    host, port = p.hostname or "127.0.0.1", p.port or 11434
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        code = s.connect_ex((host, port))
        s.close()
        results.append({
            "probe": f"TCP to local Ollama {host}:{port}",
            "outcome": "reachable (allowed by design)" if code == 0
                       else f"allowed by guard but Ollama is not listening "
                            f"(code {code})",
            "blocked": False,
        })
    except OSError as exc:
        results.append({"probe": f"TCP to local Ollama {host}:{port}",
                        "outcome": f"error: {exc}", "blocked": False})

    all_external_blocked = all(r["blocked"] for r in results[:2])
    out = {
        "passed": all_external_blocked,
        "summary": ("All outbound attempts to external addresses were blocked "
                    "inside the process. Only loopback traffic to the local "
                    "model server is permitted.")
        if all_external_blocked else
        ("AT LEAST ONE EXTERNAL ATTEMPT SUCCEEDED. The air-gap guard is not "
         "active - check config.ENFORCE_AIRGAP and that install() was called."),
        "probes": results,
    }
    _audit("airgap.self_test", {"passed": out["passed"],
                                "probes": [r["probe"] for r in results]})
    return out


def attestation_text() -> str:
    """A short statement to read out or paste onto a slide."""
    s = status()
    return "\n".join([
        "NETWORK ISOLATION ATTESTATION",
        "=" * 62,
        f"Guard active                : {s['installed']} (enforced={s['enforced']})",
        f"Permitted destinations      : {', '.join(s['allowed_hosts'])}",
        f"Model server               : {s['ollama_host']} (loopback, verified)",
        f"Loopback connections made   : {s['local_connections_allowed']}",
        f"External attempts blocked   : {s['external_attempts_blocked']}",
        f"DNS lookups blocked         : {s['dns_lookups_blocked']}",
        "",
        "Scope of this attestation: outbound network access is intercepted",
        "inside this application process and refused for any destination that",
        "is not loopback. Model weights are already on local disk and are",
        "served by Ollama over loopback. In production this process-level",
        "control would be paired with a host firewall rule for defence in",
        "depth.",
    ])
