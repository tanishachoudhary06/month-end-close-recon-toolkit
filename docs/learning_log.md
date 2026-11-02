# Learning log

## Stage 1: finance basics
- **What I did:** Learned the basic ideas of accounting: journal entries, debits and credits, the general ledger, sub-ledgers (AP and AR), the trial balance and the month-end close.
- **What confused me:** What "debit" and "credit" actually mean, and why every entry has two sides.
- **What I learned:** Every journal entry has a debit side and a credit side that are equal, so the whole ledger adds up to zero. A supplier invoice debits an expense and credits Accounts Payable.

## Stage 2: project setup
- **What I did:** Created the project folder, a Python virtual environment, installed pandas, numpy, xlsxwriter and openpyxl, and selected the .venv interpreter in VS Code.
- **What confused me:** Why File Explorer showed an empty folder while VS Code showed all my files. I had two folders with the same name in different places.
- **What I learned:** Running `explorer .` in the VS Code terminal opens the exact folder VS Code is using. A short folder path avoids problems, and a virtual environment keeps the project's packages separate.

## Stage 3: generating the data
- **What I did:** Added config.py and generate_data.py and ran the script to create the ledger (gl.csv), the AP and AR lists, the chart of accounts and the answer key.
- **What confused me:** The "file not found" errors. I thought I had to download the files, but the script creates them, and it needs the right folder paths.
- **What I learned:** The generator first builds clean, balanced data and checks it, then deliberately hides 15 mistakes and records them in an answer key. A fixed random seed gives the same files on every run.

## Stage 4: reading the data
- **What I did:** Opened gl.csv, ap.csv and the answer key with Rainbow CSV and read a supplier invoice line by line.
- **What confused me:** Why the same invoice appears twice in the ledger, with one positive and one negative amount.
- **What I learned:** One document has two lines with the same DocNo, a debit (positive) and a credit (negative) that cancel out. The Reference connects the ledger to the AP and AR lists.

## Stage 5: trial balance in Excel
- **What I did:** Built a trial balance with SUMIFS formulas and company and period dropdowns, and cross-checked it with a PivotTable.
- **What confused me:** My first version said "Balanced" while every number was 0. I had typed IT09 as the period instead of 9, filled the account list by dragging so it counted 1000, 1001, 1002, and typed 999 instead of 9999. Later, why the check says "Out of balance" (IT01 period 10, FR01 period 9) when the generator had checked every document.
- **What I learned:** The generator checks the clean data first, and I hide mistakes afterwards, including two unbalanced entries that the trial balance catches. A "Balanced" result means nothing unless the sheet found data, so I added a data-found check.

## Stage 6: reconciling payables and receivables
- **What I did:** Added item-level checks to the AP and AR tables and built a Recon sheet that compares each control account (2100 and 1100) with its sub-ledger for IT01 and FR01, periods 9 and 10.
- **What confused me:** Why a row can say "Differences explained" instead of "Reconciled". Also my formulas showed as plain text because the cells were formatted as Text, and I mistyped a table name and pointed rows at the wrong block.
- **What I learned:** A reconciliation isn't finished until every difference is explained by specific items (missing in the ledger, duplicate, or amount differs), so the Unexplained column must be 0.00.

## Stage 7: data-quality checks
- **What I did:** Added flag columns to the GL table (unbalanced, duplicate, wrong period, missing cost center, invalid account), counted them on a DQ_Rules sheet (21 lines in 13 documents), and scored the results against the answer key (15 of 15 caught).
- **What confused me:** Why most flag cells are blank (the formula returns nothing unless the rule fires), and why 13 documents are flagged although the key has 11 document-level errors (the originals of the duplicated invoices are flagged too).
- **What I learned:** The missing-cost-center rule only applies to expense accounts, because bank, revenue and payables lines legitimately have no cost center. Catching 15 of 15 shows my rules cover the error types I knew about, not unknown ones.

## Stage 8: close checklist, accruals and variance analysis
- **What I did:** Built a close checklist with status dropdowns, an accruals table with reversal entries, adjustments on the trial balance, and a variance sheet that compares period 9 with period 10 and flags big changes, with a short comment on each flagged line.
- **What confused me:** Why an accrual is reversed the next month. Also my table headers turned into Column1, Column2 and my formulas showed as text.
- **What I learned:** An accrual books a cost in the month it happened, and the reversal cancels it when the real invoice arrives so it isn't counted twice. A flag threshold on both euros and percent avoids flagging everything. For example IT and Software rose 113% but only €18k, so it wasn't flagged.

## Stage 9: tests, SAP trial, documentation and GitHub
- **What I did:** Wrote 14 test cases across record-to-report, procure-to-pay and order-to-cash. I ran 10 of them: 7 in my workbook and 3 display-only tests in the SAP S/4HANA Cloud trial by following guided tours (financial statement, journal entry with related documents, general ledger line items). 8 passed, 2 failed because they found real data problems, and 4 were not run because they need posting in an SAP system. I logged 6 simulated defects with severity, owner and next step, wrote a one-page SOP and a README, and uploaded the project to GitHub.
- **What confused me:** The difference between a test that fails because of a data problem (the trial balance doesn't balance) and a test that passes because the control caught the error (the unbalanced documents were flagged). Also why Excel called my file a "network location": it was saved in a OneDrive folder, not in my project folder, so Git couldn't see it.
- **What I learned:** A good test case states what should happen and what actually happened, and links any failure to a defect ticket. In SAP I saw the same structure as my own ledger: a journal entry is a document with debit and credit line items, one business event creates a chain of linked documents, and SAP uses debit positive and credit negative like my workbook. I also learned to say clearly which tests I did not run and why.

**
I deleted a sheet that other formulas depended on. They broke (#REF!), and every account looked invalid. I rebuilt the table and re-entered the formula.” It shows you understand how Excel dependencies work.
**