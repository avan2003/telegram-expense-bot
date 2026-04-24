import os datetime import datetime, timedelta
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID")
DB_PATH = os.getenv("DB_PATH", "/app/data/expenses.db")

def previous_month_range():
    today = datetime.now()
    first_of_this_month = today.replace(day=1)
    last_of_previous_month = first_of_this_month - timedelta(days=1)
    month_str = last_of_previous_month.strftime("%Y-%m")
    return month_str

async def send_summary():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")
    if not ALLOWED_USER_ID:
        raise RuntimeError("ALLOWED_USER_ID is missing")

    month_str = previous_month_range()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT category, SUM(amount)
        FROM expenses
        WHERE user_id = ? AND date LIKE ?
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (int(ALLOWED_USER_ID), f"{month_str}%"))
    rows = cursor.fetchall()

    if not rows:
        message = f"📊 Monthly Expense Summary ({month_str})\n\nNo expenses were logged."
    else:
        total = sum(row[1] for row in rows)
        lines = [f"📊 Monthly Expense Summary ({month_str})", ""]
        for category, amount in rows:
            lines.append(f"• {category}: SGD {amount:.2f}")
        lines.append("")
        lines.append(f"💰 Total: SGD {total:.2f}")
        message = "\n".join(lines)

    bot = Bot(BOT_TOKEN)
    await bot.send_message(chat_id=int(ALLOWED_USER_ID), text=message)

if __name__ == "__main__":
    asyncio.run(send_summary())
import sqlite3
import asyncio
