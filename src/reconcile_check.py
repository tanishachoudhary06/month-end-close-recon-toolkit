import pandas as pd

import config as cfg

TOLERANCE = 0.01
RULES = ["Unbalanced", "Duplicate", "WrongPeriod", "MissingCC", "InvalidAcct"]

# numbers read from the Excel workbook; the script compares its own results to these
EXPECTED = {
    "trial_balance": {("IT01", 9): 0.0, ("IT01", 10): 465.50, ("FR01", 9): 82.18, ("FR01", 10): 0.0},
    "ap_difference": {("IT01", 9): -9763.69, ("IT01", 10): 5943.28, ("FR01", 9): 0.0, ("FR01", 10): -15932.01},
    "ar_difference": {("IT01", 9): 3916.33, ("IT01", 10): 0.0, ("FR01", 9): 0.0, ("FR01", 10): 584.96},
    "flagged_lines": {"Unbalanced": 4, "Duplicate": 8, "WrongPeriod": 4, "MissingCC": 3, "InvalidAcct": 2},
    "any_flagged_lines": 21,
    "any_flagged_documents": 13,
    "errors_caught": 15,
}


def load_data():
    gl = pd.read_csv(cfg.RAW_DIR / "gl.csv", parse_dates=["PostingDate"])
    ap = pd.read_csv(cfg.RAW_DIR / "ap.csv")
    ar = pd.read_csv(cfg.RAW_DIR / "ar.csv")
    coa = pd.read_csv(cfg.RAW_DIR / "coa.csv")
    key = pd.read_csv(cfg.KEY_DIR / "error_key.csv")
    return gl, ap, ar, coa, key


def trial_balance(gl):
    return gl.groupby(["CompanyCode", "Period"])["AmountEUR"].sum().round(2)


def reconcile(gl, subledger, control, sign):
    """sign is -1 for payables (credit balance) and 1 for receivables."""
    keys = ["CompanyCode", "Period"]
    control_lines = gl[gl["GLAccount"] == control]

    in_gl = control_lines.groupby("Reference")["AmountEUR"].agg(["sum", "size"])
    items = subledger.merge(in_gl, how="left", left_on="InvoiceNo", right_index=True)
    items["InGL"] = items["size"].fillna(0).astype(int)
    items["GLAmt"] = (sign * items["sum"]).fillna(0).round(2)
    items["Diff"] = (items["Amount"] - items["GLAmt"]).round(2)
    items["Status"] = "OK"
    items.loc[items["Diff"].abs() > TOLERANCE, "Status"] = "Amount differs"
    items.loc[items["InGL"] > 1, "Status"] = "Duplicate in GL"
    items.loc[items["InGL"] == 0, "Status"] = "Missing in GL"

    summary = pd.DataFrame({
        "GL": (sign * control_lines.groupby(keys)["AmountEUR"].sum()).round(2),
        "Sub": subledger.groupby(keys)["Amount"].sum().round(2),
        "Explained": items.groupby(keys)["Diff"].sum().round(2),
    }).fillna(0)
    summary["Difference"] = (summary["Sub"] - summary["GL"]).round(2)
    summary["Unexplained"] = (summary["Difference"] - summary["Explained"]).round(2)
    return items, summary


def data_quality_flags(gl, coa):
    flags = gl.copy()
    types = coa.set_index("Account")["Type"]
    flags["Type"] = flags["GLAccount"].map(types).fillna("UNKNOWN")
    flags["Unbalanced"] = flags.groupby("DocNo")["AmountEUR"].transform("sum").abs() > TOLERANCE
    flags["Duplicate"] = flags.groupby(["Reference", "GLAccount", "AmountEUR"])["LineID"].transform("size") > 1
    flags["WrongPeriod"] = flags["PostingDate"].dt.month != flags["Period"]
    flags["MissingCC"] = (flags["Type"] == "Expense") & flags["CostCenter"].isna()
    flags["InvalidAcct"] = flags["Type"] == "UNKNOWN"
    flags["AnyFlag"] = flags[RULES].any(axis=1)
    return flags


def score_against_key(key, flags, ap_items, ar_items):
    items = pd.concat([ap_items, ar_items])
    problem_invoices = set(items.loc[items["Status"] != "OK", "InvoiceNo"])
    flagged_docs = set(flags.loc[flags["AnyFlag"], "DocNo"])

    def caught(row):
        if pd.notna(row["InvoiceNo"]):
            return row["InvoiceNo"] in problem_invoices
        return row["DocNo"] in flagged_docs

    return key.assign(Caught=key.apply(caught, axis=1))


def compare(label, actual, expected):
    ok = abs(actual - expected) <= TOLERANCE
    print(f"  {'OK      ' if ok else 'MISMATCH'}  {label}: python {actual}, excel {expected}")
    return ok


def main():
    gl, ap, ar, coa, key = load_data()
    results = []

    print("Trial balance (net total per company and period)")
    tb = trial_balance(gl)
    for (company, period), expected in EXPECTED["trial_balance"].items():
        results.append(compare(f"{company} period {period}", tb[(company, period)], expected))

    ap_items, ap_summary = reconcile(gl, ap, 2100, -1)
    ar_items, ar_summary = reconcile(gl, ar, 1100, 1)
    for name, summary, expected_diffs in (
        ("AP", ap_summary, EXPECTED["ap_difference"]),
        ("AR", ar_summary, EXPECTED["ar_difference"]),
    ):
        print(f"\n{name} reconciliation (sub-ledger minus GL)")
        for (company, period), expected in expected_diffs.items():
            results.append(compare(f"{company} period {period}", summary.loc[(company, period), "Difference"], expected))
        results.append(compare("unexplained difference", summary["Unexplained"].abs().sum(), 0.0))

    print("\nProblem invoices")
    problems = pd.concat([ap_items, ar_items])
    problems = problems[problems["Status"] != "OK"]
    print(problems[["InvoiceNo", "CompanyCode", "Period", "Amount", "GLAmt", "Diff", "Status"]].to_string(index=False))

    print("\nData-quality flags (lines)")
    flags = data_quality_flags(gl, coa)
    for rule, expected in EXPECTED["flagged_lines"].items():
        results.append(compare(rule, int(flags[rule].sum()), expected))
    results.append(compare("any flag, lines", int(flags["AnyFlag"].sum()), EXPECTED["any_flagged_lines"]))
    results.append(compare("any flag, documents", flags.loc[flags["AnyFlag"], "DocNo"].nunique(),
                           EXPECTED["any_flagged_documents"]))

    print("\nScore against the answer key")
    scored = score_against_key(key, flags, ap_items, ar_items)
    print(scored.groupby("ErrorType")["Caught"].agg(["size", "sum"]).rename(columns={"size": "Seeded", "sum": "Caught"}).to_string())
    results.append(compare("errors caught", int(scored["Caught"].sum()), EXPECTED["errors_caught"]))

    mismatches = results.count(False)
    print("\nAll checks agree with the workbook." if mismatches == 0 else f"\n{mismatches} check(s) do not agree.")


if __name__ == "__main__":
    main()