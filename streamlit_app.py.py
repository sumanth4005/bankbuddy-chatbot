import re
import time

import pandas as pd
import streamlit as st
from google import genai
from google.genai import errors, types
from sentence_transformers import SentenceTransformer, util

st.set_page_config(page_title="BankBuddy – Demo Bank Assistant", page_icon="🏦")

# ---------- FAQ DATA ----------
# Format: (category, [ways customers ask], answer)
FAQ_DATA = [
    # ---------- CARDS ----------
    ("cards", ["How do I report a lost or stolen debit card?", "I lost my card", "My debit card was stolen"],
     "Lock your card instantly in the mobile app under Card Settings, then call 1-800-555-0100 to order a replacement. New cards arrive in 3-5 business days."),
    ("cards", ["How do I activate my new debit card?", "Activate card", "I got a new card in the mail"],
     "Activate your card in the mobile app under Card Settings > Activate Card, or call the number on the sticker on your card. You can also activate it by making a PIN purchase at an ATM."),
    ("cards", ["How do I change my debit card PIN?", "Reset my PIN", "I forgot my card PIN"],
     "You can change your PIN at any Demo Bank ATM or in the mobile app under Card Settings > Change PIN. If you forgot it, you can set a new one in the app after verifying your identity."),
    ("cards", ["How do I lock or unlock my card?", "Freeze my card temporarily", "I found my card, how do I unlock it?"],
     "In the mobile app, go to Card Settings and toggle Lock Card on or off. Locking stops new purchases instantly, and you can unlock it anytime."),
    ("cards", ["Why was my card declined?", "My card isn't working", "Card got rejected at the store"],
     "Common reasons are insufficient funds, a locked card, reaching your daily spending limit, or a fraud alert. Check the app for alerts, or call 1-800-555-0100 for help."),
    ("cards", ["How do I tell the bank I'm traveling?", "Travel notice", "Will my card work abroad?"],
     "Travel notices aren't required, since our fraud system recognizes travel patterns. Make sure your phone number is up to date so we can reach you, and note that foreign transactions have a 3% fee."),
    ("cards", ["What is my daily debit card spending limit?", "Card purchase limit", "How much can I spend per day with my card?"],
     "The standard daily purchase limit is $3,000 and the daily ATM withdrawal limit is $500. You can view your limits in the app under Card Settings."),

    # ---------- FEES ----------
    ("fees", ["How can I avoid the monthly service fee?", "How do I not pay the monthly charge?", "Waive monthly fee"],
     "The $12 monthly fee is waived if you keep a minimum daily balance of $1,500 or receive direct deposits of $500 or more per month."),
    ("fees", ["What is the overdraft fee?", "How much is an overdraft charge?", "I overdrew my account"],
     "The overdraft fee is $34 per item, with a maximum of 3 fees per day. No fee is charged if your account is overdrawn by $50 or less at the end of the day."),
    ("fees", ["How do I avoid overdraft fees?", "Overdraft protection", "Link savings to checking"],
     "Link a savings account for overdraft protection so funds transfer automatically with no fee, and set up low-balance alerts in the app."),
    ("fees", ["Can I get a fee refunded?", "Refund a fee", "Can you reverse the charge on my account?"],
     "Fee refunds are reviewed case by case. Please contact an agent at 1-800-555-0100 or through secure chat in the app."),
    ("fees", ["Is there a fee for foreign transactions?", "International purchase fee", "Fee for using my card abroad"],
     "Yes, purchases in a foreign currency or processed outside the U.S. have a 3% foreign transaction fee."),

    # ---------- ATM ----------
    ("atm", ["Are there fees for using another bank's ATM?", "Out of network ATM fee", "How much does it cost to use a different ATM?"],
     "Out-of-network ATMs charge $3 per withdrawal in the U.S. and $5 internationally, plus any fee the ATM owner charges."),
    ("atm", ["How do I find a nearby ATM?", "ATM near me", "Where is the closest branch?"],
     "Use the ATM & Branch Locator in the mobile app or on our website to find locations, hours, and services near you."),
    ("atm", ["The ATM kept my card", "ATM swallowed my card", "My card is stuck in the ATM"],
     "Lock your card in the app right away for safety, then call 1-800-555-0100. We'll cancel the card and send a replacement in 3-5 business days."),
    ("atm", ["The ATM didn't give me cash but charged my account", "ATM took my money", "Wrong amount from ATM"],
     "Sorry about that. Please report it in the app under Transaction Details > Dispute, or call us. These are usually resolved within 10 business days."),

    # ---------- TRANSFERS & ZELLE ----------
    ("transfers", ["What is the daily Zelle sending limit?", "Zelle limit", "How much can I send with Zelle?"],
     "The standard Zelle limit is $2,000 per day and $10,000 per month. Check your exact limits in the app under Pay & Transfer > Zelle > Limits."),
    ("transfers", ["I sent Zelle money to the wrong person", "Wrong Zelle recipient", "Can I cancel a Zelle payment?"],
     "Zelle payments to enrolled users usually can't be canceled once sent. If the recipient isn't enrolled yet, you can cancel in the app. Otherwise, contact the recipient directly, or call us if you think it was a scam."),
    ("transfers", ["How do I send a wire transfer?", "Domestic wire", "Send money by wire"],
     "Send wires in the app under Pay & Transfer > Wires, or visit a branch. Domestic wires cost $25 and international wires cost $40."),
    ("transfers", ["How long does a transfer between my accounts take?", "Internal transfer time", "Move money between checking and savings"],
     "Transfers between your Demo Bank accounts are instant when made before 11 PM ET."),
    ("transfers", ["How do I transfer money to another bank?", "External transfer", "Send money to my account at another bank"],
     "Link your external account in the app under Pay & Transfer > External Accounts. Standard transfers take 1-3 business days."),

    # ---------- ACCOUNTS ----------
    ("accounts", ["Where do I find my routing number?", "What's the bank routing number?", "Routing number for direct deposit"],
     "Your routing number is shown in the app under Account Details, and at the bottom left of your checks."),
    ("accounts", ["How do I open a new account?", "Open checking account", "I want to open a savings account"],
     "You can open an account online in about 10 minutes or visit any branch. You'll need a government-issued ID and your Social Security number."),
    ("accounts", ["How do I close my account?", "Close my checking account", "I want to cancel my account"],
     "To close an account, call 1-800-555-0100 or visit a branch. Make sure all pending transactions have cleared first."),
    ("accounts", ["What is the savings account interest rate?", "Savings APY", "How much interest does savings earn?"],
     "Savings rates change regularly. Check the current rates on our website or in the app under Explore Products."),
    ("accounts", ["How do I add a joint owner to my account?", "Add someone to my account", "Joint account"],
     "Both people need to visit a branch together with government-issued IDs to add a joint owner."),
    ("accounts", ["How do I update my address or phone number?", "Change my address", "Update contact info"],
     "Update your contact information in the app under Profile & Settings. Changes take effect immediately."),

    # ---------- DEPOSITS ----------
    ("deposits", ["How do I deposit a check with my phone?", "Mobile check deposit", "Deposit a check in the app"],
     "In the app, tap Deposit Checks, sign the back of the check and write 'For mobile deposit only,' then take photos of the front and back."),
    ("deposits", ["When will my deposited check be available?", "Check hold", "Why is my deposit on hold?"],
     "Most check deposits are available the next business day. Larger checks or new accounts may have a hold of up to 5 business days, and you'll be notified if that happens."),
    ("deposits", ["How do I set up direct deposit?", "Direct deposit form", "Get my paycheck deposited"],
     "Download a pre-filled direct deposit form in the app under Account Services > Direct Deposit, and give it to your employer."),
    ("deposits", ["What is the mobile deposit limit?", "How much can I deposit with my phone?", "Mobile deposit maximum"],
     "The standard mobile deposit limit is $5,000 per day and $10,000 per month."),
    ("deposits", ["When does direct deposit arrive?", "My paycheck hasn't shown up", "Direct deposit timing"],
     "Direct deposits usually post by the morning of payday. If yours is missing, confirm with your employer that the payment was sent and that the account details are correct."),

    # ---------- FRAUD & SECURITY ----------
    ("fraud", ["I see a charge I don't recognize. What should I do?", "Someone used my card without my permission", "Unauthorized transaction"],
     "Lock your card in the app right away and call our fraud line at 1-800-555-0199. You can dispute the charge in the app under Transaction Details > Dispute."),
    ("fraud", ["I got a suspicious text or call from the bank", "Is this text from Demo Bank real?", "Phishing email"],
     "Demo Bank will never ask for your password, PIN, or full card number by text, call, or email. Don't click links, and report it to our fraud line at 1-800-555-0199."),
    ("fraud", ["I think I was scammed", "Someone tricked me into sending money", "I paid a scammer"],
     "Please call our fraud line at 1-800-555-0199 immediately. Acting fast gives the best chance of recovering funds."),
    ("fraud", ["How do I set up account alerts?", "Transaction alerts", "Notify me of purchases"],
     "Set up alerts in the app under Profile & Settings > Alerts. You can get notified about purchases, low balances, and large transactions."),
    ("fraud", ["How do I dispute a charge?", "Dispute a transaction", "I was charged twice"],
     "Open the transaction in the app and tap Dispute, or call us. We usually provide a decision within 10 business days."),

    # ---------- ONLINE BANKING ----------
    ("online", ["I forgot my username or password", "Reset password", "Can't log into online banking"],
     "Tap 'Forgot username or password?' on the sign-in screen and follow the steps to verify your identity."),
    ("online", ["My online account is locked", "Too many login attempts", "Account locked out"],
     "For security, accounts lock after several failed sign-in attempts. Use 'Forgot username or password?' to unlock it, or call 1-800-555-0100."),
    ("online", ["How do I enroll in online banking?", "Sign up for online banking", "Create online account"],
     "Download the Demo Bank app or visit our website and tap Sign Up. You'll need your account or card number and Social Security number to verify your identity."),
    ("online", ["How do I get my bank statements?", "Download statement", "Where are my monthly statements?"],
     "View and download up to 7 years of statements in the app under Account Services > Statements & Documents."),
    ("online", ["How do I turn on two-factor authentication?", "Set up 2FA", "Extra login security"],
     "Turn on two-step verification in the app under Profile & Settings > Security."),

    # ---------- CHECKS ----------
    ("checks", ["How do I order checks?", "Order more checks", "I need new checks"],
     "Order checks in the app under Account Services > Order Checks, or at any branch."),
    ("checks", ["How do I stop payment on a check?", "Cancel a check", "Stop a check I wrote"],
     "Request a stop payment in the app under Account Services > Stop Payment. The fee is $30, and the check must not have been cashed yet."),

    # ---------- GENERAL ----------
    ("general", ["What are your branch hours?", "When is the bank open?", "Is the branch open on Saturday?"],
     "Most branches are open 9 AM-5 PM Monday through Friday and 9 AM-1 PM on Saturday. Check the exact hours in the app's Branch Locator."),
    ("general", ["How do I contact customer service?", "Customer service phone number", "Talk to a person"],
     "Call 1-800-555-0100, available 24/7, or use secure chat in the app."),
]

