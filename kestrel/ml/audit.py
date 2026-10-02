"""Data forensics report. Run it before trusting any number."""
from __future__ import annotations

import re

import pandas as pd

from ..data.loader import Dataset
from ..settings import Settings

MOJI = re.compile(r"â€|Ã.|Â|\ufffd", re.I)


def audit(settings: Settings, ds: Dataset) -> str:
    tr, te = ds.train, ds.test
    L = []
    P = lambda *a: L.append(" ".join(str(x) for x in a))
    P("files used:", ds.report.files_used)
    P("rows train/test:", len(tr), len(te) if te is not None else "no test file")
    P("canonical teams:", ds.canon)
    P("rename map:", ds.team_map)
    P("unparsed created_at train:", int(tr.ts.isna().sum()))
    P("date range train:", tr.ts.min(), "->", tr.ts.max())
    P("\nsource train:\n" + tr.source.value_counts().to_string())
    P("\nraw team_label values:\n" + tr.team_label.value_counts().to_string())
    P("\nfinal_team values:\n" + tr.final_team.value_counts(dropna=False).to_string())
    P("\nmojibake rate by source (raw text):\n" +
      tr.groupby("source").request_text.apply(lambda s: s.map(lambda x: bool(MOJI.search(x))).mean()).to_string())
    P("mojibake after cleaning:", float(tr.text.map(lambda x: bool(MOJI.search(x))).mean()))
    P("\nempty text rate by channel:\n" + tr.assign(e=tr.text.eq("")).groupby("channel").e.mean().to_string())
    m = tr.ts.dt.to_period("M").astype(str)
    closed = tr.final_team.notna()
    P("\nclosed rate by month (recent months low = still open):\n" + closed.groupby(m).mean().round(3).to_string())
    c = tr[closed]
    if len(c):
        P("\nbot team == final team, overall:", round(float((c.bot_team == c.final_team).mean()), 4))
        P("by month:\n" + (c.bot_team == c.final_team).groupby(m[closed]).mean().round(3).to_string())
        P("\nbot team (rows) x final team (cols):\n" + pd.crosstab(c.bot_team, c.final_team).to_string())
        P("\ntransfers distribution:\n" + c.transfers.value_counts(dropna=False).sort_index().to_string())
        hrs = (c.resolved_ts - c.ts).dt.total_seconds() / 3600
        P("\nresolution hours by source:\n" + hrs.groupby(c.source).describe().round(1).to_string())
        P("negative durations by source:\n" + (hrs < 0).groupby(c.source).sum().to_string())
    P("\nduplicate request_id in train:", int(tr.request_id.duplicated().sum()))
    if te is not None:
        P("exact duplicate texts train<->test:", int(te.text.isin(set(tr.text)).sum()), "of", len(te))
        recent = tr[tr.ts >= tr.ts.max() - pd.Timedelta(days=60)]
        for col in ("product_family", "channel", "warranty_status"):
            P(f"\n{col}: test vs last 60 days of train (share)\n" +
              pd.concat([te[col].value_counts(normalize=True).rename("test"),
                         recent[col].value_counts(normalize=True).rename("train_recent")], axis=1).round(3).to_string())
    text = "\n".join(L)
    settings.artifact_dir.mkdir(parents=True, exist_ok=True)
    (settings.artifact_dir / "audit.txt").write_text(text, encoding="utf-8")
    return text
