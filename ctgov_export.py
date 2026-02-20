"""
ctgov_export.py — Download ClinicalTrials.gov AllPublicXML, extract a subset,
and optionally export to CSV.

Usage:
    python ctgov_export.py [options]

Options:
    --workdir DIR       Working directory (default: ctgov_all)
    --nct-ids FILE      File with one NCT ID per line (optional subset filter)
    --out-csv FILE      Output CSV file (default: subset.csv); triggers parse
    --skip-download     Skip download if AllPublicXML.zip already exists
    --skip-unzip        Skip unzip if xml/ directory already exists
"""

import argparse
import csv
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def _reporthook(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(downloaded * 100 / total_size, 100)
        mb = downloaded / 1_048_576
        total_mb = total_size / 1_048_576
        print(f"\r  {pct:5.1f}%  {mb:.1f} / {total_mb:.1f} MB", end="", flush=True)
    else:
        mb = downloaded / 1_048_576
        print(f"\r  {mb:.1f} MB downloaded", end="", flush=True)


def download(url: str, dest: str, skip: bool) -> None:
    if skip and os.path.exists(dest):
        print(f"==> Skipping download, found: {dest}")
        return
    print(f"==> Downloading {url}")
    # Resume support via Range header
    headers = {}
    existing = os.path.getsize(dest) if os.path.exists(dest) else 0
    if existing:
        headers["Range"] = f"bytes={existing}-"
        print(f"    Resuming from {existing / 1_048_576:.1f} MB")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp, open(dest, "ab") as f:
            total = int(resp.headers.get("Content-Length", 0)) + existing
            block = 1024 * 64
            block_num = existing // block
            while True:
                chunk = resp.read(block)
                if not chunk:
                    break
                f.write(chunk)
                block_num += 1
                _reporthook(block_num, block, total)
    except Exception as e:
        print(f"\n  Download error: {e}", file=sys.stderr)
        raise
    print()  # newline after progress


# ---------------------------------------------------------------------------
# Unzip
# ---------------------------------------------------------------------------

def unzip(zip_path: str, out_dir: str, skip: bool) -> None:
    if skip and os.path.isdir(out_dir) and os.listdir(out_dir):
        print(f"==> Skipping unzip, found: {out_dir}/")
        return
    os.makedirs(out_dir, exist_ok=True)
    print(f"==> Unzipping {zip_path} → {out_dir}/")
    with zipfile.ZipFile(zip_path) as zf:
        members = zf.namelist()
        total = len(members)
        for i, name in enumerate(members, 1):
            # Strip leading directory from zip paths like NCT0123xxxx/NCT01234567.xml
            parts = name.split("/")
            out_name = parts[-1] if parts[-1] else None
            if not out_name or not out_name.lower().endswith(".xml"):
                continue
            target = os.path.join(out_dir, out_name)
            with zf.open(name) as src, open(target, "wb") as dst:
                dst.write(src.read())
            if i % 10_000 == 0 or i == total:
                print(f"  {i}/{total} files extracted", end="\r", flush=True)
    print()
    print(f"==> Unzip complete: {out_dir}/")


# ---------------------------------------------------------------------------
# Subset extraction
# ---------------------------------------------------------------------------

def load_nct_ids(path: str) -> list[str]:
    ids = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            nct_id = line.strip().split(",")[0].strip().upper()
            if nct_id:
                ids.append(nct_id)
    return ids


def extract_subset(xml_dir: str, subset_dir: str, nct_ids: list[str]) -> list[str]:
    import shutil
    os.makedirs(subset_dir, exist_ok=True)
    found, missing = [], []
    for nct_id in nct_ids:
        src = os.path.join(xml_dir, f"{nct_id}.xml")
        if os.path.exists(src):
            shutil.copy2(src, subset_dir)
            found.append(nct_id)
        else:
            missing.append(nct_id)
    if missing:
        print(f"  WARNING: {len(missing)} NCT IDs not found: {missing[:10]}")
    print(f"==> Copied {len(found)} files to {subset_dir}/")
    return found


# ---------------------------------------------------------------------------
# XML parsing → CSV
# ---------------------------------------------------------------------------

def _text(root: ET.Element, path: str) -> str:
    el = root.find(path)
    return (el.text or "").strip() if el is not None and el.text else ""


def _first(root: ET.Element, *paths: str) -> str:
    for p in paths:
        v = _text(root, p)
        if v:
            return v
    return ""


def parse_xml(fp: str) -> dict:
    tree = ET.parse(fp)
    root = tree.getroot()
    nct_id = _first(root, "id_info/nct_id", "id_info/org_study_id")
    brief_title = _first(root, "brief_title", "official_title")
    overall_status = _text(root, "overall_status")
    study_type = _text(root, "study_type")
    phase = _text(root, "phase")
    enrollment = _first(root, "enrollment", "enrollment/textblock")
    start_date = _text(root, "start_date")
    primary_completion_date = _text(root, "primary_completion_date")
    completion_date = _text(root, "completion_date")
    sponsor = _text(root, "sponsors/lead_sponsor/agency")
    conditions = " | ".join(
        (c.text or "").strip() for c in root.findall("condition") if c.text
    )
    interventions = " | ".join(
        _text(itv, "intervention_name")
        for itv in root.findall("intervention")
        if _text(itv, "intervention_name")
    )
    has_results = "true" if root.find("clinical_results") is not None else "false"
    return {
        "nct_id": nct_id,
        "brief_title": brief_title,
        "overall_status": overall_status,
        "study_type": study_type,
        "phase": phase,
        "enrollment": enrollment,
        "start_date": start_date,
        "primary_completion_date": primary_completion_date,
        "completion_date": completion_date,
        "lead_sponsor": sponsor,
        "conditions": conditions,
        "interventions": interventions,
        "has_results": has_results,
        "source_file": os.path.basename(fp),
    }


COLS = [
    "nct_id", "brief_title", "overall_status", "study_type", "phase",
    "enrollment", "start_date", "primary_completion_date", "completion_date",
    "lead_sponsor", "conditions", "interventions", "has_results", "source_file",
]


def to_csv(src_dir: str, out_csv: str) -> None:
    files = sorted(
        os.path.join(src_dir, f)
        for f in os.listdir(src_dir)
        if f.lower().endswith(".xml")
    )
    total = len(files)
    print(f"==> Parsing {total} XML files → {out_csv}")
    rows = []
    errors = 0
    for i, fp in enumerate(files, 1):
        try:
            rows.append(parse_xml(fp))
        except Exception as e:
            print(f"  ERROR {os.path.basename(fp)}: {e}")
            errors += 1
        if i % 1000 == 0 or i == total:
            print(f"  {i}/{total} parsed", end="\r", flush=True)
    print()
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"==> Wrote {len(rows)} rows to {out_csv} ({errors} errors)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

URL = "https://clinicaltrials.gov/AllPublicXML.zip"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--workdir", default="ctgov_all", help="Working directory (default: ctgov_all)")
    p.add_argument("--nct-ids", metavar="FILE", help="File with one NCT ID per line (optional)")
    p.add_argument("--out-csv", metavar="FILE", help="Output CSV path (triggers parsing)")
    p.add_argument("--skip-download", action="store_true", help="Skip download if zip already exists")
    p.add_argument("--skip-unzip", action="store_true", help="Skip unzip if xml/ already populated")
    args = p.parse_args()

    workdir = args.workdir
    os.makedirs(workdir, exist_ok=True)

    zip_path = os.path.join(workdir, "AllPublicXML.zip")
    xml_dir = os.path.join(workdir, "xml")
    subset_dir = os.path.join(workdir, "subset")

    # 1. Download
    download(URL, zip_path, skip=args.skip_download)

    # 2. Unzip
    unzip(zip_path, xml_dir, skip=args.skip_unzip)

    # 3. Subset (if NCT ID list provided)
    parse_dir = xml_dir
    if args.nct_ids:
        nct_ids = load_nct_ids(args.nct_ids)
        print(f"==> Filtering {len(nct_ids)} NCT IDs")
        extract_subset(xml_dir, subset_dir, nct_ids)
        parse_dir = subset_dir

    # 4. CSV export (if requested)
    if args.out_csv:
        to_csv(parse_dir, args.out_csv)
    elif args.nct_ids:
        print(f"\nSubset XML files are in: {subset_dir}/")
        print("Run with --out-csv out.csv to also export to CSV.")
    else:
        print(f"\nAll XML files are in: {xml_dir}/")
        print("Use --nct-ids ids.txt to filter a subset.")
        print("Use --out-csv out.csv to export to CSV.")


if __name__ == "__main__":
    main()
