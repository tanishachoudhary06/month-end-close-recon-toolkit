# SOP: Month-end close and reconciliation
Version 1.0 · Owner: Finance Operations · Data: synthetic

## Purpose
Make sure the ledger is complete, balanced and correct before a period is closed.

## Scope
General ledger, accounts payable and accounts receivable for companies IT01 and FR01.

## Inputs
Ledger lines (gl.csv), supplier list (ap.csv), customer list (ar.csv), chart of accounts (coa.csv).

## Steps
1. Confirm the posting period and the cut-off date.
2. Confirm that all supplier and customer invoices are posted.
3. Run the trial balance for each company and period. The net total must be 0.00.
4. Reconcile the AP list to account 2100 and the AR list to account 1100 (Recon sheet). Explain every difference.
5. Run the data-quality checks (DQ_Rules sheet) and review every flagged line.
6. Raise a ticket for each issue with an owner and a next step (Defects sheet).
7. Post corrections, then repeat steps 3 to 5 until the checks are clean.
8. Post accruals and prepaid amortisation. Reverse the accruals in the next period.
9. Review the variance against the prior month and comment on every flagged line.
10. Complete the close checklist and get sign-off.
11. Lock the period.

## Controls
- Trial balance net total is 0.00 and the sheet confirms data was found.
- The Unexplained column in the reconciliation is 0.00.
- Flag thresholds for variances: EUR 20,000 and 20%.

## Exceptions
Anything that cannot be fixed before sign-off is logged as a ticket with an owner and a date.