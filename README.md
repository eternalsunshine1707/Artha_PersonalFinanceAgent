# Artha - Your Personal Finance Agent!

> Your money has a story. Artha reads it!

Most finance apps throw charts at you and call it a day. Artha actually talks to you. Upload your bank statement and Artha tells you where your money went, what is quietly draining you every month, and the one thing worth fixing right now. No jargon, no lectures, just honesty from something that sounds like a financially smart friend.


## What it does!?

Artha reads your PDF bank statements locally on your machine and gives you a real picture of your finances. It finds forgotten subscriptions you stopped using, flags spending that spikes on specific days, detects if you are living paycheck to paycheck, and tells you how many months you could survive if your income stopped tomorrow. Then it gives you one number, one fix, and lets you keep asking follow up questions in plain English.

Supports checking accounts and credit cards. Supports multiple banks at once. Supports month over month comparison if you upload more than one statement.


## Your data stays with you :)

Nothing leaves your device. Artha never uploads your statements to any server. The only external call is to the Claude API for the analysis, and only your transaction data goes there, not your name, account number, or any identifying details. No account creation, no cloud storage, no tracking.


## Getting started!

You need Python 3.9 or above and a free Anthropic API key. Get one at [console.anthropic.com](https://console.anthropic.com) in about two minutes.

```bash
git clone https://github.com/yourusername/artha.git
cd artha
pip install -r requirements.txt
cp .env.example .env
```

Open the `.env` file and replace `your_api_key_here` with your actual Anthropic API key. Then run:

```bash
streamlit run app.py
```

Artha opens in your browser. That is the whole setup.


## What does it cost to run!?

Each analysis costs roughly $0.01 to $0.05 depending on how many transactions are in your statement. Anthropic gives free credits when you first sign up so your initial testing will likely cost nothing. Track your exact usage at [console.anthropic.com](https://console.anthropic.com) under the Usage tab.


## Supported formats

PDF statements from checking accounts and credit cards. Most major US banks work out of the box. If your bank sends password protected PDFs, remove the password before uploading. Artha will walk you through it if it detects one.


## Tech stack

Python and Streamlit for the app, Claude API as the agent brain, pdfplumber for reading PDFs, Pandas for processing transactions, and Plotly for the charts.


## What is coming next!?

Artha is currently a local tool you run on your own machine. The plan is to turn this into a fully deployed web app so anyone can use it without any setup. No cloning, no terminal, no API key hassle. Just open a link and go. Stay tuned.


## Repo structure
```
artha/
├── app.py              main Streamlit app
├── parser.py           PDF parsing and transaction extraction
├── analyzer.py         categorization, metrics, health score
├── agent.py            Claude API integration and analysis
├── exporter.py         PDF and text export
├── .env.example        API key template
└── requirements.txt
```

## A few things worth mentioning!

The transaction data Artha produces is clean and structured, so it could technically feed into a Power BI dashboard if you wanted that kind of visual reporting layer. That is not something being built into Artha itself since the Streamlit interface already handles it, but the data is ready for it if you ever want to take it that direction.
On the LLM side, Artha runs on Claude and that was a deliberate choice. You could swap in ChatGPT or another model since the agent logic is not tied to any specific provider, but toggling between two models creates inconsistency in tone and output, which defeats the whole point of Artha having a consistent personality. So Claude it is.


## Contributing

Open source and open to contributions. If you run into a bank format that does not parse correctly or have a feature idea, open an issue or send a PR.