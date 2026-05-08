from fpdf import FPDF
from datetime import datetime


NAVY = (27, 42, 74)
GREEN = (26, 127, 75)
RED = (163, 45, 45)
GREY = (102, 102, 102)
LIGHT_GREY = (224, 224, 224)
WHITE = (255, 255, 255)
DARK_TEXT = (50, 50, 50)


class _ArthaPDF(FPDF):
    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(
            0, 8,
            f"Page {self.page_no()}/{{nb}}  |  Artha Personal Finance  |  {datetime.now().strftime('%B %d, %Y')}",
            align="C",
        )


def export_to_pdf(analysis, metrics, health_score=0, chat_history=None, include_chat=False):
    """
    Build and return a PDF report as bytes.
    analysis: dict with keys arthas_take, whats_draining_you, etc.
    metrics: dict from analyzer.calculate_metrics()
    """
    pdf = _ArthaPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # ── Header ──────────────────────────────────────────────────────────
    pdf.set_fill_color(*NAVY)
    pdf.rect(12, 12, 22, 22, "F")
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(12, 14)
    pdf.cell(22, 18, "A", align="C")

    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*NAVY)
    pdf.set_xy(38, 13)
    pdf.cell(80, 13, "Artha", align="L")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GREY)
    pdf.set_xy(38, 26)
    pdf.cell(100, 8, "Your money has a story. Artha reads it!", align="L")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GREY)
    pdf.set_xy(140, 17)
    pdf.cell(58, 8, f"Generated {datetime.now().strftime('%B %d, %Y')}", align="R")

    pdf.set_draw_color(*LIGHT_GREY)
    pdf.line(12, 38, 198, 38)
    pdf.ln(32)

    # ── Financial Summary ────────────────────────────────────────────────
    _section_heading(pdf, "Financial Summary")

    summary_rows = [
        ("Total Income", f"${metrics.get('total_income', 0):.2f}", GREEN),
        ("Total Spending", f"${metrics.get('total_spending', 0):.2f}", RED),
        (
            "Savings",
            f"${metrics.get('savings_amount', 0):.2f}",
            GREEN if metrics.get("savings_amount", 0) >= 0 else RED,
        ),
        ("Savings Rate", f"{metrics.get('savings_rate', 0):.1f}%", None),
        ("Emergency Fund", f"{metrics.get('emergency_months', 0):.1f} months", None),
        ("Bank Fees Paid", f"${metrics.get('fee_total', 0):.2f}", RED if metrics.get("fee_total", 0) > 0 else None),
        ("Health Score", f"{health_score} / 100", None),
    ]

    for label, value, color in summary_rows:
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*GREY)
        pdf.cell(80, 7, label + ":", align="L")
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*(color if color else NAVY))
        pdf.cell(0, 7, value, ln=True)

    pdf.ln(4)
    _divider(pdf)

    # ── Analysis Sections ────────────────────────────────────────────────
    section_titles = {
        "arthas_take": "Artha's Take",
        "whats_draining_you": "What's Draining You",
        "spending_loop_alert": "Spending Loop Alert",
        "one_thing_to_fix": "One Thing to Fix This Month",
        "what_if": "What If...",
        "financial_priority": "Your Financial Priority Right Now",
    }

    for key, title in section_titles.items():
        content = (analysis or {}).get(key, "")
        if not content:
            continue
        _section_heading(pdf, title)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*DARK_TEXT)
        pdf.multi_cell(0, 6, content)
        pdf.ln(3)

    # ── Spending Breakdown ───────────────────────────────────────────────
    cat_totals = metrics.get("category_totals", {})
    if cat_totals:
        if pdf.get_y() > 220:
            pdf.add_page()

        _section_heading(pdf, "Spending Breakdown by Category")
        for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
            if amt <= 0:
                continue
            pct = metrics.get("category_percentages", {}).get(cat, 0)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*GREY)
            pdf.cell(80, 6, cat, align="L")
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*NAVY)
            pdf.cell(35, 6, f"${amt:.2f}", align="L")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*GREY)
            pdf.cell(0, 6, f"({pct:.1f}%)", ln=True)
        pdf.ln(4)

    # ── Recurring Charges ────────────────────────────────────────────────
    recurring = metrics.get("recurring_charges", [])
    if recurring:
        if pdf.get_y() > 220:
            pdf.add_page()
        _section_heading(pdf, "Recurring Charges")
        for r in recurring[:8]:
            desc = r["description"][:42]
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*GREY)
            pdf.cell(90, 6, desc, align="L")
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*NAVY)
            pdf.cell(30, 6, f"${r['avg']:.2f}/mo", align="L")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*GREY)
            pdf.cell(0, 6, f"{r['count']}x this period", ln=True)
        pdf.ln(4)

    # ── Chat History ─────────────────────────────────────────────────────
    if include_chat and chat_history:
        pdf.add_page()
        _section_heading(pdf, "Chat History with Artha")
        for msg in chat_history:
            is_user = msg["role"] == "user"
            label = "You" if is_user else "Artha"
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*GREY if is_user else NAVY)
            pdf.cell(0, 7, label + ":", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*DARK_TEXT)
            pdf.multi_cell(0, 6, msg["content"])
            pdf.ln(3)

    return bytes(pdf.output())


