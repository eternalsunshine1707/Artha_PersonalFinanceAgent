import os
import re
import anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = (
    "You are Artha, a personal finance agent. Your personality is brutally honest, "
    "non-judgmental, witty when the situation calls for it, and you talk like a financially "
    "smart friend, not a corporate financial advisor. You never use financial jargon. "
    "You speak in plain conversational English. You never shame the user. You acknowledge "
    "hard truths before giving solutions. You celebrate genuine wins without being cheesy. "
    "You always prioritize in this order: stop the bleeding first, build a safety net second, "
    "grow money third. You never mention investing until the user has at least 3 months of "
    "emergency fund and no high interest debt. Your job is to give the user one clear honest "
    "picture of their finances and one clear path forward."
)

SECTION_KEYS = [
    "ARTHAS_TAKE",
    "WHATS_DRAINING_YOU",
    "SPENDING_LOOP_ALERT",
    "ONE_THING_TO_FIX",
    "WHAT_IF",
    "FINANCIAL_PRIORITY",
]


def get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not found.\n\n"
            "To fix this:\n"
            "1. Create a file named .env inside the artha/ folder\n"
            "2. Add this line: ANTHROPIC_API_KEY=your_key_here\n"
            "3. Get your API key at: https://console.anthropic.com\n"
            "4. Restart the app with: streamlit run app.py"
        )
    return anthropic.Anthropic(api_key=api_key)


def _build_metrics_text(metrics):
    lines = [
        "FINANCIAL SUMMARY",
        f"  Total Income:      ${metrics.get('total_income', 0):.2f}",
        f"  Total Spending:    ${metrics.get('total_spending', 0):.2f}",
        f"  Savings:           ${metrics.get('savings_amount', 0):.2f}",
        f"  Savings Rate:      {metrics.get('savings_rate', 0):.1f}%",
        f"  Emergency Fund:    {metrics.get('emergency_months', 0):.1f} months",
        f"  Debt Payments:     ${metrics.get('debt_total', 0):.2f}",
        f"  ATM/Cash:          ${metrics.get('atm_total', 0):.2f} ({metrics.get('atm_count', 0)} transactions)",
        f"  Bank Fees:         ${metrics.get('fee_total', 0):.2f}",
        "",
        "SPENDING BY CATEGORY",
    ]

    cat_totals = sorted(
        metrics.get("category_totals", {}).items(), key=lambda x: x[1], reverse=True
    )
    for cat, amt in cat_totals:
        pct = metrics.get("category_percentages", {}).get(cat, 0)
        lines.append(f"  {cat:<28} ${amt:>8.2f}  ({pct:.1f}%)")

    top = metrics.get("top_categories", [])
    if top:
        lines.append("")
        lines.append("TOP 3 SPENDING AREAS")
        for cat, amt in top:
            lines.append(f"  {cat}: ${amt:.2f}")

    recurring = metrics.get("recurring_charges", [])
    if recurring:
        lines.append("")
        lines.append("RECURRING CHARGES (appear >1x)")
        for r in recurring[:6]:
            lines.append(f"  {r['description'][:40]}: {r['count']}x — avg ${r['avg']:.2f}, total ${r['total']:.2f}")

    spikes = metrics.get("spending_spikes", {})
    if spikes:
        lines.append("")
        lines.append("SPENDING SPIKES BY DAY (30%+ above average)")
        for day, avg in spikes.items():
            lines.append(f"  {day}: avg ${avg:.2f}")

    if metrics.get("paycheck_to_paycheck"):
        lines.append("")
        lines.append("NOTE: Paycheck-to-paycheck pattern detected (savings rate < 5%)")

    return "\n".join(lines)


def run_analysis(metrics, health_score, mood="neutral"):
    """
    Send financial data to Claude and return parsed analysis sections dict.
    Keys: arthas_take, whats_draining_you, spending_loop_alert,
          one_thing_to_fix, what_if, financial_priority
    """
    client = get_client()
    metrics_text = _build_metrics_text(metrics)

    mood_line = {
        "stressed": (
            "The user said they are STRESSED about their finances. "
            "Open with extra warmth. Normalize the feeling. Acknowledge that many people are in this spot "
            "before you dive into the numbers. Don't skip the empathy."
        ),
        "okay": (
            "The user said they feel OKAY about their finances. Be warm but direct and efficient."
        ),
        "neutral": "The user said they feel NEUTRAL about their finances.",
    }.get(mood, "The user feels NEUTRAL about their finances.")

    prompt = f"""{metrics_text}

HEALTH SCORE: {health_score}/100

{mood_line}

Provide your analysis in EXACTLY this format, using the exact section tags below. Do not add any text before the first tag or after the last section.

[ARTHAS_TAKE]
3-5 sentences. Honest overall picture in your voice. Reference specific dollar numbers and specific patterns you see. Not generic. Not a list.

[WHATS_DRAINING_YOU]
Specific breakdown of the top money drains. Use exact dollar amounts. Give context about why each matters. Be direct.

[SPENDING_LOOP_ALERT]
If you see an emotional spending pattern — spikes on specific days, food delivery or shopping trending up — call it out warmly and specifically. Name the day and category. If no strong pattern, say briefly what to watch for.

[ONE_THING_TO_FIX]
ONE specific actionable change for this month. Not a list. Exactly one thing. Make it concrete with a specific dollar target or specific action step.

[WHAT_IF]
One what-if scenario for the biggest spending category. Show the exact math: "If you cut [X] to [Y] times per week, that's $Z per month and $W per year back in your pocket."

[FINANCIAL_PRIORITY]
Based on the health score and data, name the single most important financial priority right now — emergency fund, debt payoff, or savings rate. Explain why briefly. Do NOT mention investing unless emergency fund is over 3 months and there is no high-interest debt visible.

Use plain English. Reference specific numbers from the data. Be Artha."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    return _parse_sections(raw)


def chat_with_artha(message, metrics, chat_history):
    """
    Send a user chat message to Claude with full context and return the response string.
    chat_history: list of {"role": "user"|"assistant", "content": str}
    """
    client = get_client()
    metrics_text = _build_metrics_text(metrics)

    context = (
        f"The user's financial data for this conversation:\n\n{metrics_text}\n\n"
        "Answer based specifically on their actual data. Be Artha."
    )

    messages = [
        {"role": "user", "content": context},
        {"role": "assistant", "content": "Got it — I have your full financial picture. What would you like to know?"},
    ]

    for msg in chat_history[-12:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": message})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    )
    return response.content[0].text


def _parse_sections(text):
    """Extract sections from the [MARKER] ... [NEXT_MARKER] format."""
    sections = {
        "arthas_take": "",
        "whats_draining_you": "",
        "spending_loop_alert": "",
        "one_thing_to_fix": "",
        "what_if": "",
        "financial_priority": "",
    }

    key_map = {
        "ARTHAS_TAKE": "arthas_take",
        "WHATS_DRAINING_YOU": "whats_draining_you",
        "SPENDING_LOOP_ALERT": "spending_loop_alert",
        "ONE_THING_TO_FIX": "one_thing_to_fix",
        "WHAT_IF": "what_if",
        "FINANCIAL_PRIORITY": "financial_priority",
    }

    pattern = r"\[(" + "|".join(SECTION_KEYS) + r")\](.*?)(?=\[(?:" + "|".join(SECTION_KEYS) + r")\]|\Z)"
    matches = re.findall(pattern, text, re.DOTALL)

    for marker, content in matches:
        key = key_map.get(marker)
        if key:
            sections[key] = content.strip()

    if not any(sections.values()):
        sections["arthas_take"] = text.strip()

    return sections
