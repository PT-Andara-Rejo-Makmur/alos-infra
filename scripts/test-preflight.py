"""Preflight must enforce the configuration Compose actually uses, before any deployment."""

import importlib.util
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("preflight", Path(__file__).with_name("preflight-check.py"))
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PreflightTest(unittest.TestCase):
    def test_optional_infrastructure_image_override_cannot_be_mutable(self):
        fixture = {"ALOS_WEB_IMAGE": "r/web@sha256:" + "1" * 64,
                   "ALOS_BACKEND_IMAGE": "r/backend@sha256:" + "2" * 64,
                   "GENESIS_IMAGE": "r/genesis@sha256:" + "3" * 64,
                   "POSTGRES_IMAGE": "r/data@sha256:" + "4" * 64,
                   "WEB_HOSTNAME": "web.example.invalid", "API_HOSTNAME": "api.example.invalid",
                   "POSTGRES_DB": "fixture", "POSTGRES_USER": "fixture", "POSTGRES_PASSWORD": "fixture",
                   "GENESIS_INTERNAL_TOKEN": "fixture"}
        for key in ("CADDY_IMAGE", "OTEL_COLLECTOR_IMAGE"):
            errors = []
            preflight.validate_staging({**fixture, key: "image:latest"}, errors)
            self.assertTrue(any(key in error for error in errors))
        errors = []
        preflight.validate_staging(fixture, errors)
        self.assertEqual(errors, [])

    def test_database_release_requires_explicit_digest(self):
        valid = {"POSTGRES_DB": "fixture", "POSTGRES_USER": "fixture", "POSTGRES_PASSWORD": "fixture",
                 "POSTGRES_BIND_IP": "10.1.1.3", "POSTGRES_IMAGE": "registry.example/alos-postgres@sha256:" + "4" * 64}
        for value in (None, "", "pgvector/pgvector:pg16", valid["POSTGRES_IMAGE"]):
            errors = []
            fixture = {**valid, "POSTGRES_IMAGE": value}
            preflight.validate_data(fixture, errors)
            self.assertEqual(bool(errors), value != valid["POSTGRES_IMAGE"])

    def test_model_route_requires_secure_configured_transport(self):
        valid = {"DEFAULT_MODEL_ROUTE": "nine_router", "NINE_ROUTER_BASE_URL": "https://router.example/v1",
                 "NINE_ROUTER_API_KEY": "secret-fixture", "NINE_ROUTER_MODEL_DEFAULT": "model-fixture"}
        errors = []
        preflight.validate_model_router(valid, errors)
        self.assertEqual(errors, [])
        for override in ({"NINE_ROUTER_BASE_URL": "http://203.0.113.10/v1"},
                         {"NINE_ROUTER_BASE_URL": "https://user:secret-fixture@router.example/v1"},
                         {"NINE_ROUTER_API_KEY": ""}, {"NINE_ROUTER_MODEL_DEFAULT": ""}):
            errors = []
            preflight.validate_model_router({**valid, **override}, errors)
            self.assertTrue(errors)
            self.assertNotIn("secret-fixture", " ".join(errors))

    def test_only_complete_digest_is_immutable(self):
        for invalid in ("image:latest", "image:v1.2.3", "image@sha256:", "image@sha256:abc",
                        "image@sha256:" + "x" * 64, "image@sha256:" + "a" * 64 + ":tag"):
            with self.subTest(image=invalid):
                errors = []
                preflight.validate_image_immutability(invalid, "web", errors)
                self.assertTrue(errors)
        errors = []
        preflight.validate_image_immutability("registry.example/image:v1.2.3@sha256:" + "a" * 64,
                                              "web", errors)
        self.assertEqual(errors, [])

    def test_environment_precedes_file_including_empty_values(self):
        with patch.dict(os.environ, {"BIND": "10.1.1.2", "SECRET": ""}, clear=True):
            self.assertEqual(preflight.get_effective_env({"BIND": "127.0.0.1", "SECRET": "file",
                                                         "DEFAULT": "value"}),
                             {"BIND": "10.1.1.2", "SECRET": "", "DEFAULT": "value"})

    def test_explicit_production_file_participates_in_isolation(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.env"
            path.write_text("APP_PRIVATE_BIND_IP=10.1.1.2\n")
            with patch("sys.argv", ["preflight", "--target", "app", "--env-file", str(path),
                                    "--staging-env-file", str(path)]), \
                 patch.object(preflight, "validate_app"), \
                 patch.object(preflight, "validate_cross_environment_isolation", wraps=preflight.validate_cross_environment_isolation) as check:
                self.assertEqual(preflight.main(), 1)
                check.assert_called_once_with(path, path, unittest.mock.ANY)

    def test_rollback_requires_digest(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.env"
            path.write_text("APP_PRIVATE_BIND_IP=10.1.1.2\n")
            for image, expected in (("image:v1.2.3", 1), ("image@sha256:" + "a" * 64, 0)):
                with patch("sys.argv", ["preflight", "--target", "app", "--env-file", str(path),
                                        "--require-rollback-ref"]), \
                     patch.dict(os.environ, {"PREVIOUS_KNOWN_GOOD_IMAGE": image}), \
                     patch.object(preflight, "validate_app"):
                    self.assertEqual(preflight.main(), expected)


if __name__ == "__main__":
    unittest.main()
