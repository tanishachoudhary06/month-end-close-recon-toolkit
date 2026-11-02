import calendar

import numpy as np
import pandas as pd

import config as cfg

EXPENSE_ACCOUNTS = [a for a, _, t in cfg.ACCOUNTS if t == "Expense"]
ACCOUNT_NAMES = {a: n for a, n, _ in cfg.ACCOUNTS}
GL_COLUMNS = [
    "LineID", "CompanyCode", "FiscalYear", "Period", "PostingDate", "DocNo",
    "DocType", "LineNo", "GLAccount", "CostCenter", "Party", "Reference",
    "Currency", "AmountDoc", "AmountEUR", "Text",
]
SUBLEDGER_COLUMNS = ["InvoiceNo", "Party", "CompanyCode", "Period", "PostingDate", "Amount"]


def build_coa():
    return pd.DataFrame(cfg.ACCOUNTS, columns=["Account", "Name", "Type"])


def random_date(rng, period):
    last_day = calendar.monthrange(cfg.FISCAL_YEAR, period)[1]
    return pd.Timestamp(cfg.FISCAL_YEAR, period, int(rng.integers(1, last_day + 1)))


def to_cents(euros):
    return int(round(euros * 100))


def make_doc(doc_no, doc_type, company, period, date, reference, party, text, lines):
    """lines = [(account, signed_cents, cost_center), ...] and must net to zero."""
    assert sum(cents for _, cents, _ in lines) == 0, "document is not balanced"
    return [
        {
            "CompanyCode": company,
            "FiscalYear": cfg.FISCAL_YEAR,
            "Period": period,
            "PostingDate": date,
            "DocNo": doc_no,
            "DocType": doc_type,
            "LineNo": n,
            "GLAccount": account,
            "CostCenter": cost_center,
            "Party": party,
            "Reference": reference,
            "Currency": cfg.CURRENCY,
            "AmountCents": cents,
            "Text": text,
        }
        for n, (account, cents, cost_center) in enumerate(lines, start=1)
    ]


def build_gl_and_subledgers(rng):
    gl_rows, ap_rows, ar_rows = [], [], []
    doc_no = 1_900_000_000
    seq = 0  # one running number keeps every reference unique

    for company in cfg.COMPANY_CODES:
        for period in cfg.PERIODS:
            # supplier invoices: debit expense, credit accounts payable
            for _ in range(cfg.N_KR):
                doc_no += 1
                seq += 1
                account = int(rng.choice(cfg.KR_EXPENSE_ACCOUNTS, p=cfg.KR_EXPENSE_WEIGHTS))
                uplift = cfg.MARKETING_UPLIFT.get((company, period), 1.0) if account == 6300 else 1.0
                cents = max(to_cents(rng.lognormal(8.0, 0.9) * uplift), 5_000)
                party = f"V{int(rng.integers(1, 21)):03d}"
                reference = f"INV-{company}-{seq:05d}"
                date = random_date(rng, period)
                cost_center = str(rng.choice(cfg.COST_CENTERS[company]))
                gl_rows += make_doc(
                    doc_no, "KR", company, period, date, reference, party,
                    f"{ACCOUNT_NAMES[account]} - {party}",
                    [(account, cents, cost_center), (2100, -cents, "")],
                )
                ap_rows.append({
                    "InvoiceNo": reference, "Party": party, "CompanyCode": company,
                    "Period": period, "PostingDate": date, "AmountCents": cents, "DocNo": doc_no,
                })

            # customer invoices: debit accounts receivable, credit revenue
            for _ in range(cfg.N_DR):
                doc_no += 1
                seq += 1
                account = int(rng.choice(cfg.REVENUE_ACCOUNTS, p=cfg.REVENUE_WEIGHTS))
                cents = max(to_cents(rng.lognormal(9.5, 0.8)), 5_000)
                party = f"C{int(rng.integers(1, 31)):03d}"
                reference = f"SI-{company}-{seq:05d}"
                date = random_date(rng, period)
                gl_rows += make_doc(
                    doc_no, "DR", company, period, date, reference, party,
                    f"{ACCOUNT_NAMES[account]} - {party}",
                    [(1100, cents, ""), (account, -cents, "")],
                )
                ar_rows.append({
                    "InvoiceNo": reference, "Party": party, "CompanyCode": company,
                    "Period": period, "PostingDate": date, "AmountCents": cents, "DocNo": doc_no,
                })

            # general journals: payroll, rent, insurance amortisation
            for _ in range(cfg.N_SA):
                doc_no += 1
                seq += 1
                text, debit, credit, low, high = cfg.SA_TEMPLATES[
                    int(rng.choice(len(cfg.SA_TEMPLATES), p=cfg.SA_WEIGHTS))
                ]
                cents = to_cents(rng.uniform(low, high))
                reference = f"JV-{company}-{seq:05d}"
                date = random_date(rng, period)
                cost_center = str(rng.choice(cfg.COST_CENTERS[company]))
                gl_rows += make_doc(
                    doc_no, "SA", company, period, date, reference, "", text,
                    [(debit, cents, cost_center), (credit, -cents, "")],
                )

    gl = pd.DataFrame(gl_rows)
    gl.insert(0, "LineID", range(1, len(gl) + 1))
    return gl, pd.DataFrame(ap_rows), pd.DataFrame(ar_rows)


