import pdfplumber
import pandas as pd
import re
import io
from datetime import datetime


def parse_pdf(uploaded_file):
    """
    Parse a bank statement PDF and return (DataFrame, error_message).
    Exactly one of them will be None.
    """
    filename = getattr(uploaded_file, "name", "unknown.pdf")

    try:
        if hasattr(uploaded_file, "getvalue"):
            pdf_bytes = uploaded_file.getvalue()
        elif hasattr(uploaded_file, "read"):
            pdf_bytes = uploaded_file.read()
        else:
            pdf_bytes = bytes(uploaded_file)

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            all_text = ""
            all_tables = []

            for page in pdf.pages:
                page_text = page.extract_text() or ""
                all_text += page_text + "\n"
                page_tables = page.extract_tables() or []
                all_tables.extend(page_tables)

        if not all_text.strip():
            return None, (
                f"Could not extract text from '{filename}'. "
                "The PDF may be a scanned image. Try downloading a text-based PDF directly from your bank's website."
            )

        statement_type = _detect_statement_type(all_text)
        bank_name = _detect_bank_name(all_text)
        month, year = _extract_month_year(all_text)

        transactions = _parse_transactions(all_text, all_tables, statement_type)

        if not transactions:
            return None, (
                f"Could not extract transactions from '{filename}'. "
                "Try downloading the statement directly from your bank's website as a PDF (not a scan)."
            )

        df = pd.DataFrame(transactions)

        for col in ["date", "description", "type"]:
            if col not in df.columns:
                df[col] = ""
        if "amount" not in df.columns:
            df["amount"] = 0.0

        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0).abs()
        df["statement_type"] = statement_type
        df["bank_name"] = bank_name
        df["month"] = month
        df["year"] = year
        df["category"] = ""
        df["is_atm"] = df["description"].str.lower().str.contains(
            r"atm|cash withdrawal|cash advance", regex=True, na=False
        )
        df["is_foreign"] = df["description"].str.lower().str.contains(
            r"foreign|international|\bfx\b|currency conversion", regex=True, na=False
        )

        return df, None

    except Exception as e:
        err = str(e).lower()
        if any(kw in err for kw in ["password", "encrypt", "protected", "decrypt", "pdfium"]):
            return None, (
                f"'{filename}' is password protected.\n\n"
                "To fix this:\n"
                "1. Open the PDF in Adobe Reader, Preview (Mac), or Chrome browser\n"
                "2. Go to File → Print\n"
                "3. Choose 'Save as PDF' as the destination/printer\n"
                "4. Save the new (unlocked) copy and upload that instead"
            )
        return None, (
            f"Could not parse '{filename}': {str(e)}\n"
            "Try exporting the statement as a different PDF format from your bank's website."
        )


def _detect_statement_type(text):
    text_lower = text.lower()
    credit_keywords = [
        "credit card", "credit limit", "minimum payment", "statement balance",
        "new charges", "rewards points", "cash back", "annual percentage rate",
        "apr", "minimum due", "payment due",
    ]
    checking_keywords = [
        "checking account", "savings account", "available balance",
        "beginning balance", "ending balance", "direct deposit",
        "overdraft", "routing number",
    ]
    credit_score = sum(1 for kw in credit_keywords if kw in text_lower)
    checking_score = sum(1 for kw in checking_keywords if kw in text_lower)
    return "credit_card" if credit_score > checking_score else "checking"


def _detect_bank_name(text):
    banks = {
        "Chase": ["chase bank", "jpmorgan chase", "chase.com"],
        "Bank of America": ["bank of america", "bankofamerica.com"],
        "Wells Fargo": ["wells fargo", "wellsfargo.com"],
        "Citi": ["citibank", "citi bank", "citi card", "citicorp"],
        "Capital One": ["capital one", "capitalone.com"],
        "US Bank": ["u.s. bank", "us bank", "usbank.com"],
        "TD Bank": ["td bank", "tdbank.com"],
        "PNC": ["pnc bank", "pncbank.com"],
        "American Express": ["american express", "amex.com"],
        "Discover": ["discover bank", "discover card", "discover.com"],
        "Ally": ["ally bank", "ally.com"],
        "USAA": ["usaa federal", "usaa.com"],
        "Navy Federal": ["navy federal credit union"],
        "SoFi": ["sofi bank", "sofi.com"],
        "Marcus": ["marcus by goldman sachs"],
        "Synchrony": ["synchrony bank", "synchronybank.com"],
        "Barclays": ["barclays bank", "barclaysus.com"],
    }
    text_lower = text.lower()
    for bank, keywords in banks.items():
        if any(kw in text_lower for kw in keywords):
            return bank
    return "Your Bank"


def _extract_month_year(text):
    months_map = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
        "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
        "oct": 10, "nov": 11, "dec": 12,
    }
    text_lower = text.lower()

    month_year_pattern = (
        r"\b(january|february|march|april|may|june|july|august|september|"
        r"october|november|december|jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)"
        r"[\s,]+(\d{4})\b"
    )
    match = re.search(month_year_pattern, text_lower)
    if match:
        month_name = match.group(1)
        year = int(match.group(2))
        if 2000 <= year <= 2035:
            return months_map.get(month_name, 1), year

    date_pattern = r"\b(\d{1,2})/\d{1,2}/(\d{4})\b"
    for m in re.finditer(date_pattern, text):
        month_num = int(m.group(1))
        year_num = int(m.group(2))
        if 1 <= month_num <= 12 and 2000 <= year_num <= 2035:
            return month_num, year_num

    now = datetime.now()
    return now.month, now.year


