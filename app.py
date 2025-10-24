import logging
import random
import asyncio
import re
from collections import deque
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import pytesseract
from PIL import Image
import io

# लॉगिंग
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ग्लोबल डेटा
last_results = deque(maxlen=50)  # पिछले 50 रिजल्ट्स (नंबर)
user_chats = set()              # सक्रिय यूज़र्स
is_running = False              # 24/7 स्टेटस

# नंबर पैटर्न (0-9)
NUMBER_PATTERN = re.compile(r'\b([0-9])\b')

# OCR से इमेज से टेक्स्ट निकालो
def ocr_image(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang='eng')
        return text
    except Exception as e:
        logger.error(f"OCR Error: {e}")
        return ""

# टेक्स्ट से नंबर निकालो
def extract_numbers(text):
    numbers = NUMBER_PATTERN.findall(text)
    return [int(n) for n in numbers if n.isdigit()]

# एनालिसिस और प्रेडिक्शन
def analyze_and_predict(numbers):
    if len(numbers) < 3:
        return "कम डेटा", None, None, 50

    recent = numbers[-5:]
    small_count = sum(1 for x in recent if x <= 4)
    big_count = len(recent) - small_count

    # पैटर्न चेक
    last_three = recent[-3:]
    if len(set(last_three)) == 1:  # 3 same
        pred_num = random.choice([0,1,2,3,4,5,6,7,8,9])
        confidence = 75
    elif small_count >= 4:
        pred_num = random.choice([5,6,7,8,9])
        confidence = 82
    elif big_count >= 4:
        pred_num = random.choice([0,1,2,3,4])
        confidence = 82
    else:
        pred_num = random.randint(0, 9)
        confidence = 68

    pred_type = "Small" if pred_num <= 4 else "Big"
    color = "Violet" if pred_num in [0, 5] else ("Red" if pred_num >= 5 else "Green")

    return color, pred_num, pred_type, confidence

# फोटो हैंडलर (स्क्रीनशॉट)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_chats.add(chat_id)

    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    await update.message.reply_text("स्क्रीनशॉट मिला! एनालिसिस कर रहा हूँ...")

    text = ocr_image(photo_bytes)
    if not text.strip():
        await update.message.reply_text("कोई टेक्स्ट नहीं मिला। साफ़ स्क्रीनशॉट भेजें।")
        return

    numbers = extract_numbers(text)
    if len(numbers) < 5:
        await update.message.reply_text(f"केवल {len(numbers)} नंबर मिले। कम से कम 5 चाहिए।")
        return

    # ग्लोबल रिजल्ट्स अपडेट
    last_results.extend(numbers[-20:])

    color, pred_num, pred_type, confidence = analyze_and_predict(list(last_results))

    message = (
        "पूरा एनालिसिस\n\n"
        f"मिले नंबर: `{', '.join(map(str, numbers[-10:]))}`\n"
        f"पिछले 5: `{', '.join(map(str, numbers[-5:]))}`\n\n"
        f"अगला नंबर: **{pred_num}**\n"
        f"टाइप: **{pred_type}** (0-4=Small, 5-9=Big)\n"
        f"कलर: **{color}**\n"
        f"आत्मविश्वास: {confidence}%\n\n"
        "अभी बेट लगाओ! (सिमुलेशन है)"
    )
    await update.message.reply_text(message, parse_mode='Markdown')

# 24/7 ऑटो प्रेडिक्शन
async def auto_prediction_task(application: Application):
    global is_running
    while is_running:
        try:
            # नया रैंडम रिजल्ट
            new_result = random.choices([0,1,2,3,4,5,6,7,8,9], weights=[10]*10, k=1)[0]
            last_results.append(new_result)

            color, pred_num, pred_type, confidence = analyze_and_predict(list(last_results))

            message = (
                "24/7 ऑटो प्रेडिक्शन\n\n"
                f"अभी का रिजल्ट: `{new_result}` ({'Violet' if new_result in [0,5] else ('Red' if new_result >=5 else 'Green')})\n"
                f"अगला अनुमान: **{pred_num}** ({pred_type})\n"
                f"कलर: **{color}**\n"
                f"आत्मविश्वास: {confidence}%\n\n"
                f"पिछले 10: `{' | '.join(map(str, list(last_results)[-10:]))}`\n\n"
                "सिमुलेशन है — रियल गेम में कोई गारंटी नहीं!"
            )

            for chat_id in list(user_chats):
                try:
                    await application.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                except:
                    user_chats.discard(chat_id)

            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Auto error: {e}")
            await asyncio.sleep(10)

# कमांड्स
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chats.add(update.effective_chat.id)
    await update.message.reply_text(
        "*कलर + नंबर प्रेडिक्टर बॉट चालू!*\n\n"
        "फोटो भेजो → मैं पूरा एनालिसिस करूँगा\n"
        "हर मिनट ऑटो प्रेडिक्शन भी आएगा!\n\n"
        "/predict - मैन्युअल\n"
        "/stop - ऑटो बंद\n"
        "/stats - स्टेटस",
        parse_mode='Markdown'
    )

async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chats.add(update.effective_chat.id)
    if len(last_results) < 3:
        await update.message.reply_text("पहले स्क्रीनशॉट भेजो!")
        return
    color, pred_num, pred_type, confidence = analyze_and_predict(list(last_results))
    await update.message.reply_text(
        f"मैन्युअल प्रेडिक्शन\n\n"
        f"अगला: **{pred_num}** ({pred_type})\n"
        f"कलर: **{color}**\n"
        f"आत्मविश्वास: {confidence}%",
        parse_mode='Markdown'
    )

async def stop_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chats.discard(update.effective_chat.id)
    await update.message.reply_text("ऑटो प्रेडिक्शन आपके लिए बंद।")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"*बॉट स्टेटस*\n\n"
        f"सक्रिय यूज़र्स: {len(user_chats)}\n"
        f"कुल रिजल्ट्स: {len(last_results)}\n"
        f"24/7: {'चालू' if is_running else 'बंद'}",
        parse_mode='Markdown'
    )

# मेन फंक्शन
def main():
    global is_running
    TOKEN = '8313201920:AAH1PfXk6b6sgBPNCT_H5AEMAhZETItO5gg'

    application = Application.builder().token(TOKEN).build()

    # हैंडलर्स
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("predict", predict))
    application.add_handler(CommandHandler("stop", stop_auto))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # 24/7 ऑटो शुरू करो
    async def start_auto():
        global is_running
        is_running = True
        await auto_prediction_task(application)

    application.job_queue.run_once(lambda _: application.create_task(start_auto()), 2)

    print("24/7 + OCR प्रेडिक्टर बॉट चालू हो रहा है...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
