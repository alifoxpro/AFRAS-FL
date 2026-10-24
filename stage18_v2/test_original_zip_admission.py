"""Source-ZIP admission checks on nine miniature fixtures; no real target scored."""
import json
from pathlib import Path
import tempfile
import unittest

import replay_predictions as replay
import verify_original_nine_zip_bytes as verify


class OriginalNineZipByteAdmissionTests(unittest.TestCase):
    def make_sources(self, root):
        sources=root/"source_zips"
        sources.mkdir()
        entries=[]
        for idx,dev in enumerate(replay.DEVICES):
            path=sources/(dev+".zip")
            data=("test only source archive "+dev+" "+str(idx)).encode()
            path.write_bytes(data)
            entries.append({
                "device":dev,"filename":dev+".zip",
                "local_sha256":verify.sha256_file(path),
                "local_bytes":len(data),
            })
        manifest=root/"manifest.json"
        manifest.write_text(json.dumps({
            "manifest_schema":"AFRAS_V2_ORIGINAL_NINE_DEVICE_ZIP_EXPECTED_BYTES_V1",
            "local_archives":entries
        }))
        return sources,manifest

    def test_all_nine_synthetic_archive_digests_pass_without_decompression(self):
        with tempfile.TemporaryDirectory() as d:
            sources,manifest=self.make_sources(Path(d))
            output=verify.validate_original_source_manifest(sources,manifest)
            self.assertEqual(output["original_zips_verified"],9)
            self.assertEqual(output["human_scientific_approval_created"],False)
            self.assertEqual(output["heldout_model_predictions_generated"],False)
            self.assertEqual(output["member_decompression_performed"],False)

    def test_repackaged_public_source_bytes_are_not_mislabeled_local_original(self):
        with tempfile.TemporaryDirectory() as d:
            sources,manifest=self.make_sources(Path(d))
            data=json.loads(manifest.read_text())
            data["record_status"]="UNAPPROVED_PUBLISHER_UCI_NATIVE_MEMBERS_REPACKAGED_NINE_SOURCE_WRAPPERS"
            data["human_authorization_granted"]=False
            manifest.write_text(json.dumps(data))
            result=verify.validate_original_source_manifest(sources,manifest)
            self.assertEqual(result["original_zips_verified"],9)
            self.assertEqual(result["origin"],"PUBLISHER_UCI_REPACKAGED_NOT_USER_LIBRARY")
            self.assertIn("PUBLISHER_REPACKAGED",result["status"])
            self.assertIn("REPACKAGED",result["files"][0]["status"])
            self.assertIs(result["human_scientific_approval_created"],False)

    def test_one_modified_original_zip_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            sources,manifest=self.make_sources(Path(d))
            device=replay.DEVICES[-1]
            (sources/(device+".zip")).write_bytes(b"tampered original ZIP")
            with self.assertRaisesRegex(ValueError,"ZIP byte size differs|ZIP SHA-256 mismatch"):
                verify.validate_original_source_manifest(sources,manifest)

    def test_missing_original_zip_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            sources,manifest=self.make_sources(Path(d))
            (sources/(replay.DEVICES[0]+".zip")).unlink()
            with self.assertRaises(FileNotFoundError):
                verify.validate_original_source_manifest(sources,manifest)

    def test_noncanonical_nine_zip_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            sources,manifest=self.make_sources(Path(d))
            data=json.loads(manifest.read_text())
            data["local_archives"][0]["device"]="NOT_ORIGINAL_NBAIOT"
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"canonical devices"):
                verify.validate_original_source_manifest(sources,manifest)


if __name__=="__main__":
    unittest.main()
