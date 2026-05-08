import pandas as pd
import re

CATEGORIES = {
    "Food Delivery": [
        "uber eats", "ubereats", "doordash", "door dash", "grubhub", "grub hub",
        "zomato", "swiggy", "instacart", "gopuff", "go puff", "postmates",
        "seamless", "caviar", "favor delivery",
    ],
    "Dining Out": [
        "restaurant", "cafe", "coffee", "starbucks", "mcdonald", "mcdonalds",
        "subway", "chipotle", "pizza", "sushi", "burger", "taco bell", "wendy",
        "dunkin", "panera", "chick-fil", "chick fil", "wing", "diner", "bistro",
        "grill", "eatery", "kitchen", "bar & grill", "applebee", "olive garden",
        "red lobster", "outback", "cheesecake factory", "ihop", "denny", "waffle house",
        "five guys", "shake shack", "in-n-out", "popeye", "kfc", "domino",
        "papa john", "little caesar", "smoothie king", "jamba juice", "peet",
    ],
    "Groceries": [
        "walmart grocery", "kroger", "whole foods", "trader joe", "safeway",
        "costco", "aldi", "publix", "grocery", "supermarket", "fresh market",
        "wegmans", "sprouts", "food lion", "stop & shop", "h-e-b", "heb",
        "meijer", "giant food", "winn-dixie", "winco", "smart & final",
        "market basket", "price chopper", "shoprite", "harris teeter",
        "fresh thyme", "natural grocers",
    ],
    "Transport": [
        "lyft", "metro card", "transit", "parking", "toll", "shell", "bp",
        "chevron", "exxon", "mobil", "sunoco", "citgo", "marathon gas",
        "valero", "speedway", "wawa fuel", "mta ", "bart ", "wmata", "cta ",
        "septa", "amtrak", "greyhound", "peter pan bus", "gas station",
        "fuel", "sunpass", "e-zpass", "ezpass", "fastrak", "peach pass",
    ],
    "Subscriptions": [
        "netflix", "spotify", "hulu", "disney+", "disney plus", "amazon prime",
        "apple one", "apple tv", "apple music", "apple icloud", "youtube premium",
        "hbo max", "hbomax", "peacock", "paramount+", "paramount plus",
        "adobe creative", "microsoft 365", "google one", "dropbox",
        "icloud storage", "audible", "kindle unlimited", "sirius xm", "siriusxm",
        "gym membership", "planet fitness", "la fitness", "24 hour fitness",
        "anytime fitness", "orange theory", "equinox",
    ],
    "Shopping": [
        "amazon.com", "amazon mktp", "target", "zara", "h&m", "ebay",
        "etsy", "best buy", "home depot", "lowe's", "lowes", "ikea",
        "gap online", "old navy", "forever 21", "nordstrom", "macy's",
        "macys", "tj maxx", "tjmaxx", "ross stores", "marshalls",
        "dollar tree", "dollar general", "five below", "bath & body",
        "ulta beauty", "sephora", "chewy", "petco", "petsmart",
        "wayfair", "overstock", "newegg", "gamestop", "steam purchase",
    ],
    "Healthcare": [
        "pharmacy", "cvs pharmacy", "walgreens", "rite aid", "doctor",
        "hospital", "clinic", "dental", "medical center", "urgent care",
        "labcorp", "lab corp", "quest diagnostics", "optometrist", "vision center",
        "therapist", "mental health", "dermatology", "orthopedic",
        "radiology", "pathology", "patient first",
    ],
    "ATM & Cash": [
        "atm", "cash withdrawal", "cash advance", "cashback",
        "cash back at", "teller cash",
    ],
    "Bank Fees": [
        "monthly maintenance fee", "overdraft fee", "service charge",
        "late fee", "annual fee", "returned item fee", "wire fee",
        "foreign transaction fee", "minimum balance fee", "paper statement fee",
        "interest charge", "finance charge", "penalty fee",
    ],
    "Travel": [
        "airline", "hotel", "airbnb", "vrbo", "booking.com", "expedia",
        "delta air", "united air", "american airlines", "southwest airlines",
        "jetblue", "spirit air", "frontier air", "alaska air",
        "marriott", "hilton", "hyatt", "ihg hotel", "best western",
        "car rental", "hertz", "enterprise rent", "avis", "budget rent",
        "national car", "alamo rent",
    ],
    "Income": [
        "direct deposit", "payroll", "ach deposit", "salary deposit",
        "wages", "paycheck", "zelle received from", "venmo payment received",
        "venmo cashout", "cash app deposit", "transfer received",
        "freelance", "consulting payment", "tax refund",
    ],
    "Transfer": [
        "zelle payment to", "zelle sent", "venmo payment to",
        "paypal transfer", "cash app to", "wire transfer",
        "transfer to ", "transfer from ", "internal transfer",
        "savings transfer", "account transfer",
    ],
}


