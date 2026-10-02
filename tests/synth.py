"""Synthetic data for TESTS ONLY. It never touches data/input. Same columns as the real pack, trivial text."""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

TEAMS = ["Technical Support", "Installation", "Billing", "Returns & Refunds", "Escalations",
         "Consumables & Spares", "Warranty & Shield"]
OLD = {"Consumables & Spares": "Spares Desk", "Warranty & Shield": "Shield Desk"}
PRODS = ["air fryer", "mixer-grinder", "water purifier", "robot vacuum", "cooktop", "fan", "heater"]
T = {
    "Technical Support": ["{p} is not working, stopped suddenly", "{p} making loud noise and leaking", "{p} breakdown please send technician"],
    "Installation": ["need installation of my {p}", "installation not done yet nobody came", "demo and installation booking for {p}"],
    "Billing": ["refund for wrong charge on invoice", "invoice copy needed for {p}", "payment deducted twice for {p}"],
    "Returns & Refunds": ["want to return my {p} wrong item", "cancel order and refund {p}"],
    "Escalations": ["third time calling escalate to manager {p}", "consumer court notice about {p}"],
    "Consumables & Spares": ["need filter replacement for {p}", "order spare jar lid for {p}", "where to buy spare parts for {p}"],
    "Warranty & Shield": ["how to claim Shield plan for {p}", "is my {p} still under warranty", "extend warranty on {p}"],
}


def make_frames(n: int = 1200, n_test: int = 150, seed: int = 0) -> dict:
    rng, nrng = random.Random(seed), np.random.default_rng(seed)
    start, end = pd.Timestamp("2025-03-01"), pd.Timestamp("2026-08-31")
    rows, res = [], []
    tot = n + n_test
    for i in range(tot):
        ts = start + (end - start) * (i / tot)
        src = "legacy_zoho" if ts < pd.Timestamp("2025-10-01") else "crm"
        r = rng.random()
        if r < 0.10:
            final = rng.choice(["Installation", "Technical Support"]); bot = "Billing"
            txt = f"I paid for {'installation' if final == 'Installation' else 'repair'} of my {{p}} but nothing happened"
        elif r < 0.15:
            final = rng.choice(["Technical Support", "Consumables & Spares", "Warranty & Shield"]); bot = "Consumables & Spares"
            txt = "please call me about my {p}"
        else:
            final = rng.choice(TEAMS); txt = rng.choice(T[final]); bot = final if rng.random() < 0.85 else rng.choice(TEAMS)
        p = rng.choice(PRODS)
        txt = txt.format(p=p) + " \u2014 thanks"
        if src == "legacy_zoho":
            txt = txt.encode("utf-8").decode("latin-1")
        ren = ts >= pd.Timestamp("2025-12-01")
        nm = lambda t: t if ren or t not in OLD else OLD[t]
        row = dict(request_id=f"SR{i:06d}", created_at_ist=str(ts), channel=rng.choice(["ivr", "chat", "whatsapp", "email"]),
                   product_family=p, warranty_status=rng.choice(["in_warranty", "shield", "out_of_warranty"]),
                   request_text=txt, source=src)
        if i < n:
            rows.append({**row, "team_label": nm(bot)})
            closed = i < n - int(0.03 * n)
            res.append(dict(request_id=row["request_id"], first_team=nm(bot), final_team=nm(final) if closed else "",
                            transfers=int(bot != final) if closed else "",
                            resolved_at=str(ts + pd.Timedelta(hours=float(nrng.integers(2, 90)))) if closed else ""))
        else:
            rows.append(row)
    df = pd.DataFrame(rows)
    test = df.iloc[n:].drop(columns=["team_label"], errors="ignore").reset_index(drop=True)
    teams = [dict(team=t if t not in OLD else OLD[t], renamed_to=t if t in OLD else "", handles=t) for t in TEAMS]
    return {"train": df.iloc[:n].reset_index(drop=True), "test": test, "resolution": pd.DataFrame(res),
            "teams": pd.DataFrame(teams), "sample_submission": pd.DataFrame({"request_id": test.request_id, "team": TEAMS[0]})}


FILENAMES = {"train": "train", "test": "test_unlabelled", "resolution": "resolution_log", "teams": "teams",
             "sample_submission": "sample_submission"}


def write_dir(folder: Path, frames: dict, fmt: str = "xlsx") -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for role, df in frames.items():
        path = folder / f"{FILENAMES[role]}.{fmt}"
        if fmt == "xlsx":
            df.to_excel(path, index=False)
        else:
            df.to_csv(path, index=False)