def check_clean(gl, ap, ar, coa):
    assert gl["LineID"].is_unique, "LineID must be unique"
    assert set(gl["GLAccount"]) <= set(coa["Account"]), "unknown account in GL"
    assert (gl.groupby("DocNo")["AmountCents"].sum() == 0).all(), "unbalanced document"
    for subledger, control, sign in ((ap, 2100, -1), (ar, 1100, 1)):
        in_gl = gl[gl["GLAccount"] == control].groupby(["CompanyCode", "Period"])["AmountCents"].sum() * sign
        in_sub = subledger.groupby(["CompanyCode", "Period"])["AmountCents"].sum()
        assert in_gl.sub(in_sub, fill_value=0).eq(0).all(), f"account {control} does not match its sub-ledger"


def seed_errors(rng, gl, ap, ar):
    key = []
    used = set()  # one error per document keeps the answer key unambiguous

    def pick_docs(mask, n):
        pool = [int(d) for d in gl.loc[mask, "DocNo"].unique() if int(d) not in used]
        chosen = [int(d) for d in rng.choice(pool, size=n, replace=False)]
        used.update(chosen)
        return chosen

    def doc_info(doc_no):
        row = gl.loc[gl["DocNo"] == doc_no].iloc[0]
        return row["CompanyCode"], int(row["Period"])

    def expense_line(doc_no):
        return gl.index[(gl["DocNo"] == doc_no) & gl["GLAccount"].isin(EXPENSE_ACCOUNTS)][0]

    def log(error_type, description, company, period, doc_no=None, line_id=None, invoice_no=None):
        key.append({
            "ErrorID": f"E{len(key) + 1:02d}", "ErrorType": error_type,
            "CompanyCode": company, "Period": period, "DocNo": doc_no,
            "LineID": line_id, "InvoiceNo": invoice_no, "Description": description,
        })

    # 1. unbalanced documents: push one line of a journal off by 50-500 EUR
    for d in pick_docs(gl["DocType"] == "SA", cfg.ERRORS["unbalanced"]):
        company, period = doc_info(d)
        delta = int(rng.integers(5_000, 50_000))
        row = gl.index[(gl["DocNo"] == d) & (gl["LineNo"] == 1)][0]
        gl.loc[row, "AmountCents"] += delta
        log("Unbalanced document", f"Debit line raised by {delta / 100:.2f} EUR",
            company, period, doc_no=d)

    # 2. duplicate invoices: copy a whole supplier invoice under a new document number
    for d in pick_docs(gl["DocType"] == "KR", cfg.ERRORS["duplicate"]):
        company, period = doc_info(d)
        copy = gl[gl["DocNo"] == d].copy()
        new_doc = int(gl["DocNo"].max()) + 1
        first_id = int(gl["LineID"].max()) + 1
        copy["DocNo"] = new_doc
        copy["LineID"] = range(first_id, first_id + len(copy))
        gl = pd.concat([gl, copy], ignore_index=True)
        used.add(new_doc)
        log("Duplicate invoice", f"DocNo {new_doc} duplicates DocNo {d}",
            company, period, doc_no=new_doc)

    # 3. wrong period: posting date falls in the next month, period stays the same
    for d in pick_docs(gl["DocNo"].notna(), cfg.ERRORS["wrong_period"]):
        company, period = doc_info(d)
        date = pd.Timestamp(cfg.FISCAL_YEAR, period + 1, int(rng.integers(1, 29)))
        gl.loc[gl["DocNo"] == d, "PostingDate"] = date
        log("Wrong period", f"Posted {date:%Y-%m-%d} but assigned to period {period}",
            company, period, doc_no=d)

    # 4. missing cost center on an expense line
    for d in pick_docs(gl["GLAccount"].isin(EXPENSE_ACCOUNTS), cfg.ERRORS["missing_cost_center"]):
        company, period = doc_info(d)
        row = expense_line(d)
        gl.loc[row, "CostCenter"] = ""
        log("Missing cost center", "Cost center left blank on expense line",
            company, period, doc_no=d, line_id=int(gl.loc[row, "LineID"]))

    # 5. invalid account on an expense line (document stays balanced)
    for d in pick_docs(gl["GLAccount"].isin(EXPENSE_ACCOUNTS), cfg.ERRORS["invalid_account"]):
        company, period = doc_info(d)
        row = expense_line(d)
        gl.loc[row, "GLAccount"] = cfg.INVALID_ACCOUNT
        log("Invalid account", f"Expense line posted to account {cfg.INVALID_ACCOUNT}",
            company, period, doc_no=d, line_id=int(gl.loc[row, "LineID"]))

    # 6. sub-ledger vs GL mismatches
    for subledger, doc_type, label, missing_n, amount_n in (
        (ap, "KR", "AP", cfg.ERRORS["ap_missing_in_gl"], cfg.ERRORS["ap_amount_differs"]),
        (ar, "DR", "AR", cfg.ERRORS["ar_missing_in_gl"], cfg.ERRORS["ar_amount_differs"]),
    ):
        for d in pick_docs(gl["DocType"] == doc_type, missing_n):
            company, period = doc_info(d)
            invoice = subledger.loc[subledger["DocNo"] == d, "InvoiceNo"].iloc[0]
            gl = gl[gl["DocNo"] != d]
            log(f"{label} sub-ledger mismatch", f"{invoice} is in the {label} sub-ledger but missing in the GL",
                company, period, doc_no=d, invoice_no=invoice)
        for d in pick_docs(gl["DocType"] == doc_type, amount_n):
            company, period = doc_info(d)
            invoice = subledger.loc[subledger["DocNo"] == d, "InvoiceNo"].iloc[0]
            delta = int(rng.integers(10_000, 100_000))
            subledger.loc[subledger["DocNo"] == d, "AmountCents"] += delta
            log(f"{label} sub-ledger mismatch", f"{invoice} amount differs by {delta / 100:.2f} EUR",
                company, period, doc_no=d, invoice_no=invoice)

    key_df = pd.DataFrame(key).astype({"DocNo": "Int64", "LineID": "Int64"})
    return gl.reset_index(drop=True), ap, ar, key_df