def categorize_transaction(description):
    """Assign a category to a single transaction description."""
    desc_lower = description.lower()

    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in desc_lower:
                return category

    # Uber could be ride-share or food delivery — default to Transport if not "eats"
    if "uber" in desc_lower and "eats" not in desc_lower:
        return "Transport"

    # Walmart without "grocery" context defaults to Shopping
    if "walmart" in desc_lower:
        return "Shopping"

    return "Other"


def categorize_transactions(df):
    """Add category column to a copy of the DataFrame."""
    df = df.copy()
    df["category"] = df["description"].apply(categorize_transaction)
    return df


def calculate_metrics(df, emergency_fund_amount=0.0, monthly_expenses=None):
    """
    Compute the full financial metrics dictionary from a transactions DataFrame.
    emergency_fund_amount: user-provided savings balance in dollars.
    monthly_expenses: user-provided monthly expense estimate (used for emergency months calc).
    """
    if df is None or df.empty:
        return {}

    df = categorize_transactions(df)

    income_mask = df["category"] == "Income"
    income_df = df[income_mask & (df["type"] == "credit")]
    total_income = float(income_df["amount"].sum())

    # Also catch large credits in checking that may be income (direct deposits etc.)
    if total_income == 0:
        large_credits = df[(df["type"] == "credit") & (~df["category"].isin(["Transfer"]))]
        total_income = float(large_credits["amount"].sum())

    spending_mask = (df["type"] == "debit") & (~df["category"].isin(["Transfer", "Income"]))
    spending_df = df[spending_mask]
    total_spending = float(spending_df["amount"].sum())

    savings_amount = total_income - total_spending
    savings_rate = (savings_amount / total_income * 100) if total_income > 0 else 0.0

    category_totals = (
        spending_df.groupby("category")["amount"].sum()
        .sort_values(ascending=False)
        .to_dict()
    )
    category_totals = {k: float(v) for k, v in category_totals.items() if v > 0}

    category_percentages = {}
    if total_spending > 0:
        category_percentages = {
            k: float(v / total_spending * 100) for k, v in category_totals.items()
        }

    top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:3]

    desc_counts = df["description"].value_counts()
    recurring_charges = []
    for desc, count in desc_counts[desc_counts > 1].items():
        rows = df[df["description"] == desc]
        recurring_charges.append({
            "description": desc,
            "count": int(count),
            "total": float(rows["amount"].sum()),
            "avg": float(rows["amount"].mean()),
        })
    recurring_charges = sorted(recurring_charges, key=lambda x: x["total"], reverse=True)[:10]

    atm_df = df[df["category"] == "ATM & Cash"]
    fee_df = df[df["category"] == "Bank Fees"]
    foreign_df = df[df.get("is_foreign", pd.Series(False, index=df.index))] if "is_foreign" in df.columns else pd.DataFrame()

    atm_total = float(atm_df["amount"].sum())
    fee_total = float(fee_df["amount"].sum())
    foreign_total = float(foreign_df["amount"].sum()) if not foreign_df.empty else 0.0

    spending_spikes = {}
    daily_totals = {}

    try:
        df_dated = df.copy()
        df_dated["date_parsed"] = pd.to_datetime(df["date"], infer_datetime_format=True, errors="coerce")
        valid_dated = df_dated.dropna(subset=["date_parsed"])

        if not valid_dated.empty:
            spend_dated = valid_dated[spending_mask.reindex(valid_dated.index, fill_value=False)]
            if not spend_dated.empty:
                spend_dated = spend_dated.copy()
                spend_dated["dow"] = spend_dated["date_parsed"].dt.day_name()
                spend_dated["date_only"] = spend_dated["date_parsed"].dt.date

                daily_sums = spend_dated.groupby("date_only")["amount"].sum()
                avg_daily = float(daily_sums.mean()) if not daily_sums.empty else 0
                daily_totals = {str(k): float(v) for k, v in daily_sums.items()}

                dow_avg = spend_dated.groupby("dow")["amount"].mean()
                for day, avg in dow_avg.items():
                    if avg_daily > 0 and float(avg) > avg_daily * 1.30:
                        spending_spikes[day] = float(avg)
    except Exception:
        pass

    debt_keywords = r"loan payment|mortgage|student loan|auto loan|car payment|credit card payment|minimum payment"
    debt_df = df[df["description"].str.lower().str.contains(debt_keywords, regex=True, na=False)]
    debt_total = float(debt_df[debt_df["type"] == "debit"]["amount"].sum())

    effective_monthly = monthly_expenses if (monthly_expenses and monthly_expenses > 0) else total_spending
    emergency_months = float(emergency_fund_amount / effective_monthly) if effective_monthly > 0 else 0.0

    paycheck_to_paycheck = savings_rate < 5 and total_income > 0

    return {
        "total_income": total_income,
        "total_spending": total_spending,
        "savings_amount": savings_amount,
        "savings_rate": savings_rate,
        "category_totals": category_totals,
        "category_percentages": category_percentages,
        "top_categories": [(k, float(v)) for k, v in top_categories],
        "recurring_charges": recurring_charges,
        "atm_total": atm_total,
        "atm_count": int(len(atm_df)),
        "fee_total": fee_total,
        "foreign_total": foreign_total,
        "spending_spikes": spending_spikes,
        "daily_totals": daily_totals,
        "debt_total": debt_total,
        "emergency_months": emergency_months,
        "emergency_fund_amount": float(emergency_fund_amount),
        "monthly_expenses": float(effective_monthly),
        "paycheck_to_paycheck": bool(paycheck_to_paycheck),
        "transaction_count": int(len(df)),
    }


