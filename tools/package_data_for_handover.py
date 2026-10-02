"""Package the client data for private handover to the invitation address.

Why this exists
---------------
The brief says two things that must both be honoured:

    "On Kestrel's data: This is client data. Do not publish it. Use a private
     repository (share access with the address in your invitation) or send a zip.
     A public repository containing the data files is recorded against the submission."

    "Please upload your Github Repo URL (Public)"

So: the GitHub repo is PUBLIC and carries code, the trained model and predictions.csv. The data
travels separately, privately. This script builds that private bundle. It is the "or send a zip"
path from the brief, and it also works if you would rather share a private repo -- the manifest it
prints tells the recipient exactly what they got and what its checksum is.

Safety rules this enforces
--------------------------
1. **Dry run by default.** Nothing is written unless you pass --write. The script prints the manifest
   so you can see what would go in before anything lands on disk.
2. **Refuses to write inside the repository.** The zip is customer data; if it ever ended up in the
   repo, `git add .` would stage it. The output path must be outside the repo root.
3. **Refuses to include anything on the blocklist** -- no .env, no .venv, no .git, no model internals
   beyond the one model file, no logs that might carry secrets.
4. **Never includes the audit outputs that quote customer text** in the *public* path. This zip IS the
   private path, so audit.txt and the error CSVs are included here deliberately -- the recipient is the
   client, who owns that text.

Usage
-----
    .venv/Scripts/python.exe tools/package_data_for_handover.py                # dry run
    .venv/Scripts/python.exe tools/package_data_for_handover.py --write        # write the zip
    .venv/Scripts/python.exe tools/package_data_for_handover.py --write --out ../kestrel-data.zip

After sending: confirm the recipient's address is the one in the invitation, send over an
invitation-scoped channel, and ask them to delete the bundle once they have extracted it.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "input"
ART = ROOT / "artifacts"

# What goes in. The data pack, plus the artifacts that let the recipient reproduce and audit.
INCLUDE_FILES = [
    DATA / "train.csv",
    DATA / "test_unlabelled.csv",
    DATA / "resolution_log.csv",
    DATA / "teams.csv",
    DATA / "sample_submission.csv",
    DATA / "ops-policy.pdf",
    DATA / "README.md",
    ART / "metrics.json",
    ART / "predictions.csv",
    ART / "audit.txt",
    ART / "errors_holdout.csv",
    ART / "errors_holdout_labelled.csv",
    ART / "confusion_holdout.csv",
    ART / "form_values.json",
]

# Never, under any circumstance.
BLOCK_PATTERNS = (".env", ".venv", ".git/", "__pycache__", "id_rsa", ".pem", ".key", "secrets")

# The model is a build output, not client data, so it stays in the PUBLIC repo. Not duplicated here.
PUBLIC_REPO_ALREADY_HAS = [ART / "model.joblib"]


def blocked(rel: Path) -> bool:
    s = rel.as_posix()
    return any(p in s for p in BLOCK_PATTERNS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="actually create the zip (default: dry run)")
    ap.add_argument("--out", default=None, help="output path; must be OUTSIDE the repository")
    args = ap.parse_args()

    present, missing = [], []
    for f in INCLUDE_FILES:
        (present if f.exists() else missing).append(f)

    # ASCII only: this prints to a Windows console that may not be UTF-8, and an em-dash
    # renders as a replacement character there. The pack is a client-facing artefact.
    print("=" * 74)
    print("PRIVATE HANDOVER BUNDLE - Kestrel Home client data")
    print("=" * 74)
    print("\nThis contains CUSTOMER DATA. Send it only to the address in your invitation,")
    print("over an invitation-scoped channel. Never attach it to a public repository.\n")

    print(f"would include ({len(present)} files):")
    total = 0
    for f in present:
        size = f.stat().st_size
        total += size
        print(f"   {size:>12,}  {f.relative_to(ROOT)}")
    print(f"   {'':>12}  {'-' * 44}")
    print(f"   {total:>12,}  total ({total / 1_048_576:.1f} MB)")

    if missing:
        print(f"\nnot found, skipped ({len(missing)}):")
        for f in missing:
            print(f"   {f.relative_to(ROOT)}")

    print("\npublic repo already carries these, so they are not duplicated here:")
    for f in PUBLIC_REPO_ALREADY_HAS:
        mark = "present" if f.exists() else "MISSING"
        print(f"   {f.relative_to(ROOT)}  [{mark}]")

    bad = [f for f in present if blocked(f)]
    if bad:
        print("\nREFUSING: these match the blocklist:")
        for f in bad:
            print(f"   {f}")
        return 2

    if not args.write:
        print("\nDRY RUN. Nothing written. Re-run with --write to create the bundle.")
        return 0

    out = Path(args.out).expanduser() if args.out else ROOT.parent / "kestrel-private-data.zip"
    out = out.resolve()
    if ROOT == out or ROOT in out.parents:
        print(f"\nREFUSING: {out} is inside the repository. Customer data must never sit in the")
        print("           repo tree, even transiently -- a later `git add .` would stage it.")
        print("           Choose a path outside the project folder.")
        return 2

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in present:
            z.write(f, arcname=str(Path("kestrel") / f.relative_to(ROOT)))

    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"\nWROTE  {out}  ({out.stat().st_size:,} bytes)")
    print(f"sha256 {digest}")
    print("\nGive the recipient the checksum so they can confirm it arrived intact, and ask them")
    print("to delete the bundle once extracted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())