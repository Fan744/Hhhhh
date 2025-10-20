import logging
import aiohttp
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)

# ✅ ADD YOUR BOT TOKEN HERE
BOT_TOKEN = "7576547930:AAEPWxQHD3yNJwcZ0zCpK5OZFHiawxQrGIQ"

# ✅ TELEGRAM CHANNEL USERNAME (without @)
CHANNEL_USERNAME = "team_black_hat_offical"

# ✅ Enable logs
logging.basicConfig(level=logging.INFO)

# Global memory for tracking user sessions
user_sessions = {}

# ✅ Loading bar text
async def show_loading(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    loading = await context.bot.send_message(chat_id, "🔄 Loading AI Engine [░░░░░░░░░░] 0%")
    for percent in range(10, 101, 10):
        bar = "▓" * (percent // 10) + "░" * (10 - percent // 10)
        await loading.edit_text(f"🔄 LOADING AI PREDICTION [{bar}] {percent}%")
        await asyncio.sleep(0.2)

# ✅ Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if user has joined the required channel
    try:
        member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        if member.status not in ["member", "administrator", "creator"]:
            raise Exception("Not joined")
    except:
        # User not joined
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("✅ I JOINED", callback_data="check_join")]
        ])
        await context.bot.send_message(chat_id, "❗ YOU NEED TO JOIN OUR CHANNEL TO USE THIS BOT", reply_markup=keyboard)
        return

    await context.bot.send_message(chat_id, "👋 WELCOME TO AI PREDICTION TOOL\n\nKINDLY ENTER YOUR GAME ID:")
    user_sessions[user_id] = {"step": "awaiting_game_id"}

# ✅ Handle JOINED check
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    try:
        member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        if member.status not in ["member", "administrator", "creator"]:
            await query.edit_message_text("❌ YOU STILL HAVEN'T JOINED THE CHANNEL. PLEASE JOIN FIRST.")
        else:
            await query.edit_message_text("✅ GREAT! YOU ARE VERIFIED.\nHOW SEND /start to begin.")
    except:
        await query.edit_message_text("⚠️ ERROR VERIFYING. TRY AGAIN LATER.")

# ✅ Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_sessions:
        return await update.message.reply_text("PLEASE TYPE /start to begin.")

    session = user_sessions[user_id]

    # Step 1: Game ID
    if session["step"] == "awaiting_game_id":
        session["game_id"] = text
        session["step"] = "awaiting_tool_choice"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛩 AVIATOR AI TOOL", callback_data="aviator")],
            [InlineKeyboardButton("🐯 TIGER VS DRAGON", callback_data="tvd")],
            [InlineKeyboardButton("🔢 BIG SMALL", callback_data="bigsmall")]
        ])
        await update.message.reply_text("✅ GAME ID SAVED.\nSELECT TOOL BELOW:", reply_markup=keyboard)

    # Step 2: Awaiting results
    elif session["step"] == "awaiting_results":
        await show_loading(context, update.effective_chat.id)
        prediction = await predict(session["tool"], text)
        await update.message.reply_text(f"🎯 AI PREDICTION RESULT:\n\n{prediction}")

# ✅ Handle Tool Selection
async def handle_tool_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if user_id not in user_sessions:
        return await query.edit_message_text("PLEASE TYPE /start first.")

    tool_text = {
        "aviator": "✈️ PLEASE ENTER LAST 4 CRASH VALUES (e.g. `1.20      4.20     3.03       99.99`):",
        "tvd": "🐅 PLEASE ENTER LAST 4 RESULTS (e.g. `T . D . T . D`):",
        "bigsmall": "🔢 PLEASE ENTER LAST 5 NUMBERS (e.g. `20     3     21     8`):"
    }

    user_sessions[user_id]["tool"] = data
    user_sessions[user_id]["step"] = "awaiting_results"

    await query.edit_message_text(tool_text[data], parse_mode='Markdown')

# ✅ AI Logic Prediction
async def predict(tool, input_text):
    if tool == "aviator":
        try:
            nums = [float(x) for x in input_text.strip().split()]
            avg = sum(nums) / len(nums)
            if avg < 2:
                return "🔴 PREDICTION: LOW CRASH (<1X)"
            elif avg < 10:
                return "🟡 PREDICTION: MEDIUM CRASH (2x–5x)"
            else:
                return "🟢 PREDICTION: HIGH CRASH (>10x)"
        except:
            return "❌ INVALID INPUT FORMAT FOR AVIATOR."

    elif tool == "tvd":
        sequence = input_text.upper().replace(",", "").split()
        if sequence.count("T") > sequence.count("D"):
            return "🔮 PREDICTION: TIGER"
        else:
            return "🔮 PREDICTION: DRAGON"

    elif tool == "bigsmall":
        try:
            nums = [int(x) for x in input_text.split()]
            avg = sum(nums) / len(nums)
            return "📊 PREDICTION: BIG" if avg >= 10 else "📉 PREDICTION: SMALL"
        except:
            return "❌ INVALID INPUT FORMAT FOR BIG SMALL."

# ✅ Main entry point
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(handle_tool_select))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()