def export_to_text(analysis, metrics, health_score=0, chat_history=None, include_chat=False):
    """Build and return a plain-text report as a UTF-8 string."""
    W = 60
    hr = "=" * W
    thin = "-" * W

    lines = [
        hr,
        "ARTHA — Personal Finance Analysis",
        "Your money has a story. Artha reads it!",
        f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        hr,
        "",
        "FINANCIAL SUMMARY",
        thin,
        f"  Total Income     : ${metrics.get('total_income', 0):.2f}",
        f"  Total Spending   : ${metrics.get('total_spending', 0):.2f}",
        f"  Savings          : ${metrics.get('savings_amount', 0):.2f}",
        f"  Savings Rate     : {metrics.get('savings_rate', 0):.1f}%",
        f"  Emergency Fund   : {metrics.get('emergency_months', 0):.1f} months",
        f"  Bank Fees Paid   : ${metrics.get('fee_total', 0):.2f}",
        f"  Health Score     : {health_score} / 100",
        "",
    ]

    section_titles = {
        "arthas_take": "ARTHA'S TAKE",
        "whats_draining_you": "WHAT'S DRAINING YOU",
        "spending_loop_alert": "SPENDING LOOP ALERT",
        "one_thing_to_fix": "ONE THING TO FIX THIS MONTH",
        "what_if": "WHAT IF...",
        "financial_priority": "YOUR FINANCIAL PRIORITY RIGHT NOW",
    }

    for key, title in section_titles.items():
        content = (analysis or {}).get(key, "")
        if not content:
            continue
        lines += [title, thin, content, ""]

    cat_totals = metrics.get("category_totals", {})
    if cat_totals:
        lines += ["SPENDING BREAKDOWN", thin]
        for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
            if amt > 0:
                pct = metrics.get("category_percentages", {}).get(cat, 0)
                lines.append(f"  {cat:<28} ${amt:>8.2f}   ({pct:.1f}%)")
        lines.append("")

    recurring = metrics.get("recurring_charges", [])
    if recurring:
        lines += ["RECURRING CHARGES", thin]
        for r in recurring[:8]:
            lines.append(f"  {r['description'][:40]:<40} {r['count']}x   avg ${r['avg']:.2f}")
        lines.append("")

    if include_chat and chat_history:
        lines += [hr, "CHAT HISTORY", hr, ""]
        for msg in chat_history:
            label = "You" if msg["role"] == "user" else "Artha"
            lines += [f"{label}:", msg["content"], ""]

    lines += [
        hr,
        "Generated by Artha | Ran 100% locally on your device.",
        "Your data was only sent to Anthropic's API for analysis.",
        "Nothing is stored on any server.",
        hr,
    ]

    return "\n".join(lines)


# ── Helpers ────────────────────────────────────────────────────────────────


def _section_heading(pdf, title):
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 9, title, ln=True)
    pdf.set_draw_color(*LIGHT_GREY)
    pdf.line(pdf.get_x(), pdf.get_y(), 198, pdf.get_y())
    pdf.ln(3)


def _divider(pdf):
    pdf.set_draw_color(*LIGHT_GREY)
    pdf.line(12, pdf.get_y(), 198, pdf.get_y())
    pdf.ln(5)
