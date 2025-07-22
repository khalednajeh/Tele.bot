from telegram.ext import CallbackQueryHandler
import requests
import json
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler, ConversationHandler
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
import os

# مفتاح OCR
OCR_API_KEY = 'K88477734388957'

# كلمات تدل على الاشتراك
KEYWORDS_SUBSCRIBE = ['تم', 'مشترك', 'تم الاشتراك', 'subscribed', 'subscribe']

# كلمات تدل على القناة
KEYWORDS_CHANNEL = ['khaled', 'najeh', 'نتعلم']

# ملف الأزرار
BUTTONS_FILE = 'buttons.json'

# كلمة السر
ADMIN_PASSWORD = '0000'

# لحفظ الجلسات المؤقتة
user_verified = set()
admin_sessions = {}

def ocr_space_api(image_path):
    with open(image_path, 'rb') as f:
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'filename': f},
            data={
                'apikey': OCR_API_KEY,
                'language': 'ara',
            }
        )
    try:
        result = response.json()
        return result['ParsedResults'][0]['ParsedText'].lower()
    except:
        return ''

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 أهلاً وسهلاً في قناة *Khaled Najeh*!\n\n"
        "🎯 لعرض الرابط الحصري، فقط أرسل *لقطة شاشة من الصفحة الرئيسية لقناتنا* على يوتيوب.\n\n"
        "🔗 رابط القناة:\nhttps://youtube.com/@khalednajeh1"
    )

def handle_photo(update: Update, context: CallbackContext):
    if update.message and update.message.photo:
        file = update.message.photo[-1].get_file()
        image_path = f"{file.file_id}.jpg"
        file.download(image_path)

        update.message.reply_text("⏳ جاري التحقق من الصورة...")

        extracted_text = ocr_space_api(image_path)
        os.remove(image_path)

        has_subscribe_word = any(word in extracted_text for word in KEYWORDS_SUBSCRIBE)
        has_channel_name = any(name in extracted_text for name in KEYWORDS_CHANNEL)

        if has_subscribe_word and has_channel_name:
            user_verified.add(update.message.from_user.id)
            update.message.reply_text("✅ شكراً لاشتراكك في قناة Khaled Najeh!\n📥 إليك الأزرار:")
            send_buttons(update, context)
        else:
            update.message.reply_text(
    "❌ لم أجد دليل كافي على أنك مشترك في القناة.\n"
    "يرجى إرسال صورة توضح الاشتراك في *قناتنا تحديدًا*.\n\n"
    "🔗 رابط القناة:\nhttps://youtube.com/@khalednajeh1"
)

def send_buttons(update: Update, context: CallbackContext):
    if not os.path.exists(BUTTONS_FILE):
        with open(BUTTONS_FILE, 'w') as f:
            json.dump([], f)

    with open(BUTTONS_FILE, 'r') as f:
        buttons = json.load(f)

    keyboard = [
        [InlineKeyboardButton(btn['text'], callback_data=f"btn_{i}")]
        for i, btn in enumerate(buttons)
    ]
    if keyboard:
        update.message.reply_text("⬇️ اختر من الأزرار التالية:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.message.reply_text("⚠️ لا يوجد أزرار حالياً.")

def handle_button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id not in user_verified:
        query.answer("يجب التحقق أولاً.")
        return

    index = int(query.data.split("_")[1])

    with open(BUTTONS_FILE, 'r') as f:
        buttons = json.load(f)

    if index < len(buttons):
        content = buttons[index]['content']
        query.message.reply_text(content)

# ========== ADMIN SECTION ==========

# حالات للمحادثة
ENTER_PASSWORD, ADMIN_MENU, ADD_BUTTON_TEXT, ADD_BUTTON_CONTENT, DELETE_BUTTON = range(5)

def admin_entry(update: Update, context: CallbackContext):
    update.message.reply_text("🔒 من فضلك أدخل كلمة السر للدخول:")
    return ENTER_PASSWORD

def check_password(update: Update, context: CallbackContext):
    if update.message.text == ADMIN_PASSWORD:
        admin_sessions[update.message.from_user.id] = True
        update.message.reply_text("✅ تم الدخول كأدمن.\nاختر إجراء:", reply_markup=ReplyKeyboardMarkup(
            [['➕ إضافة زر', '❌ حذف زر']], one_time_keyboard=True, resize_keyboard=True
        ))
        return ADMIN_MENU
    else:
        update.message.reply_text("❌ كلمة السر غير صحيحة.")
        return ConversationHandler.END

def admin_menu(update: Update, context: CallbackContext):
    text = update.message.text
    if text == '➕ إضافة زر':
        update.message.reply_text("📝 أرسل نص الزر:")
        return ADD_BUTTON_TEXT
    elif text == '❌ حذف زر':
        with open(BUTTONS_FILE, 'r') as f:
            buttons = json.load(f)
        msg = "🗑️ اختر رقم الزر لحذفه:\n" + "\n".join([f"{i+1}. {b['text']}" for i, b in enumerate(buttons)])
        update.message.reply_text(msg)
        return DELETE_BUTTON
    else:
        update.message.reply_text("❓ أمر غير مفهوم.")
        return ADMIN_MENU

def add_button_text(update: Update, context: CallbackContext):
    context.user_data['new_button_text'] = update.message.text
    update.message.reply_text("✏️ أرسل المحتوى الذي سيتم عرضه عند الضغط على الزر:")
    return ADD_BUTTON_CONTENT

def add_button_content(update: Update, context: CallbackContext):
    new_button = {
        'text': context.user_data['new_button_text'],
        'content': update.message.text
    }

    if not os.path.exists(BUTTONS_FILE):
        with open(BUTTONS_FILE, 'w') as f:
            json.dump([], f)

    with open(BUTTONS_FILE, 'r') as f:
        buttons = json.load(f)

    buttons.append(new_button)
    with open(BUTTONS_FILE, 'w') as f:
        json.dump(buttons, f)

    update.message.reply_text("✅ تم إضافة الزر.")
    return ConversationHandler.END

def delete_button(update: Update, context: CallbackContext):
    index = int(update.message.text.strip()) - 1
    with open(BUTTONS_FILE, 'r') as f:
        buttons = json.load(f)
    if 0 <= index < len(buttons):
        del buttons[index]
        with open(BUTTONS_FILE, 'w') as f:
            json.dump(buttons, f)
        update.message.reply_text("✅ تم حذف الزر.")
    else:
        update.message.reply_text("❌ رقم غير صالح.")
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("❎ تم الإلغاء.")
    return ConversationHandler.END

# ========== MAIN ==========

def main():
    TOKEN = "7809623294:AAHM-FU-_3KBgcCSs0SyGaQsWNwGPCkHbJg"
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    dp.add_handler(CallbackQueryHandler(handle_button_click))

    # محادثة الأدمن
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler('admin', admin_entry)],
        states={
            ENTER_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, check_password)],
            ADMIN_MENU: [MessageHandler(Filters.text & ~Filters.command, admin_menu)],
            ADD_BUTTON_TEXT: [MessageHandler(Filters.text & ~Filters.command, add_button_text)],
            ADD_BUTTON_CONTENT: [MessageHandler(Filters.text & ~Filters.command, add_button_content)],
            DELETE_BUTTON: [MessageHandler(Filters.text & ~Filters.command, delete_button)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(admin_conv)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()