def calculate_health_score(metrics, emergency_months=None):
    """
    Compute health score 1-100 and a score breakdown dict.
    emergency_months overrides what's in metrics if provided.
    """
    em = emergency_months if emergency_months is not None else metrics.get("emergency_months", 0)
    savings_rate = metrics.get("savings_rate", 0)
    total_income = metrics.get("total_income", 0)
    debt_total = metrics.get("debt_total", 0)
    category_percentages = metrics.get("category_percentages", {})

    # Savings rate (30 pts)
    if savings_rate > 20:
        savings_score = 30
    elif savings_rate >= 10:
        savings_score = 20
    elif savings_rate >= 1:
        savings_score = 10
    else:
        savings_score = 0

    # Emergency fund (25 pts)
    if em >= 6:
        em_score = 25
    elif em >= 3:
        em_score = 20
    elif em >= 1:
        em_score = 10
    else:
        em_score = 0

    # Debt load (25 pts)
    if total_income > 0:
        debt_pct = (debt_total / total_income) * 100
    else:
        debt_pct = 0

    if debt_total == 0 or debt_pct == 0:
        debt_score = 25
    elif debt_pct < 20:
        debt_score = 15
    elif debt_pct <= 40:
        debt_score = 5
    else:
        debt_score = 0

    # Spending consistency (20 pts)
    over_40 = sum(1 for pct in category_percentages.values() if pct > 40)
    if over_40 == 0:
        consistency_score = 20
    elif over_40 == 1:
        consistency_score = 10
    else:
        consistency_score = 0

    total = savings_score + em_score + debt_score + consistency_score
    total = min(total, 100)

    breakdown = {
        "savings_rate": savings_score,
        "emergency_fund": em_score,
        "debt_load": debt_score,
        "spending_consistency": consistency_score,
    }
    return total, breakdown


def compare_months(dfs_by_month):
    """
    Given a dict of {month_label: DataFrame}, return comparison data.
    Returns (comparison_df, trends_dict)
    """
    records = []
    for label, df in sorted(dfs_by_month.items()):
        metrics = calculate_metrics(df)
        row = {"month": label, "total_spending": metrics.get("total_spending", 0)}
        row.update(metrics.get("category_totals", {}))
        records.append(row)

    if not records:
        return pd.DataFrame(), {}

    comp_df = pd.DataFrame(records).fillna(0)

    trends = {}
    if len(comp_df) >= 2:
        all_cats = [c for c in comp_df.columns if c not in ("month", "total_spending")]
        for cat in all_cats:
            values = comp_df[cat].tolist()
            if len(values) >= 2:
                consecutive_increases = 0
                for i in range(1, len(values)):
                    if values[i] > values[i - 1]:
                        consecutive_increases += 1
                    else:
                        consecutive_increases = 0
                if consecutive_increases >= 2:
                    trends[cat] = "creeping_up"

    return comp_df, trends
