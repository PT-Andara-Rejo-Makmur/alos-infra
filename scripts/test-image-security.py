"""Ensure the image gate cannot turn absent or unfixed findings into a clean claim."""

import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("image_security", Path(__file__).with_name("verify-image-security.py"))
image_security = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image_security)


def report(findings):
    return {"SchemaVersion": 2, "ArtifactType": "container_image", "ArtifactName": "image:fixture",
            "Results": [{"Class": "os-pkgs", "Vulnerabilities": findings}]}


class ImageSecurityTest(unittest.TestCase):
    def test_only_reviewed_scratch_collector_with_binary_scan_is_accepted(self):
        fixture = {**report([]), "Results": [{"Class": "lang-pkgs", "Type": "gobinary", "Target": "otelcol"}],
                   "Metadata": {"RepoDigests": [image_security.SCRATCH_COLLECTOR], "DiffIDs": ["sha256:fixture"],
                                "ImageConfig": {"config": {"Entrypoint": ["/otelcol"]}}}}
        self.assertEqual(image_security.inspect_report(fixture, strict=True)["blocked"], 0)
        for override in ({"RepoDigests": ["unreviewed/image@sha256:fixture"]},
                         {"DiffIDs": []}, {"OS": {"Family": "debian"}}, {"ImageConfig": {}}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                image_security.inspect_report({**fixture, "Metadata": {**fixture["Metadata"], **override}})
        with self.assertRaises(ValueError):
            image_security.inspect_report({**fixture, "Results": [{"Class": "lang-pkgs"}]})

    def test_fixable_high_blocks_and_medium_remains_visible(self):
        summary = image_security.inspect_report(report([
            {"VulnerabilityID": "CVE-fixture-high", "Severity": "HIGH", "FixedVersion": "2"},
            {"VulnerabilityID": "CVE-fixture-medium", "Severity": "MEDIUM", "FixedVersion": "2"},
        ]))
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["blocked"], 1)

    def test_unfixed_is_reported_and_strict_gate_blocks(self):
        fixture = report([{"VulnerabilityID": "CVE-fixture", "Severity": "CRITICAL"}])
        summary = image_security.inspect_report(fixture)
        self.assertEqual(summary["high_critical"], 1)
        self.assertEqual(summary["fixable_high_critical"], 0)
        self.assertEqual(summary["blocked"], 0)
        self.assertEqual(image_security.inspect_report(fixture, strict=True)["blocked"], 1)

    def test_incomplete_or_wrong_artifact_fails_closed(self):
        for fixture in ({}, {**report([]), "ArtifactType": "filesystem"},
                        {**report([]), "Results": []},
                        {**report([]), "Results": [{"Class": "lang-pkgs"}]},
                        report({}),
                        report([{"Severity": "HIGH"}])):
            with self.subTest(fixture=fixture), self.assertRaises(ValueError):
                image_security.inspect_report(fixture)

    def test_complete_scan_without_findings_passes(self):
        self.assertEqual(image_security.inspect_report(report([]), strict=True)["blocked"], 0)


if __name__ == "__main__":
    unittest.main()
