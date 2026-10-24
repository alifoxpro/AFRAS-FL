#!/usr/bin/env python3
"""One-time Stage-13 Ennio publisher-download member-byte reconciliation.

Permitted science use: check public-source provenance BEFORE freezing the test
protocol; this does not compute Ennio labels, fingerprints or classifier metrics.
Input archive is downloaded directly from public UCI with transport SHA checked.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

EXPECTED = {
    "Ennio_Doorbell/benign_traffic.csv": {
        "bytes": 37135498,
        "local_sha256": "75cc608d3196950ad1cb14fc050babb96098128106b55ed84226e3ea97dba821"
    },
    "Ennio_Doorbell/gafgyt_attacks.rar": {
        "bytes": 52525066,
        "local_sha256": "2ded0dca827f13a921bf5b36f3b257ed65c83d60095cc7c78ecdbcf343f2b7ba"
    }
}
KNOWN_ORIGINAL_UCI_OUTER_SHA256 = "64929678b081d8e579a8d7c488cf11cc588403f282d5fb065b4156edbd55de9b"

def digest_file(path):
    d = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            d.update(block)
    return d.hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original-uci-archive",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    if args.output.exists():
        raise FileExistsError("Never overwrite evidence")
    archive_sha=digest_file(args.original_uci_archive)
    if archive_sha!=KNOWN_ORIGINAL_UCI_OUTER_SHA256:
        raise ValueError("Public UCI transport checksum differs from earlier independent runs")
    comparisons=[]
    with zipfile.ZipFile(args.original_uci_archive) as archive:
        names=[a.filename for a in archive.infolist() if not a.is_dir()]
        for rel,expected in EXPECTED.items():
            matching=[n for n in names if n==rel or n.endswith("/"+rel)]
            if len(matching)!=1:
                raise ValueError("Expected exactly one Ennio source member: "+rel)
            h=hashlib.sha256()
            observed=0
            with archive.open(matching[0]) as source:
                for data in iter(lambda:source.read(1024*1024),b""):
                    observed+=len(data)
                    h.update(data)
            sha=h.hexdigest()
            equal=(sha==expected["local_sha256"] and
                   observed==expected["bytes"])
            comparisons.append({
                "relative_member_path":rel,
                "public_uci_member_path":matching[0],
                "public_uci_member_bytes":observed,
                "public_uci_member_sha256":sha,
                "independent_user_library_member_sha256":expected["local_sha256"],
                "independent_user_library_member_bytes":expected["bytes"],
                "exact_source_member_match":equal,
            })
            print("ENNNIO_OFFICIAL_SOURCE_MEMBER",rel,"MATCH" if equal else "MISMATCH",sha,flush=True)
    result={
       "audit":"STAGE13_PUBLIC_UCI_ENNIO_EXACT_MEMBER_BYTE_RECONCILIATION",
       "public_archive_outer_sha256":archive_sha,
       "source_url":"https://archive.ics.uci.edu/static/public/442/detection+of+iot+botnet+attacks+n+baiot.zip",
       "comparisons":comparisons,
       "matched":sum(row["exact_source_member_match"] for row in comparisons),
       "expected":len(EXPECTED),
       "all_members_match":all(row["exact_source_member_match"] for row in comparisons),
       "disclaimer":"Authenticates local member content against the publicly hosted archive bytes; does not independently verify event-level ground truth, deduced feature recurrence, or held-out model accuracy."
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x") as fd:
        json.dump(result,fd,indent=2,allow_nan=False)
    if not result["all_members_match"]:
        raise ValueError("Ennio content mismatch")
    print("STAGE13_ENNIO_PUBLIC_BYTE_GATE_PASS",flush=True)

if __name__=="__main__":
    main()
