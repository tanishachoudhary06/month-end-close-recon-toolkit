from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
KEY_DIR = ROOT / "data" / "answer_key"

SEED = 42
FISCAL_YEAR = 2026
PERIODS = [9, 10]
COMPANY_CODES = ["IT01", "FR01"]
CURRENCY = "EUR"

# (account, name, type)
ACCOUNTS = [
    (1000, "Bank", "Asset"),
    (1100, "Accounts Receivable", "Asset"),
    (1200, "Inventory", "Asset"),
    (1300, "Prepaid Expenses", "Asset"),
    (2100, "Accounts Payable", "Liability"),
    (2200, "Accrued Expenses", "Liability"),
    (3000, "Share Capital", "Equity"),
    (4000, "Retail Sales", "Revenue"),
    (4100, "Wholesale Sales", "Revenue"),
    (4200, "E-commerce Sales", "Revenue"),
    (5000, "Cost of Goods Sold", "Expense"),
    (6000, "Rent", "Expense"),
    (6100, "Salaries", "Expense"),
    (6200, "Utilities", "Expense"),
    (6300, "Marketing", "Expense"),
    (6400, "Insurance", "Expense"),
    (6500, "Professional Fees", "Expense"),
    (6600, "IT and Software", "Expense"),
]

COST_CENTERS = {
    "IT01": ["CC100", "CC300", "CC900"],  # Milan boutique, e-commerce, HQ
    "FR01": ["CC200", "CC300", "CC900"],  # Paris boutique, e-commerce, HQ
}

# documents generated per company and period
N_KR, N_DR, N_SA = 60, 40, 25

KR_EXPENSE_ACCOUNTS = [5000, 6200, 6300, 6400, 6500, 6600]
KR_EXPENSE_WEIGHTS = [0.35, 0.10, 0.20, 0.05, 0.15, 0.15]
REVENUE_ACCOUNTS = [4000, 4100, 4200]
REVENUE_WEIGHTS = [0.4, 0.3, 0.3]

# (text, debit account, credit account, min EUR, max EUR)
SA_TEMPLATES = [
    ("Payroll", 6100, 1000, 8_000, 20_000),
    ("Rent", 6000, 1000, 5_000, 15_000),
    ("Insurance amortisation", 6400, 1300, 500, 2_000),
]
SA_WEIGHTS = [0.4, 0.3, 0.3]

# business event for Module F: marketing campaign in Italy in period 10
MARKETING_UPLIFT = {("IT01", 10): 1.4}

# number of seeded errors of each type
ERRORS = {
    "unbalanced": 2,
    "duplicate": 2,
    "wrong_period": 2,
    "missing_cost_center": 3,
    "invalid_account": 2,
    "ap_missing_in_gl": 1,
    "ap_amount_differs": 1,
    "ar_missing_in_gl": 1,
    "ar_amount_differs": 1,
}
INVALID_ACCOUNT = 9999