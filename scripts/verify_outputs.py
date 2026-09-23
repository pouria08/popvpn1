"""Validate the generated artefacts.

Used by the GitHub Action right after a run so a broken pipeline never gets
committed:

    python scripts/verify_outputs.py

Checks performed:

* ``base64.txt`` decodes and matches ``working_configs.txt`` line for line
* ``outputs/stats.json`` agrees with the number of published configs
* ``outputs/clash.yaml`` parses as YAML and every proxy has server+port
* ``outputs/singbox.json`` parses as JSON and has outbounds
* every published URI is re-parseable by the pipeline's own parser
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Artefacts are written relative to the current working directory, so that is
# also where the scripts look for them.
WORKDIR = Path.cwd()

from popvpn.protocols import parse_uri  # noqa: E402


def _fail(errors: list[str], message: str) -> None:
    errors.append(message)
    print(f"  ✗ {message}")


def _ok(message: str) -> None:
    print(f"  ✓ {message}")


def verify(root: Path = WORKDIR) -> list[str]:
    errors: list[str] = []
    print("[verify] checking generated outputs")

    plain_path = root / "working_configs.txt"
    base64_path = root / "base64.txt"
    stats_path = root / "outputs" / "stats.json"

    for path in (plain_path, base64_path, stats_path):
        if not path.exists():
            _fail(errors, f"missing {path}")
    if errors:
        return errors

    plain = plain_path.read_text(encoding="utf-8")
    uris = [line for line in plain.splitlines() if "://" in line]
    _ok(f"{len(uris)} configs in working_configs.txt")

    decoded = base64.b64decode(base64_path.read_text().strip()).decode("utf-8")
    if decoded.splitlines() != uris:
        _fail(errors, "base64.txt does not match working_configs.txt")
    else:
        _ok("base64.txt matches working_configs.txt")

    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    if stats.get("total") != len(uris):
        _fail(errors, f"stats.json total={stats.get('total')} != published {len(uris)}")
    else:
        _ok(f"stats.json agrees ({len(uris)})")

    quality = stats.get("quality", {})
    probe = stats.get("probe", {})
    if quality.get("require_verified"):
        if probe.get("mode") not in {"tcp", "tls"}:
            _fail(errors, "strict publication requires a tcp or tls probe")
        if len(uris) > int(probe.get("configs_alive", 0)):
            _fail(errors, "published config count exceeds fresh verified configs")
        verified_path = root / "outputs" / "verified.txt"
        if not verified_path.exists():
            _fail(errors, f"missing {verified_path}")
        else:
            verified_uris = [line for line in verified_path.read_text(encoding="utf-8").splitlines() if "://" in line]
            if verified_uris != uris:
                _fail(errors, "strict all.txt and verified.txt do not match")
            else:
                _ok("strict output contains verified configs only")

    invalid = [uri for uri in uris if parse_uri(uri) is None]
    if invalid:
        _fail(errors, f"{len(invalid)} published URIs do not re-parse, e.g. {invalid[0][:80]}")
    else:
        _ok("every published URI re-parses")

    if not plain.startswith("#profile-title:"):
        _fail(errors, "working_configs.txt is missing the Hiddify profile header")
    else:
        _ok("profile header present")

    clash_path = root / "outputs" / "clash.yaml"
    if clash_path.exists():
        try:
            import yaml  # type: ignore

            document = yaml.safe_load(clash_path.read_text(encoding="utf-8"))
            proxies = document.get("proxies", [])
            broken = [p for p in proxies if not p.get("server") or not p.get("port")]
            if broken:
                _fail(errors, f"{len(broken)} clash proxies miss server/port")
            else:
                _ok(f"clash.yaml valid ({len(proxies)} proxies)")
        except ImportError:
            print("  · PyYAML not installed, skipping clash.yaml validation")
        except Exception as exc:  # noqa: BLE001 - report any parse problem
            _fail(errors, f"clash.yaml invalid: {exc}")

    singbox_path = root / "outputs" / "singbox.json"
    if singbox_path.exists():
        try:
            document = json.loads(singbox_path.read_text(encoding="utf-8"))
            outbounds = document.get("outbounds", [])
            if len(outbounds) < 4:
                _fail(errors, "singbox.json has no outbounds")
            else:
                _ok(f"singbox.json valid ({len(outbounds)} outbounds)")
        except ValueError as exc:
            _fail(errors, f"singbox.json invalid: {exc}")

    print("[verify] " + ("FAILED" if errors else "OK"))
    return errors


if __name__ == "__main__":
    failures = verify()
    raise SystemExit(1 if failures else 0)
