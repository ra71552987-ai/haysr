import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8271506797:AAHBkap1k50sTMWuGZDrukfY57l96WYxpWA"
CHANNEL_USERNAME = "@yorklme"
CHANNEL_POST = -1003481744348
ADMINS = [7615929638]

bot = telebot.TeleBot(TOKEN)

votes = {}             # اسم -> عدد الأصوات
voters = {}            # اسم -> مجموعة معرفات اللي صوتوا
votes_messages = {}    # اسم -> (chat_id, message_id) لرسالة التصويت بالقناة


# ======= دالة مساعدة لتحديث زر التصويت في الرسالة المخزنة =======
def update_vote_button(name):
    """
    تحاول تعدّل زر رسالة التصويت الخاصة بالاسم إذا كانت موجودة.
    """
    if name not in votes_messages:
        return
    chat_id, message_id = votes_messages[name]
    try:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"🖤 تصويت ({votes.get(name,0)})", callback_data=f"vote_{name}"))
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
    except Exception:
        # ممكن الرسالة انمحيت أو ما عدنا صلاحية - نتجاهل الخطأ بشكل آمن
        pass


# ==================== /START ====================
@bot.message_handler(commands=["start"])
def start_cmd(msg):
    user_id = msg.from_user.id

    if user_id in ADMINS:
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("➕ نشر تصويت", callback_data="send_vote"),
            InlineKeyboardButton("📈 إضافة أصوات", callback_data="add_vote_menu"),
            InlineKeyboardButton("❌ حذف تصويت", callback_data="remove_vote_menu")
        )
        bot.reply_to(msg, "🎛 أهلاً فيك — هاي لوحة التحكم:", reply_markup=markup)
    else:
        bot.reply_to(msg, "🤍 أهلاً في بوت التصويت\n🖤 الأوامر مخصصة للأدمن فقط.")


# ==================== SEND VOTE ====================
@bot.callback_query_handler(func=lambda call: call.data == "send_vote")
def ask_name(call):
    # فقط الأدمن يستطيع نشر، نحط تحقق بسيط
    if call.from_user.id not in ADMINS:
        return bot.answer_callback_query(call.id, "🚫 مو إلك", show_alert=True)

    msg = bot.send_message(call.message.chat.id, "📝 اكتب اسم الشخص يلي بدك تنشر عنه تصويت:")
    bot.register_next_step_handler(msg, publish_vote)

def publish_vote(msg):
    name = msg.text.strip()
    if not name:
        return bot.reply_to(msg, "❌ الاسم مو صالح")

    # تهيئة الهياكل لو ما كانت موجودة
    votes.setdefault(name, 0)
    voters.setdefault(name, set())

    # إرسال رسالة التصويت إلى القناة وتخزين معرف الرسالة
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f"🖤 تصويت ({votes[name]})", callback_data=f"vote_{name}"))

    sent = bot.send_message(
        CHANNEL_POST,
        f"📌 *تصويت لشخص:* {name}",
        parse_mode="Markdown",
        reply_markup=markup
    )

    # خزّن موقع رسالة التصويت لحتى نقدر نحدّثها لاحقاً
    votes_messages[name] = (sent.chat.id, sent.message_id)

    bot.reply_to(msg, "✔ تم نشر التصويت بالقناة 🎉")


# ==================== VOTING ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("vote_"))
def vote(call):
    name = call.data.replace("vote_", "")
    user_id = call.from_user.id

    # التحقق من الاشتراك بالقناة
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ["left", "kicked"]:
            bot.answer_callback_query(call.id, "❗ لازم تشترك بالقناة قبل التصويت", show_alert=True)
            return
    except Exception:
        bot.answer_callback_query(call.id, "❗ لازم تشترك بالقناة قبل التصويت", show_alert=True)
        return

    # تهيئة لو ما موجود
    votes.setdefault(name, 0)
    voters.setdefault(name, set())

    if user_id in voters[name]:
        bot.answer_callback_query(call.id, "🚫 انت مصوّت من قبل", show_alert=True)
        return

    voters[name].add(user_id)
    votes[name] += 1

    # حدّث زر الرسالة: إذا الكول جاء من رسالة محددة (غالباً رسالة القناة)، بنحدثها
    try:
        # نجرّب نحدّث نفس رسالة الكول
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"🖤 تصويت ({votes[name]})", callback_data=f"vote_{name}"))
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass

    # تأكد كمان تحديث الرسالة المخزنة (لو كانت موجودة)
    update_vote_button(name)

    bot.answer_callback_query(call.id, "🖤 شكراً لصوتك!")


