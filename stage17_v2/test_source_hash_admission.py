"""Stage-17 V2 local archive SHA admission checks (synthetic bytes only).

Tests assert that all eight source archive byte streams are verified and the
held-out archive is never opened, even though its identity is in the manifest.
This is NOT official UCI byte provenance or a native ZIP/RAR decode test.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import source_only_pilot as m


class SourceHashAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="afras_v2_source_sha_")
        self.root = Path(self.temp.name)
        self.heldout = m.DEVICES[0]
        self.sources = list(m.DEVICES[1:])
        self.records = []
        for device in m.DEVICES:
            data = ("synthetic-source-" + device).encode("utf8")
            if device != self.heldout:
                (self.root / (device + ".zip")).write_bytes(data)
            self.records.append({
                "device": device,
                "filename": device + ".zip",
                "local_sha256": hashlib.sha256(data).hexdigest(),
            })
        self.manifest = self.root / "local_manifest.json"
        self._save_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def _save_manifest(self):
        self.manifest.write_text(
            json.dumps({"local_archives": self.records}),
            encoding="utf8"
        )

    def test_eight_source_hashes_pass_with_target_archive_absent(self):
        result = m.verify_source_archive_hashes(
            self.root, self.manifest, self.sources, self.heldout
        )
        self.assertEqual(len(result), 8)
        self.assertNotIn(self.heldout, result)
        self.assertFalse((self.root / (self.heldout + ".zip")).exists())

    def test_mutated_source_bytes_fail(self):
        device = self.sources[3]
        with (self.root / (device + ".zip")).open("ab") as f:
            f.write(b"mutated")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            m.verify_source_archive_hashes(
                self.root, self.manifest, self.sources, self.heldout
            )

    def test_target_in_source_list_fails_before_open(self):
        wrong = [self.heldout, *self.sources[:-1]]
        with self.assertRaisesRegex(ValueError, "exclude exactly one"):
            m.verify_source_archive_hashes(
                self.root, self.manifest, wrong, self.heldout
            )

    def test_manifest_duplicate_device_rejected(self):
        self.records[1]["device"] = self.records[0]["device"]
        self._save_manifest()
        with self.assertRaisesRegex(ValueError, "Unknown/duplicate"):
            m.verify_source_archive_hashes(
                self.root, self.manifest, self.sources, self.heldout
            )

    def test_manifest_source_filename_rejected(self):
        self.records[1]["filename"] = "../escape.zip"
        self._save_manifest()
        with self.assertRaisesRegex(ValueError, "Unexpected device archive filename"):
            m.verify_source_archive_hashes(
                self.root, self.manifest, self.sources, self.heldout
            )


if __name__ == "__main__":
    unittest.main()