rows = []
for faq_id, (category, questions, answer) in enumerate(FAQ_DATA):
    for q in questions:
        rows.append({"faq_id": faq_id, "category": category, "question": q, "answer": answer})
faqs = pd.DataFrame(rows)


# ---------- LOAD MODELS ONCE (cached so they don't reload on every message) ----------
@st.cache_resource
def load_client():
    # The key is read from Streamlit's secret settings, never written in code
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


@st.cache_resource
def load_search():
    embedder = SentenceTransformer("all-mpnet-base-v2")
    embeddings = embedder.encode(faqs["question"].tolist(), convert_to_tensor=True)
    return embedder, embeddings


client = load_client()
embedder, faq_embeddings = load_search()


# ---------- SEMANTIC SEARCH ----------
def retrieve(question, top_k=5):
    q_emb = embedder.encode(question, convert_to_tensor=True)
    hits = util.semantic_search(q_emb, faq_embeddings, top_k=top_k)[0]
    return [(faqs.iloc[h["corpus_id"]], h["score"]) for h in hits]


# ---------- SAFETY RULES + GEMINI ----------
SENSITIVE = re.compile(r"\b\d{9,16}\b|ssn|social security|password|\bpin\b", re.I)

SYSTEM_PROMPT = """You are BankBuddy, a customer support assistant for Demo Bank.
Rules:
- Answer ONLY using the FAQ entries provided. Never invent fees, limits, or policies.
- If the FAQs don't answer the question, say: "I'm not sure about that. Let me connect you with an agent."
- Never ask for account numbers, SSNs, PINs, or passwords.
- For fraud or stolen cards, tell the customer to act immediately.
- Be friendly and concise (2-4 sentences)."""

