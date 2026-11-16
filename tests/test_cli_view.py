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


class ViewerDevTests(unittest.TestCase):
    def _run(
        self,
        *,
        dev: bool,
        previous: str | None = None,
    ) -> tuple[dict[str, bool], dict[str, object]]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            assets.mkdir()
            discovery = _discovery_path(root)
            if previous is not None:
                _write_discovery(discovery, previous)
            seen: dict[str, bool] = {}

            class FakeServer:
                server_port = 8123

                def __init__(self, address: object, handler: object) -> None:
                    pass

                def serve_forever(self) -> None:
                    seen["discovery"] = discovery.exists()
                    raise KeyboardInterrupt

                def server_close(self) -> None:
                    pass

            arguments = Namespace(
                embed=False,
                dev=dev,
                host="127.0.0.1",
                port=0,
                snapshot=None,
                title=None,
                no_open=True,
            )
            with (
                patch(
                    "kg_build_system.cli.service._private.view._assets",
                    return_value=assets,
                ),
                patch(
                    "kg_build_system.cli.service._private.view._snapshot",
                    return_value=(b"{}", "application/json"),
                ),
                patch(
                    "kg_build_system.cli.service._private.view.ViewerServer",
                    FakeServer,
                ),
                patch(
                    "kg_build_system.cli.service._private.view._discovery_path",
                    return_value=discovery,
                ),
            ):
                self.assertEqual(run_view(arguments), 0)

            final: dict[str, object] = {"exists": discovery.exists()}
            if discovery.exists():
                final["text"] = discovery.read_text()
                final["mode"] = discovery.stat().st_mode & 0o777
            return seen, final

    def test_dev_publishes_the_discovery_file_while_serving(self) -> None:
        seen, final = self._run(dev=True)
        self.assertTrue(seen["discovery"])
        self.assertFalse(final["exists"])

    def test_dev_restores_a_previous_discovery_file(self) -> None:
        seen, final = self._run(
            dev=True,
            previous="http://127.0.0.1:9999",
        )
        self.assertTrue(seen["discovery"])
        self.assertTrue(final["exists"])
        self.assertEqual(
            json.loads(str(final["text"])),
            {"api": "http://127.0.0.1:9999"},
        )
        self.assertEqual(final["mode"], 0o600)

    def test_the_default_serves_without_a_discovery_file(self) -> None:
        seen, final = self._run(dev=False)
        self.assertFalse(seen["discovery"])
        self.assertFalse(final["exists"])


class ViewerEmbedTests(unittest.TestCase):
    def test_run_view_embed_serves_the_bundled_viewer(self) -> None:
        arguments = Namespace(
            embed=True,
            dev=False,
            host="127.0.0.1",
            port=8001,
            snapshot=None,
            title=None,
            no_open=True,
        )
        with patch(
            "kg_build_system.cli.service._private.view._serve_embedded_viewer",
            return_value=0,
        ) as serve:
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