def _parse_transactions(text, tables, statement_type):
    if tables:
        table_txns = _parse_from_tables(tables, statement_type)
        if len(table_txns) >= 3:
            return table_txns

    text_txns = _parse_from_text(text, statement_type)
    return text_txns


def _parse_from_tables(tables, statement_type):
    transactions = []

    for table in tables:
        if not table or len(table) < 2:
            continue

        header_row = None
        data_start = 0

        for i, row in enumerate(table[:5]):
            if not row:
                continue
            row_text = " ".join(str(c).lower() for c in row if c)
            if any(kw in row_text for kw in ["date", "description", "amount", "debit", "credit", "transaction"]):
                header_row = row
                data_start = i + 1
                break

        if header_row is None:
            header_row = table[0]
            data_start = 1

        col_map = {}
        for i, cell in enumerate(header_row):
            if cell is None:
                continue
            h = str(cell).lower().strip()
            if re.search(r"\bdate\b", h) and "date" not in col_map:
                col_map["date"] = i
            elif re.search(r"description|memo|transaction|detail|merchant|payee|narrative", h):
                if "description" not in col_map:
                    col_map["description"] = i
            elif re.search(r"\bdebit\b|withdrawal|charge", h):
                col_map["debit"] = i
            elif re.search(r"\bcredit\b|deposit|payment", h):
                col_map["credit"] = i
            elif re.search(r"\bamount\b", h) and "amount" not in col_map:
                col_map["amount"] = i

        if "date" not in col_map or "description" not in col_map:
            continue

        for row in table[data_start:]:
            if not row or not any(c for c in row if c):
                continue
            try:
                date_val = str(row[col_map["date"]] or "").strip()
                desc_val = str(row[col_map["description"]] or "").strip()

                if not date_val or not re.search(r"\d", date_val) or not desc_val:
                    continue
                if any(kw in desc_val.lower() for kw in ["date", "description", "transaction", "balance"]):
                    continue

                amount = 0.0
                txn_type = "debit"

                if "debit" in col_map and col_map["debit"] < len(row):
                    debit_str = str(row[col_map["debit"]] or "").strip()
                    if debit_str and re.search(r"\d", debit_str):
                        amount = _clean_amount(debit_str)
                        if amount:
                            txn_type = "debit"

                if "credit" in col_map and col_map["credit"] < len(row):
                    credit_str = str(row[col_map["credit"]] or "").strip()
                    if credit_str and re.search(r"\d", credit_str):
                        credit_amount = _clean_amount(credit_str)
                        if credit_amount and (amount == 0 or credit_amount > 0):
                            amount = credit_amount
                            txn_type = "credit"

                if "amount" in col_map and amount == 0 and col_map["amount"] < len(row):
                    amount_str = str(row[col_map["amount"]] or "").strip()
                    amount = _clean_amount(amount_str)
                    if "-" in amount_str or "(" in amount_str:
                        txn_type = "debit"
                    else:
                        txn_type = "credit" if statement_type == "checking" else "debit"

                if amount == 0:
                    continue

                transactions.append({"date": date_val, "description": desc_val, "amount": abs(amount), "type": txn_type})

            except (IndexError, ValueError, TypeError):
                continue

    return transactions


def _parse_from_text(text, statement_type):
    transactions = []
    lines = text.split("\n")

    patterns = [
        r"^(\d{1,2}[/\-]\d{1,2}(?:[/\-]\d{2,4})?)\s+(.+?)\s{2,}([\-\+]?\$?[\d,]+\.\d{2})\s*$",
        r"^(\d{1,2}[/\-]\d{1,2}(?:[/\-]\d{2,4})?)\s+(.+?)\s+([\-\+]?\$?[\d,]+\.\d{2})\s*$",
        r"^([A-Z][a-z]{2}\.?\s+\d{1,2},?\s*\d{0,4})\s+(.+?)\s+([\-\+]?\$?[\d,]+\.\d{2})\s*$",
        r"^(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\s+(.+?)\s+([\-\+]?\$?[\d,]+\.\d{2})\s*$",
    ]

    skip_keywords = [
        "date", "description", "amount", "balance", "transaction", "debit", "credit",
        "opening", "closing", "beginning", "ending", "account number", "routing",
        "statement period", "page", "total",
    ]

    for line in lines:
        line = line.strip()
        if len(line) < 12:
            continue

        line_lower = line.lower()
        if any(kw in line_lower for kw in skip_keywords):
            has_dollar = bool(re.search(r"\$[\d,]+\.\d{2}", line))
            if not has_dollar:
                continue

        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                date_str = match.group(1).strip()
                desc = match.group(2).strip()
                amount_str = match.group(3).strip()

                if any(kw in desc.lower() for kw in skip_keywords):
                    break

                amount = _clean_amount(amount_str)
                if amount == 0:
                    break

                if "-" in amount_str or "(" in amount_str:
                    txn_type = "debit"
                else:
                    txn_type = "credit" if statement_type == "checking" else "debit"

                transactions.append({"date": date_str, "description": desc, "amount": abs(amount), "type": txn_type})
                break

    return transactions


def _clean_amount(amount_str):
    if not amount_str:
        return 0.0
    negative = "-" in amount_str or ("(" in amount_str and ")" in amount_str)
    cleaned = re.sub(r"[^\d.]", "", amount_str)
    if not cleaned:
        return 0.0
    try:
        val = float(cleaned)
        return -val if negative else val
    except ValueError:
        return 0.0
