from __future__ import annotations

import gzip
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from kg_build_system.cli.service._private.view import (
    ViewerHandler,
    ViewerServer,
    _api_url,
    _discovery_path,
    _remove_discovery,
    _snapshot,
    _viewer_command,
    _viewer_environment,
    _viewer_source,
    _write_discovery,
    run_view,
)


class ViewerSnapshotTests(unittest.TestCase):
    def test_a_bare_workflow_plan_is_wrapped_with_a_title(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow_plan.json"
            path.write_text(
                json.dumps(
                    {
                        "components": [],
                        "steps": [],
                        "connections": [],
                        "provenance": {"blueprint": {}},
                    }
                )
            )
            body, content_type = _snapshot(path, "estate")
        document = json.loads(body)
        self.assertEqual(content_type, "application/json")
        self.assertEqual(document["format"], "kg-viewer-snapshot")
        self.assertEqual(document["title"], "estate")
        self.assertIn("workflow", document)

    def test_a_gzip_plan_is_decompressed_before_wrapping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow_plan.json.gz"
            path.write_bytes(
                gzip.compress(
                    json.dumps(
                        {
                            "components": [],
                            "steps": [],
                            "connections": [],
                        }
                    ).encode()
                )
            )
            body, _ = _snapshot(path, "estate")
        self.assertEqual(json.loads(body)["format"], "kg-viewer-snapshot")

    def test_a_viewer_snapshot_is_served_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text(
                json.dumps(
                    {
                        "format": "kg-viewer-snapshot",
                        "version": 1,
                        "name": "kept",
                        "title": "Kept",
                        "workflow": {
                            "components": [],
                            "steps": [],
                            "connections": [],
                        },
                    }
                )
            )
            body, _ = _snapshot(path, "ignored")
        document = json.loads(body)
        self.assertEqual(document["name"], "kept")
        self.assertEqual(document["title"], "Kept")

    def test_missing_snapshot_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            _snapshot(Path("/no/such/snapshot.json"), None)


class ViewerDiscoveryTests(unittest.TestCase):
    def test_the_discovery_file_is_the_minimal_api_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = _discovery_path(root)
            _write_discovery(path, "http://127.0.0.1:8001")
            self.assertEqual(
                json.loads(path.read_text()),
                {"api": "http://127.0.0.1:8001"},
            )
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            _remove_discovery(path)
            self.assertFalse(path.exists())

    def test_a_wildcard_bind_publishes_loopback(self) -> None:
        self.assertEqual(_api_url("0.0.0.0", 8001), "http://127.0.0.1:8001")
        self.assertEqual(_api_url("127.0.0.1", 8001), "http://127.0.0.1:8001")

    def test_the_source_viewer_is_detected(self) -> None:
        self.assertIsNotNone(_viewer_source())


class ViewerCommandTests(unittest.TestCase):
    def test_the_source_viewer_uses_the_requested_port(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            binary = source / "node_modules" / ".bin" / "next"
            binary.parent.mkdir(parents=True)
            binary.write_text("")
            with (
                patch(
                    "kg_build_system.cli.service._private.view._viewer_source",
                    return_value=source,
                ),
                patch(
                    "kg_build_system.cli.service._private.view.shutil.which",
                    return_value="/usr/bin/npm",
                ),
            ):
                command = _viewer_command(8123, "127.0.0.1")
        self.assertEqual(
            command,
            [
                "/usr/bin/npm",
                "run",
                "dev",
                "--",
                "--port",
                "8123",
                "--hostname",
                "127.0.0.1",
            ],
        )

    def test_the_viewer_environment_publishes_an_absolute_discovery_path(self) -> None:
        discovery = Path("/tmp/example/.kbs/viewer.json")
        environment = _viewer_environment(discovery)
        self.assertEqual(
            environment["KBS_DISCOVERY"],
            str(discovery.resolve()),
        )
        self.assertEqual(environment["NEXT_TELEMETRY_DISABLED"], "1")


class ViewerEmbedTests(unittest.TestCase):
    def test_run_view_embed_serves_the_empty_viewer(self) -> None:
        arguments = Namespace(
            embed=True,
            host="127.0.0.1",
            port=8001,
            snapshot=None,
            title=None,
        )
        with (
            patch(
                "kg_build_system.cli.service._private.view._viewer_source",
                return_value=None,
            ),
            patch(
                "kg_build_system.cli.service._private.view._serve_embedded_static_viewer",
                return_value=0,
            ) as serve,
        ):
            self.assertEqual(run_view(arguments), 0)
        serve.assert_called_once_with(arguments)


class ViewerServerTests(unittest.TestCase):
    def test_the_server_serves_the_index_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            assets = Path(directory)
            (assets / "index.html").write_text("viewer")
            server = ViewerServer(("127.0.0.1", 0), ViewerHandler)
            server.assets = assets
            server.snapshot_bytes = b'{"format":"kg-viewer-snapshot"}'
            server.snapshot_type = "application/json"
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                with urllib.request.urlopen(f"{base}/") as response:
                    self.assertEqual(response.read(), b"viewer")
                with urllib.request.urlopen(f"{base}/snapshot") as response:
                    self.assertEqual(
                        response.read(), b'{"format":"kg-viewer-snapshot"}'
                    )
                    self.assertEqual(
                        response.headers["Content-Type"], "application/json"
                    )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_an_embedded_server_does_not_serve_a_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            assets = Path(directory)
            (assets / "index.html").write_text("viewer")
            server = ViewerServer(("127.0.0.1", 0), ViewerHandler)
            server.assets = assets
            server.snapshot_bytes = b""
            server.snapshot_type = "application/json"
            server.embed = True
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                with self.assertRaises(urllib.error.HTTPError) as missing:
                    urllib.request.urlopen(f"{base}/snapshot")
                self.assertEqual(missing.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
