import logging
import random
from collections import deque
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio

# लॉगिंग
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ग्लोबल डेटा
last_results = deque(maxlen=20)  # पिछले 20 रिजल्ट्स
user_chats = set()  # सभी चैट IDs जो बॉट से बात कर रहे हैं
is_running = False  # ऑटो प्रेडिक्शन स्टेटस

# रैंडम रिजल्ट जेनरेटर (सिमुलेशन)
def generate_random_result():
    weights = [45, 45, 10]  # Red: 45%, Green: 45%, Violet: 10%
    return random.choices(['Red', 'Green', 'Violet'], weights=weights, k=1)[0]

# प्रेडिक्शन लॉजिक
def get_prediction():
    if len(last_results) < 3:
        return random.choice(['Red', 'Green'])
    
    recent = list(last_results)[-3:]
    red_count = recent.count('Red')
    green_count = recent.count('Green')
    
    if red_count >= 2:
        return 'Green'
    elif green_count >= 2:
        return 'Red'
    else:
        return random.choice(['Red', 'Green', 'Violet'])

# ऑटो प्रेडिक्शन टास्क (हर 60 सेकंड)
async def auto_prediction_task(application: Application):
    global is_running
    while is_running:
        try:
            # 1. नया रिजल्ट जेनरेट करो (सिमुलेशन)
            new_result = generate_random_result()
            last_results.append(new_result)

            # 2. प्रेडिक्शन बनाओ
            prediction = get_prediction()
            confidence = random.randint(68, 92)

            # 3. मैसेज बनाओ
            message = (
                "ऑटो प्रेडिक्शन (24/7)\n\n"
                f"अभी का रिजल्ट: `{new_result}`\n"
                f"अगला प्रेडिक्शन: **{prediction}**\n"
                f"आत्मविश्वास: {confidence}%\n\n"
                f"पिछले 10 रिजल्ट्स:\n"
                f"`{' | '.join(list(last_results)[-10:])}`\n\n"
                "यह सिर्फ सिमुलेशन है। रियल गेम में कोई गारंटी नहीं!"
            )

            # 4. सभी यूजर्स को भेजो
            for chat_id in list(user_chats):
                try:
                    await application.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    logger.error(f"Failed to send to {chat_id}: {e}")
                    user_chats.discard(chat_id)

            # 60 सेकंड वेट
            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"Auto prediction error: {e}")
            await asyncio.sleep(10)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_chats.add(chat_id)

    await update.message.reply_text(
        "*24/7 कलर प्रेडिक्शन बॉट चालू!*\n\n"
        "हर मिनट में आपको ऑटो प्रेडिक्शन मिलेगा!\n\n"
        "/predict - मैन्युअल प्रेडिक्शन\n"
        "/stop - ऑटो प्रेडिक्शन बंद करें\n"
        "/stats - स्टेटस चेक करें\n\n"
        "*जुआ से दूर रहें। यह सिर्फ एंटरटेनमेंट है।*",
        parse_mode='Markdown'
    )

# /predict (मैन्युअल)
async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_chats.add(chat_id)

    prediction = get_prediction()
    confidence = random.randint(65, 90)

    message = (
        f"**मैन्युअल प्रेडिक्शन**: **{prediction}**\n"
        f"**आत्मविश्वास**: {confidence}%\n"
        f"**पिछले 5**: `{' | '.join(list(last_results)[-5:])}`"
    )
    await update.message.reply_text(message, parse_mode='Markdown')

# /stop
async def stop_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_chats.discard(chat_id)
    await update.message.reply_text("ऑटो प्रेडिक्शन आपके लिए बंद कर दिया गया।")

# /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_users = len(user_chats)
    total_results = len(last_results)
    await update.message.reply_text(
        f"*बॉट स्टेटस*\n\n"
        f"सक्रिय यूजर्स: {total_users}\n"
        f"कुल रिजल्ट्स: {total_results}\n"
        f"24/7 प्रेडिक्शन: {'चालू' if is_running else 'बंद'}",
        parse_mode='Markdown'
    )

# मेन फंक्शन
def main():
    global is_running

    # आपका टोकन यहाँ डाला गया है
    TOKEN = '8313201920:AAH1PfXk6b6sgBPNCT_H5AEMAhZETItO5gg'

    application = Application.builder().token(TOKEN).build()

    # कमांड्स
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("predict", predict))
    application.add_handler(CommandHandler("stop", stop_auto))
    application.add_handler(CommandHandler("stats", stats))

    # बॉट स्टार्ट होने पर ऑटो टास्क शुरू करो
    async def start_auto_task():
        global is_running
        is_running = True
        await auto_prediction_task(application)

    application.job_queue.run_once(lambda _: application.create_task(start_auto_task()), 2)

    print("24/7 कलर प्रेडिक्शन बॉट स्टार्ट हो रहा है...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