SHOW_DEBUG = True  # temporary: shows the real error in the chat. Set to False when fixed.

# Tried in order: if one is busy or unavailable, the next one is used
MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]


def call_gemini(prompt):
    last_error = ""
    for model in MODELS:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.2,
                    ),
                )
                return response.text
            except errors.ServerError as e:  # 503 busy: wait, then retry
                last_error = f"{model}: {e}"
                print(f"[Gemini] {last_error}")
                time.sleep(2 * (attempt + 1))
            except Exception as e:  # bad key, model unavailable, quota, network: try next model
                last_error = f"{model}: {type(e).__name__}: {e}"
                print(f"[Gemini] {last_error}")
                break
    msg = "Sorry, our assistant is temporarily unavailable. Please try again shortly or contact an agent."
    if SHOW_DEBUG:
        msg += f"\n\n(Debug: {last_error[:300]})"
    return msg


def ask_bot(question):
    if SENSITIVE.search(question):
        return "⚠️ For your security, please never share account numbers, SSNs, PINs, or passwords in chat."

    results = retrieve(question, top_k=5)
    if results[0][1] < 0.35:
        return "I'm not sure about that. Let me connect you with an agent."

    seen, unique = set(), []
    for r, _ in results:
        if r["faq_id"] not in seen:
            seen.add(r["faq_id"])
            unique.append(r)

    context = "\n\n".join(f"Q: {r['question']}\nA: {r['answer']}" for r in unique)
    return call_gemini(f"FAQ entries:\n{context}\n\nCustomer question: {question}")


# ---------- WEB INTERFACE ----------
st.title("🏦 BankBuddy – Demo Bank Assistant")
st.caption(
    "Ask me about cards, fees, transfers, deposits, fraud, and online banking. "
    "This is a demo bot for a fictional bank: never share real account numbers, SSNs, PINs, or passwords."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Example question buttons
EXAMPLES = [
    "I lost my debit card",
    "How do I avoid the monthly fee?",
    "What is the Zelle limit?",
    "I got a suspicious text from the bank",
]
clicked = None
cols = st.columns(len(EXAMPLES))
for col, example in zip(cols, EXAMPLES):
    if col.button(example, use_container_width=True):
        clicked = example

# Show the conversation so far
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# New message from the input box or an example button
prompt = st.chat_input("Ask a banking question...") or clicked
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = ask_bot(prompt)
        st.write(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
