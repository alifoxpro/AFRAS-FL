"""Fast synthetic tests; no CICIoT2023 or DIAD2024 downloads required."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "data" / "split_records_leakfree.py"
spec = importlib.util.spec_from_file_location("afras_split", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def write_input(path, n=250, groups=False, unsorted_time=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=["feature1", "severity", "device", "event_time"])
        wr.writeheader()
        for i in range(n):
            wr.writerow({"feature1": str(i),
                         "severity": ("High", "Medium", "Low")[i % 3],
                         "device": "shared" if groups else f"device_{i}",
                         "event_time": str(i if not (unsorted_time and i == 7) else -1)})


class StrictSplitTests(unittest.TestCase):
    def test_ranges_do_not_overlap_and_have_embargo(self):
        ranges = mod.ordered_ranges(250, 20)
        self.assertEqual(ranges["train"][1] + 19, ranges["val"][0])
        self.assertEqual(ranges["val"][1] + 19, ranges["test"][0])
        self.assertEqual(sum(b - a for a, b in ranges.values()), 250 - 38)

    def test_end_to_end_manifest_and_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "raw" / "ciciot2023" / "Link_1_Core.csv"
            write_input(src)
            out = mod.split_dataset(src.parent, root / "splits", "ciciot2023",
                                    group_column="device", time_column="event_time")
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertTrue(manifest["group_disjoint_verified"])
            ids = []
            for part in ("train", "val", "test"):
                csv_path = out / part / src.name
                with csv_path.open(newline="") as f:
                    rows = list(csv.DictReader(f))
                self.assertEqual(mod.digest_file(csv_path),
                                 manifest["links"]["Link_1_Core"]["partitions"][part]["sha256"])
                ids.extend(int(row["__afras_source_row_id"]) for row in rows)
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(len(ids), 250 - 38)
            with self.assertRaises(FileExistsError):
                mod.split_dataset(src.parent, root / "splits", "ciciot2023")

    def test_reject_group_crossing_partitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "raw" / "Link_1_Core.csv"
            write_input(src, groups=True)
            with self.assertRaisesRegex(ValueError, "crosses"):
                mod.split_dataset(src.parent, root / "splits", "ciciot2023",
                                  group_column="device")
            self.assertFalse((root / "splits" / "ciciot2023").exists())

    def test_reject_unsorted_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "raw" / "Link_1_Core.csv"
            write_input(src, unsorted_time=True)
            with self.assertRaisesRegex(ValueError, "nondecreasing"):
                mod.split_dataset(src.parent, root / "splits", "ciciot2023",
                                  time_column="event_time")

    def test_groups_cannot_cross_partitions_across_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "raw" / "Link_1_Core.csv"
            second = root / "raw" / "Link_2_Core.csv"
            write_input(first)
            write_input(second)
            # Link 1 / row 0: device_0 is in TRAIN.
            # Link 2 / row 190: device_0 is in VAL, but each link alone
            # looks group-disjoint. The GLOBAL across-link guard must fail.
            with second.open(newline="") as fh:
                reader = csv.DictReader(fh)
                columns, data = reader.fieldnames, list(reader)
            data[190]["device"] = "device_0"
            with second.open("w", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=columns)
                writer.writeheader()
                writer.writerows(data)
            with self.assertRaisesRegex(ValueError, "crosses"):
                mod.split_dataset(first.parent, root / "splits", "ciciot2023",
                                  group_column="device")
            self.assertFalse((root / "splits" / "ciciot2023").exists())

    def test_reject_too_short(self):
        with self.assertRaises(ValueError):
            mod.ordered_ranges(70, 20)


if __name__ == "__main__":
    unittest.main()
