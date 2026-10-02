"""Example plugin. It is real: counts rows per input file. Copy this file to add your own tools.

A plugin is any .py file (or package) in plugins/ that defines register(registry).
"""
from kestrel.data.discovery import discover, read_detected
from kestrel.extensions import Tool


class DataSummaryTool(Tool):
    name = "data_summary"
    description = "Row and column counts for every detected input file."

    def run(self, ctx, **params):
        disc = discover(ctx.settings)
        out = {}
        for role, f in disc.by_role.items():
            df = read_detected(ctx.settings, f, role)
            out[role] = {"file": f.path.name, "rows": int(len(df)), "columns": list(df.columns)}
        return out


def register(registry):
    registry.register(DataSummaryTool())
