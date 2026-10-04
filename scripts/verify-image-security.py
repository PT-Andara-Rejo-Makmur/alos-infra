"""Validate complete Trivy reports; retain unfixed findings for the production gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


# This audited collector is built from scratch; it has no distribution packages.
# Accept only this exact release with a completed Go binary scan, never a generic
# missing OS result. Updating the collector requires updating this reviewed pin.
SCRATCH_COLLECTOR = "otel/opentelemetry-collector@sha256:310a800ad69ee430e7c541796852a242c9c7db97aaad4daa5ccf843c525fbdb2"


def verified_scratch_collector(report: dict, results: list) -> bool:
    metadata = report.get("Metadata") or {}
    config = metadata.get("ImageConfig") or {}
    return (
        not metadata.get("OS")
        and SCRATCH_COLLECTOR in (metadata.get("RepoDigests") or [])
        and bool(metadata.get("DiffIDs"))
        and (config.get("config") or {}).get("Entrypoint") == ["/otelcol"]
        and any(result.get("Class") == "lang-pkgs" and result.get("Type") == "gobinary"
                and result.get("Target") == "otelcol" for result in results)
    )


def inspect_report(report: dict, *, strict: bool = False) -> dict:
    results = report.get("Results")
    if report.get("SchemaVersion") != 2 or not isinstance(results, list) or not results:
        raise ValueError("Missing or unsupported Trivy image report")
    if report.get("ArtifactType") != "container_image":
        raise ValueError("Expected a container image scan")
    if not any(result.get("Class") == "os-pkgs" for result in results) and not verified_scratch_collector(report, results):
        raise ValueError("OS package analysis is missing")
    counts = {"total": 0, "high_critical": 0, "fixable_high_critical": 0, "blocked": 0}
    for result in results:
        findings = result.get("Vulnerabilities")
        if findings is None:
            findings = []
        if not isinstance(findings, list):
            raise ValueError("Invalid vulnerability collection")
        for finding in findings:
            if (not isinstance(finding, dict) or not finding.get("VulnerabilityID")
                    or finding.get("Severity") not in {"UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"}):
                raise ValueError("Invalid vulnerability finding")
            counts["total"] += 1
            if finding.get("Severity") not in {"HIGH", "CRITICAL"}:
                continue
            counts["high_critical"] += 1
            fixable = bool(finding.get("FixedVersion"))
            counts["fixable_high_critical"] += int(fixable)
            counts["blocked"] += int(strict or fixable)
    return {"image": report.get("ArtifactName"), "strict": strict, **counts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--strict", action="store_true",
                        help="Block all HIGH/CRITICAL findings, including those without a patch")
    args = parser.parse_args()
    summaries = []
    for path in args.reports:
        try:
            summaries.append(inspect_report(json.loads(path.read_text()), strict=args.strict))
        except (OSError, ValueError, TypeError, AttributeError) as error:
            print(f"Invalid image security report {path.name}: {error}")
            return 1
    print(json.dumps(summaries, indent=2))
    return int(any(summary["blocked"] for summary in summaries))


if __name__ == "__main__":
    raise SystemExit(main())
