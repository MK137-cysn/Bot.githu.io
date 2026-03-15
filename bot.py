import requests
import os
import time
import edge_tts
import threading
import http.server
import socketserver
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- ផ្នែកបញ្ឆោត Render (Dummy Server) ---
def run_dummy_server():
    # Render តម្រូវឱ្យមាន Port (Default 10000)
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    # បង្កើត Server ងាយៗមួយដើម្បីឱ្យ Render ឃើញថាមាន Web Service ដើរ
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Dummy server started at port {port}")
        httpd.serve_forever()

# បើក Dummy Server ក្នុង Thread ផ្សេងមួយដើម្បីកុំឱ្យវាទាស់ជាមួយ Bot
threading.Thread(target=run_dummy_server, daemon=True).start()

# --- Configuration ---
TELEGRAM_TOKEN = '8562086998:AAGtfdIzJvuHvHZd9dWarC8Y3TMX13K2hJ4'
ELEVENLABS_API_KEY = '5e09bdaa950ef146c81858a17c1a340ab2a3c00fb17768cd91c4005b25cdba11'
CHANNEL_ID = '@I_AM_RA2'
CHANNEL_URL = 'https://t.me/I_AM_RA2'
VOICE_ID_EN = '21m00Tcm4TlvDq8ikWAM'
VOICE_KH = "km-KH-SreymomNeural"

user_usage_en = {} # កូតាអង់គ្លេស
user_mode = {}  

main_keyboard = [['🇺🇸 English', '🇰🇭 ខ្មែរ'], ['📊 ឆែកមើលកូតាអង់គ្លេស']]
markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

async def is_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception: return False

def get_join_keyboard():
    keyboard = [[InlineKeyboardButton("🔗 ចូលរួម Channel", url=CHANNEL_URL)],
                [InlineKeyboardButton("✅ ខ្ញុំបានចូលរួមរួចហើយ", callback_data="check_sub")]]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_subscribed(context.bot, update.effective_user.id):
        await update.message.reply_text("សូមជ្រើសរើសភាសា៖\n- ខ្មែរ: 500អក្សរ/សារ (ប្រើបានរហូត)\n- អង់គ្លេស: 500អក្សរ/ថ្ងៃ", reply_markup=markup)
    else:
        await update.message.reply_text("សូមចូលរួម Channel ជាមុនសិន!", reply_markup=get_join_keyboard())

async def check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_subscribed(context.bot, query.from_user.id):
        await query.edit_message_text("✅ រួចរាល់! សូមជ្រើសរើសភាសាខាងក្រោម៖")
        await context.bot.send_message(chat_id=query.from_user.id, text="ជ្រើសរើសភាសា៖", reply_markup=markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    current_time = time.time()

    if not await is_subscribed(context.bot, user_id):
        await update.message.reply_text("សូមចូលរួម Channel ជាមុនសិន!", reply_markup=get_join_keyboard())
        return

    if text == '🇺🇸 English':
        user_mode[user_id] = 'en'
        await update.message.reply_text("Mode: English (កូតា 500/ថ្ងៃ)")
        return
    elif text == '🇰🇭 ខ្មែរ':
        user_mode[user_id] = 'kh'
        await update.message.reply_text("Mode: ខ្មែរ (សរសេរបាន 500 អក្សរ/សារ)")
        return
    elif text == '📊 ឆែកមើលកូតាអង់គ្លេស':
        usage = user_usage_en.get(user_id, {'count': 0, 'last_reset': current_time})
        await update.message.reply_text(f"📊 អង់គ្លេសប្រើអស់៖ {usage['count']}/500 អក្សរ")
        return

    mode = user_mode.get(user_id, 'kh')
    file_path = f"voice_{user_id}.mp3"

    # --- ករណីភាសាខ្មែរ ---
    if mode == 'kh':
        if len(text) > 500:
            await update.message.reply_text("❌ សម្រាប់ភាសាខ្មែរ អ្នកអាចសរសេរបានត្រឹមតែ 500 អក្សរប៉ុណ្ណោះក្នុងមួយសារ!")
            return
            
        await context.bot.send_chat_action(chat_id=user_id, action="record_voice")
        try:
            communicate = edge_tts.Communicate(text, VOICE_KH)
            await communicate.save(file_path)
            
            caption = (f"🤖 Bot: @Speak19_English_bot\n"
                       f"🔊 បំប្លែងដោយ៖ @I_AM_RA2\n"
                       f"📊 ប្រើអស់៖ {len(text)}/500 អក្សរ (ខ្មែរ)")
            
            with open(file_path, "rb") as audio:
                await update.message.reply_voice(voice=audio, caption=caption)
            os.remove(file_path)
        except Exception as e:
            await update.message.reply_text(f"Error ខ្មែរ: {str(e)}")

    # --- ករណីភាសាអង់គ្លេស ---
    else:
        usage = user_usage_en.get(user_id, {'count': 0, 'last_reset': current_time})
        if current_time - usage['last_reset'] > 86400:
            usage = {'count': 0, 'last_reset': current_time}
        
        if usage['count'] + len(text) > 500:
            await update.message.reply_text("❌ អស់កូតាអង់គ្លេស 500 អក្សរសម្រាប់ថ្ងៃនេះហើយ!")
            return

        await context.bot.send_chat_action(chat_id=user_id, action="upload_document")
        res = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID_EN}", 
                            json={"text": text, "model_id": "eleven_monolingual_v1"}, 
                            headers={"xi-api-key": ELEVENLABS_API_KEY})
        
        if res.status_code == 200:
            usage['count'] += len(text)
            user_usage_en[user_id] = usage
            
            caption = (f"🤖 Bot: @Speak19_English_bot\n"
                       f"🔊 បំប្លែងដោយ៖ @I_AM_RA2\n"
                       f"📊 ប្រើអស់៖ {usage['count']}/500 អក្សរ (អង់គ្លេស)")
            
            with open(file_path, "wb") as f: f.write(res.content)
            with open(file_path, "rb") as audio:
                await update.message.reply_audio(audio=audio, caption=caption)
            os.remove(file_path)
        else:
            await update.message.reply_text("ElevenLabs API Error!")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_callback, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running on Render...")
    app.run_polling()

if __name__ == '__main__':
    main()
    
