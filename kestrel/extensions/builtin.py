"""Built-in tools, commands and the full_pipeline workflow. They call kestrel.services only."""
from __future__ import annotations

from .. import services
from ..errors import ExtensionError
from .base import Command, Step, Tool, Workflow


def _opt(args: list, flag: str, default=None):
    if flag in args:
        i = args.index(flag)
        if i + 1 >= len(args):
            raise ExtensionError(f"{flag} needs a value.")
        return args[i + 1]
    return default


class DataStatusTool(Tool):
    name, description = "data_status", "Which input files were found, which roles are missing, whether the model is stale."

    def run(self, ctx, **p):
        return services.data_status(ctx)


class ValidateDataTool(Tool):
    name, description = "validate_data", "Validate the input folder for 'train' or 'predict'."
    input_schema = {"type": "object", "properties": {"action": {"type": "string", "enum": ["train", "predict"], "default": "train"}}}

    def run(self, ctx, action: str = "train", **p):
        return services.validate_data(ctx, action)


class RouteRequestTool(Tool):
    name, description = "route_request", "Route one request: team, confidence, reasons."
    input_schema = {"type": "object", "required": ["request_text"], "properties": {
        "request_text": {"type": "string"}, "product_family": {"type": "string"},
        "warranty_status": {"type": "string"}, "channel": {"type": "string"}}}

    def run(self, ctx, **record):
        return ctx.router.route(record)


class ReadMetricsTool(Tool):
    name, description = "read_metrics", "Latest training metrics (holdout accuracy, bot baseline, gate)."

    def run(self, ctx, **p):
        return services.read_metrics(ctx)


class StatusCommand(Command):
    name, description, usage = "status", "Show input files and model state.", "status"

    def run(self, ctx, args):
        return services.data_status(ctx)


class ValidateCommand(Command):
    name, description, usage = "validate", "Validate input files.", "validate [--action train|predict]"

    def run(self, ctx, args):
        return services.validate_data(ctx, _opt(args, "--action", "train"))


class AuditCommand(Command):
    name, description, usage = "audit", "Write artifacts/audit.txt (data forensics).", "audit"

    def run(self, ctx, args):
        return services.run_audit(ctx)


class TrainCommand(Command):
    name, description, usage = "train", "Train, evaluate, write model and predictions.", "train"

    def run(self, ctx, args):
        return services.run_train(ctx)


class PredictCommand(Command):
    name, description, usage = "predict", "Route the test file with the current model.", "predict [--out path.csv]"

    def run(self, ctx, args):
        return services.predict_file(ctx, _opt(args, "--out"))


class CheckSubmissionCommand(Command):
    name, description, usage = "check_submission", "Validate predictions.csv against the test file and team names.", "check_submission [--path file.csv]"

    def run(self, ctx, args):
        return services.check_submission(ctx, _opt(args, "--path"))


class GoldenCommand(Command):
    name, description, usage = "golden", "Run the fixed cases from the client's email (config/golden_cases.json).", "golden [--path file.json]"

    def run(self, ctx, args):
        return services.golden(ctx, _opt(args, "--path"))


class NumbersCommand(Command):
    name = "numbers"
    description = "Rupee and volume arithmetic from measured values."
    usage = ("numbers --transfer-cost-inr N [--hosting-inr-month N] [--licence-inr-year N] [--orders-per-month N] "
             "[--maintenance-hours-month N] [--hour-inr N]")

    def run(self, ctx, args):
        raw = _opt(args, "--transfer-cost-inr")
        if raw is None:
            raise ExtensionError("--transfer-cost-inr is required (cost of one transfer, from the ops policy).")
        try:
            kw = {"transfer_cost_inr": float(raw)}
            for flag, key in (("--hosting-inr-month", "hosting_inr_month"), ("--licence-inr-year", "licence_inr_year"),
                              ("--orders-per-month", "orders_per_month"), ("--maintenance-hours-month", "maintenance_hours_month"),
                              ("--hour-inr", "hour_inr")):
                v = _opt(args, flag)
                if v is not None:
                    kw[key] = float(v)
        except ValueError as e:
            raise ExtensionError(f"Numeric argument expected: {e}") from e
        return services.numbers(ctx, **kw)


class DoctorCommand(Command):
    name, description, usage = "doctor", "Check environment, input files, validation and model state.", "doctor [--strict]"

    def run(self, ctx, args):
        return services.doctor(ctx, "--strict" in args)


class PolicyTextCommand(Command):
    name, description, usage = "policy_text", "Extract the policy PDF to artifacts/policy.txt and list cost-looking lines.", "policy_text"

    def run(self, ctx, args):
        return services.policy_text(ctx)


class AuditRulesCommand(Command):
    name, description, usage = "audit_rules", "Measure each rules.json rule against closed CRM history.", "audit_rules"

    def run(self, ctx, args):
        return services.audit_rules(ctx)


class FormValuesCommand(Command):
    name, description, usage = "form_values", "Measured values for the form and memo (writes artifacts/form_values.json).", "form_values [--flagged-limit 0.30]"

    def run(self, ctx, args):
        v = _opt(args, "--flagged-limit")
        return services.form_values(ctx, float(v) if v is not None else None)


class RenderDocsCommand(Command):
    name = "render_docs"
    description = "Fill docs/templates/*.md from measured values and write output/MEMO.md, output/EVIDENCE.md."
    usage = "render_docs [--transfer-cost-inr N] [--hosting-inr-month N] [--flagged-limit 0.30]"

    def run(self, ctx, args):
        try:
            tc, host, fl = _opt(args, "--transfer-cost-inr"), _opt(args, "--hosting-inr-month", "0"), _opt(args, "--flagged-limit")
            return services.render_docs(ctx, float(tc) if tc is not None else None, float(host), float(fl) if fl is not None else None)
        except ValueError as e:
            raise ExtensionError(f"Numeric argument expected: {e}") from e


class FullPipeline(Workflow):
    name = "full_pipeline"
    description = "Validate input, write the audit, train and evaluate, check predictions."
    steps = [Step("command", "validate", {"args": []}, "validate input"),
             Step("command", "audit", {"args": []}, "audit data"),
             Step("command", "train", {"args": []}, "train and evaluate"),
             Step("command", "check_submission", {"args": []}, "check predictions")]


def register_builtins(registry) -> None:
    for cls in (DataStatusTool, ValidateDataTool, RouteRequestTool, ReadMetricsTool, StatusCommand, ValidateCommand,
                AuditCommand, TrainCommand, PredictCommand, CheckSubmissionCommand, GoldenCommand, NumbersCommand, DoctorCommand, PolicyTextCommand, AuditRulesCommand, FormValuesCommand,
                RenderDocsCommand, FullPipeline):
        registry.register(cls())