def export(gl, ap, ar, coa, key):
    cfg.RAW_DIR.mkdir(parents=True, exist_ok=True)
    cfg.KEY_DIR.mkdir(parents=True, exist_ok=True)

    gl_out = gl.sort_values(["DocNo", "LineNo"]).copy()
    gl_out["AmountEUR"] = (gl_out["AmountCents"] / 100).round(2)
    gl_out["AmountDoc"] = gl_out["AmountEUR"]
    gl_out["PostingDate"] = gl_out["PostingDate"].dt.strftime("%Y-%m-%d")
    gl_out[GL_COLUMNS].to_csv(cfg.RAW_DIR / "gl.csv", index=False)

    for name, subledger in (("ap", ap), ("ar", ar)):
        out = subledger.copy()
        out["Amount"] = (out["AmountCents"] / 100).round(2)
        out["PostingDate"] = out["PostingDate"].dt.strftime("%Y-%m-%d")
        out[SUBLEDGER_COLUMNS].to_csv(cfg.RAW_DIR / f"{name}.csv", index=False)

    coa.to_csv(cfg.RAW_DIR / "coa.csv", index=False)
    key.to_csv(cfg.KEY_DIR / "error_key.csv", index=False)


def main():
    rng = np.random.default_rng(cfg.SEED)
    coa = build_coa()
    gl, ap, ar = build_gl_and_subledgers(rng)
    check_clean(gl, ap, ar, coa)
    print(f"clean data OK: {len(gl)} GL lines, {gl['DocNo'].nunique()} documents")

    gl, ap, ar, key = seed_errors(rng, gl, ap, ar)
    export(gl, ap, ar, coa, key)

    print(f"after seeding: {len(gl)} GL lines, {len(ap)} AP invoices, {len(ar)} AR invoices")
    print(f"{len(key)} errors seeded:")
    print(key["ErrorType"].value_counts().to_string())
    print(f"files written to {cfg.RAW_DIR} and {cfg.KEY_DIR}")


if __name__ == "__main__":
    main()