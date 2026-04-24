
import re
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID")  # your Telegram numeric user ID as text
DB_PATH = os.getenv("DB_PATH", "/app/data/expenses.db")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    note TEXT,
    date TEXT NOT NULL
)
""")
conn.commit()

def detect_category(note: str) -> str:
    text = (note or "").lower()
    if any(x in text for x in ["food", "lunch", "dinner", "breakfast", "kopi", "coffee", "tea", "meal", "rice", "burger"]):
        return "Food"
    if any(x in text for x in ["grab", "mrt", "bus", "taxi", "train", "transport", "gocar", "gojek"]):
        return "Transport"
    if any(x in text for x in ["internet", "phone", "electric", "water", "bill", "utility", "utilities"]):
        return "Bills"
    if any(x in text for x in ["shop", "shopping", "lazada", "shopee", "fairprice", "ntuc", "groceries", "grocery"]):
        return "Shopping"
    return "Other"

def allowed(update: Update) -> bool:
    if ALLOWED_USER_ID is None:
        return True
    return str(update.effective_user.id) == str(ALLOWED_USER_ID)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    await update.message.reply_text(
        "Hi! Send expenses like:\n"
        "12.50 lunch\n"
        "45 grab\n"
        "120 internet bill\n\n"
        "Commands:\n"
        "/today - today's total\n"
        "/month - current month summary"
    )

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    user_id = update.effective_user.id
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT category, SUM(amount)
        FROM expenses
        WHERE user_id = ? AND date = ?
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (user_id, today_str))
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("No expenses logged for today.")
        return

    total = sum(row[1] for row in rows)
    lines = [f"📅 Today's expenses ({today_str})", ""]
    for category, amount in rows:
        lines.append(f"• {category}: SGD {amount:.2f}")
    lines.append("")
    lines.append(f"💰 Total: SGD {total:.2f}")
    await update.message.reply_text("\n".join(lines))

async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    user_id = update.effective_user.id
    month_str = datetime.now().strftime("%Y-%m")
    cursor.execute("""
        SELECT category, SUM(amount)
        FROM expenses
        WHERE user_id = ? AND date LIKE ?
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (user_id, f"{month_str}%"))
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("No expenses logged for this month yet.")
        return

    total = sum(row[1] for row in rows)
    lines = [f"📊 Monthly summary ({month_str})", ""]
    for category, amount in rows:
        lines.append(f"• {category}: SGD {amount:.2f}")
    lines.append("")
    lines.append(f"💰 Total: SGD {total:.2f}")
    await update.message.reply_text("\n".join(lines))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    text = (update.message.text or "").strip()

    # Expected format: "<amount> <note>"
    match = re.match(r"^([0-9]+(?:\\.[0-9]{1,2})?)\\s+(.+)$", text)
    if not match:
        await update.message.reply_text("Please send expenses like: 12.50 lunch")
        return

    amount = float(match.group(1))
    note = match.group(2).strip()
    category = detect_category(note)
    user_id = update.effective_user.id
    date_str = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        INSERT INTO expenses (user_id, amount, category, note, date)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, amount, category, note, date_str))
    conn.commit()

    await update.message.reply_text(f"✅ Added: SGD {amount:.2f} · {category}")

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("month", month))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
