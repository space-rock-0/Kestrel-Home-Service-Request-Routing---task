"""Text repair, feature columns, team-name mapping, timestamp parsing."""
from __future__ import annotations

import re
import unicodedata

import pandas as pd
from ftfy import fix_text


def clean_text(s) -> str:
    """Repair mojibake (legacy Zoho export), normalise unicode and whitespace, lowercase."""
    if not isinstance(s, str):
        return ""
    s = fix_text(s)
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"\s+", " ", s).strip()


def _mixed(s: pd.Series, dayfirst: bool = False) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", format="mixed", dayfirst=dayfirst)


def parse_ts(s: pd.Series) -> pd.Series:
    """Parse dates from Excel or CSV.

    - Excel serial numbers (a date cell formatted as General, e.g. 45678.5) convert from the 1899-12-30 origin.
    - Everything else parses cell by cell (format='mixed'). Without it pandas infers one format from row 1
      and turns the rest into NaT. Day-first is tried only when it parses clearly more cells.
    """
    s = s.astype(str).str.strip()
    num = pd.to_numeric(s, errors="coerce")
    serial = num.between(20000, 80000)
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    if serial.any():
        out.loc[serial] = pd.to_datetime(num[serial], unit="D", origin="1899-12-30")
    rest = ~serial
    if rest.any():
        a = _mixed(s[rest])
        if a.isna().mean() > 0.02:
            b = _mixed(s[rest], True)
            if b.isna().sum() < a.isna().sum():
                a = b
        out.loc[rest] = a
    return out


def add_meta(df: pd.DataFrame) -> pd.DataFrame:
    """Token column with product, warranty, channel and the product x warranty cross. `source` is excluded on purpose."""
    df = df.copy()
    p = df["product_family"].str.replace(r"\s+", "_", regex=True)
    w = df["warranty_status"].str.replace(r"\s+", "_", regex=True)
    c = df["channel"].str.replace(r"\s+", "_", regex=True)
    df["meta"] = "p_" + p + " w_" + w + " c_" + c + " pw_" + p + "_" + w
    return df


# teams.csv carries a human note in the renamed_to cell, e.g. "Installs & Demo (from 15 Jan 2026)".
# That date belongs to the team change, not to the team's name. Left in place it becomes part of the
# canonical label, which splits one queue into two classes and puts a name no scorer recognises in predictions.csv.
RENAME_NOTE = re.compile(r"\s*\((?:from|since|renamed|effective|w\.e\.f\.?)[^)]*\)\s*$", re.I)


def bare_team_name(value) -> str | None:
    """The team name alone: the renamed_to cell without its trailing note. None when the cell is empty."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return RENAME_NOTE.sub("", str(value).strip()).strip() or None


def build_team_map(teams: pd.DataFrame, train: pd.DataFrame):
    """Map old and new team names to one canonical name.

    A renamed team is one queue with two spellings, so both spellings map to one label:

    - the note in ``renamed_to`` is stripped, so ``Installs & Demo (from 15 Jan 2026)`` becomes
      ``Installs & Demo``
    - the current name wins by default, because that is what the newest rows are written with
    - the old name only wins while it is genuinely still the more common one in the last 60 days of
      training data. The test set is the most recent data, so it follows whichever name is in use.

    Every official queue therefore keeps exactly one label, and no label carries a date.
    """
    ts = parse_ts(train["created_at_ist"])
    recent = train.loc[ts >= ts.max() - pd.Timedelta(days=60), "team_label"].str.strip().value_counts()
    m = {}
    for _, r in teams.iterrows():
        old = str(r["team"]).strip()
        new = bare_team_name(r.get("renamed_to"))
        if new and new != old:
            canon = old if recent.get(old, 0) > recent.get(new, 0) else new
            m[old] = m[new] = canon
        else:
            m.setdefault(old, old)
    return m, sorted(set(m.values()))