# ==================== ADD VOTES (ADMINS via buttons) ====================
@bot.callback_query_handler(func=lambda call: call.data == "add_vote_menu")
def select_name_add(call):
    if call.from_user.id not in ADMINS:
        return bot.answer_callback_query(call.id, "🚫 مو إلك", show_alert=True)

    if not votes:
        return bot.answer_callback_query(call.id, "ما في أسماء لسه", show_alert=True)

    markup = InlineKeyboardMarkup()
    for name in votes:
        markup.add(InlineKeyboardButton(name, callback_data=f"add_to_{name}"))

    # نعدل نص الرسالة اللي ضغط عليها الأدمن لعرض القائمة
    try:
        bot.edit_message_text("🔢 اختر الاسم يلي بدك تزيد أصوات له:", call.message.chat.id, call.message.message_id)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        # لو ما قدرنا نعدل رسالة (مثلاً رسالة قديمة) نرسل رسالة جديدة:
        bot.send_message(call.message.chat.id, "🔢 اختر الاسم يلي بدك تزيد أصوات له:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_to_"))
def ask_amount(call):
    if call.from_user.id not in ADMINS:
        return bot.answer_callback_query(call.id, "🚫 مو إلك", show_alert=True)

    name = call.data.replace("add_to_", "")
    msg = bot.send_message(call.message.chat.id, f"📈 اكتب عدد الأصوات اللي بدك تضيف لـ {name}:")
    bot.register_next_step_handler(msg, lambda m: apply_add(m, name))


def apply_add(msg, name):
    # تأكد من صلاحية الرقم والاسم
    try:
        amount = int(msg.text)
    except:
        return bot.reply_to(msg, "❌ لازم رقم صالح")

    votes.setdefault(name, 0)
    voters.setdefault(name, set())

    votes[name] += amount

    # حدث زر الرسالة المخزنة إذا موجودة
    update_vote_button(name)

    bot.reply_to(msg, f"✔ تمت زيادة {amount} صوت\n🔢 المجموع الجديد: {votes[name]}")


# ==================== REMOVE VOTE (ADMINS via buttons) ====================
@bot.callback_query_handler(func=lambda call: call.data == "remove_vote_menu")
def delete_vote_menu(call):
    if call.from_user.id not in ADMINS:
        return bot.answer_callback_query(call.id, "🚫 مو إلك", show_alert=True)

    if not votes:
        return bot.answer_callback_query(call.id, "ما في أسماء لسه", show_alert=True)

    markup = InlineKeyboardMarkup()
    for name in votes:
        markup.add(InlineKeyboardButton(name, callback_data=f"remove_from_{name}"))

    try:
        bot.edit_message_text("❌ اختر الاسم يلي بدك تشيل منه صوت:", call.message.chat.id, call.message.message_id)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, "❌ اختر الاسم يلي بدك تشيل منه صوت:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_from_"))
def ask_user_to_remove(call):
    if call.from_user.id not in ADMINS:
        return bot.answer_callback_query(call.id, "🚫 مو إلك", show_alert=True)

    name = call.data.replace("remove_from_", "")
    msg = bot.send_message(call.message.chat.id, f"🧍‍♂️ اكتب معرف الشخص يلي بدك تشيل صوته من {name}:")
    bot.register_next_step_handler(msg, lambda m: apply_remove(m, name))


def apply_remove(msg, name):
    try:
        uid = int(msg.text)
    except:
        return bot.reply_to(msg, "❌ لازم معرف صحيح")

    voters.setdefault(name, set())
    votes.setdefault(name, 0)

    if uid not in voters[name]:
        return bot.reply_to(msg, "❌ هاد الشخص ما صوّت")

    voters[name].remove(uid)
    votes[name] = max(0, votes[name] - 1)

    # حدث زر الرسالة المخزنة إذا موجودة
    update_vote_button(name)

    bot.reply_to(msg, f"✔ تم إزالة صوت\n📉 المجموع الجديد لـ {name}: {votes[name]}")


# ==================== RUN BOT ====================
bot.infinity_polling()
