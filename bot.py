import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
PAYMENT_URL = "https://fitstate.ru/pay"

ASK_GENDER, ASK_AGE, ASK_WEIGHT, ASK_HEIGHT, ASK_GOAL = range(5)

ARCHETYPES = {
    "emotional_eater": {
        "emoji": "😰", "name": "Эмоциональный едок",
        "problem": "Ты не срываешься потому что слабый.\nТы срываешься, потому что мозг выучил паттерн:\nстресс → еда → легче.\n\nЭто не вопрос силы воли — это вопрос замены инструмента.\nБез работы с этим — любая диета временная.",
        "cycle": "🔴 Что происходит у тебя:\n\n→ Стресс активирует тягу к еде\n→ Ты ешь — становится легче\n→ Потом вина → ещё стресс → снова ешь\n→ Круг замкнулся",
        "solution": "✅ Что реально помогает:\n\n→ Замечать триггер до того, как рука потянулась\n→ Заменить еду другим инструментом снятия стресса\n→ Убрать провоцирующие ситуации заранее\n\nЭто навык. Ему можно научиться за 3–4 недели.",
        "tools": "🛠 Что уберём в твоём случае:\n\n1️⃣ Техники прерывания триггера\n2️⃣ Быстрые замены — 3–4 инструмента без еды\n3️⃣ Структура питания — убираем ситуации срыва",
        "day3": "📌 Топ-3 ошибки эмоционального едока:\n\n1. Держать дома запасы любимой еды\n2. Пропускать приёмы пищи — голод усиливает триггер\n3. Бороться силой воли — нужно переключать, не бороться",
        "proof": "Анна, 34 года — минус 11 кг за 8 недель.\nПерестала есть от стресса уже на 2-й неделе.\n\nМихаил, 31 год — минус 9 кг. Впервые не сорвался ни разу.",
    },
    "social_hostage": {
        "emoji": "🍕", "name": "Социальный заложник",
        "problem": "Наедине с собой ты держишься отлично.\nНо любое застолье или компания — всё рушится.\n\nЭто не слабость характера — это отсутствие конкретной стратегии.",
        "cycle": "🔴 Что происходит у тебя:\n\n→ Всю неделю держишься — приходит праздник\n→ Неловко отказывать, не хочешь выделяться\n→ Ешь как все — прогресс обнуляется\n→ Снова с понедельника",
        "solution": "✅ Что реально помогает:\n\n→ Конкретные сценарии: кафе, корпоратив, застолье\n→ Фразы-ответы, которые не обидят\n→ Правило 80/20 — как позволять себе без ущерба\n\nЭто навык, а не сила воли.",
        "tools": "🛠 Что уберём в твоём случае:\n\n1️⃣ Стратегия поведения в компании без срывов\n2️⃣ Гибкая система — любой праздник не ломает прогресс\n3️⃣ Коммуникация — как отказывать без обид",
        "day3": "📌 Топ-3 ошибки социального заложника:\n\n1. Ждать подходящего момента — его не будет\n2. Избегать мероприятий — это не жизнь\n3. Есть про запас перед выходом — не работает",
        "proof": "Катя, 29 лет — минус 8 кг без отказа от вечеринок.\n\nДмитрий, 36 лет — минус 10 кг. Рестораны с клиентами каждую неделю — ни одного срыва.",
    },
    "metabolic_skeptic": {
        "emoji": "⚖️", "name": "Метаболический скептик",
        "problem": "Ешь немного, стараешься, делаешь всё правильно.\nА результата нет.\n\nСтандартные советы просто не подходят для твоей ситуации.",
        "cycle": "🔴 Что происходит у тебя:\n\n→ Ешь мало — вес стоит или растёт\n→ Добавляешь активность — результата нет\n→ Думаешь «мне не дано»\n→ Опускаешь руки",
        "solution": "✅ Что реально помогает:\n\n→ Точный расчёт твоего реального коридора калорий\n→ Перезапуск обмена через правильный дефицит\n→ Работа с режимом сна и стрессом\n\nМетаболизм не сломан. Ему дают неправильный сигнал.",
        "tools": "🛠 Что уберём в твоём случае:\n\n1️⃣ Точная калорийность — реальный дефицит именно для тебя\n2️⃣ Состав питания — БЖУ, запускающий жиросжигание\n3️⃣ Режим — сон и стресс влияют сильнее, чем многие думают",
        "day3": "📌 Почему «мало ешь, но не худеешь»:\n\n1. Хроническое недоедание замедляет метаболизм\n2. Скрытые калории в «здоровых» продуктах\n3. Кортизол от стресса блокирует жиросжигание",
        "proof": "Ирина, 38 лет — 2 года не могла сдвинуться с места.\nЗа 8 недель минус 7 кг. Оказалось — ела слишком мало.\n\nСергей, 33 года — тренировался 4 раза в неделю. Поменяли питание — минус 9 кг.",
    },
    "starter_stopper": {
        "emoji": "🔁", "name": "Стартер-стопер",
        "problem": "В начале мотивация огромная.\nНо через 10–14 дней она испаряется — и всё заново.\n\nПроблема не в тебе.\nПроблема в том, что ты работаешь на силе воли. А она конечна у всех.",
        "cycle": "🔴 Что происходит у тебя:\n\n→ Мощный старт — мотивация на максимуме\n→ Через 1–2 недели энтузиазм падает\n→ Один пропуск → ощущение провала → бросаешь\n→ Через время — снова с понедельника",
        "solution": "✅ Что реально помогает:\n\n→ Заменить мотивацию системой — она не исчезает\n→ Внешние точки контроля: куратор, группа\n→ Маленькие wins вместо большой далёкой цели\n\nКогда есть система и окружение — мотивация не нужна.",
        "tools": "🛠 Что уберём в твоём случае:\n\n1️⃣ Система вместо силы воли — структура, которой легко следовать\n2️⃣ Куратор и группа — поддержка, которая не даёт выпасть\n3️⃣ Протокол срыва — что делать если пропустил",
        "day3": "📌 Почему стартер-стопер останавливается на 2-й неделе:\n\n1. Мотивация эмоциональная — она быстро гаснет\n2. Нет системы на сложный день — один пропуск = провал\n3. Цель далеко — мозг не видит прогресса",
        "proof": "Олег, 27 лет — начинал 6 раз за 2 года.\nВ потоке FitState впервые прошёл все 8 недель. Минус 8 кг.\n\nНастя, 31 год — группа и куратор сделали то, что сила воли не смогла за 3 года.",
    },
}


def calc(weight, height, goal):
    bmi = round(weight / ((height / 100) ** 2), 1)
    if goal == "fat":
        lo, hi = (8, 12) if bmi > 30 else (6, 9) if bmi > 25 else (4, 7)
        wlo, whi = round(weight - hi), round(weight - lo)
        bmi2 = round((wlo + whi) / 2 / ((height / 100) ** 2), 1)
        return dict(cw=weight, cb=bmi, wr=f"{wlo}–{whi} кг",
                    ch=f"−{lo}–{hi} кг жира", b2=bmi2, waist=f"−{lo+1}–{hi-1} см",
                    en="заметно вырастет к 3-й неделе")
    elif goal == "muscle":
        return dict(cw=weight, cb=bmi, wr=f"{round(weight+3)}–{round(weight+6)} кг",
                    ch="+3–6 кг мышц", b2=round(bmi+0.8, 1), waist="без изменений",
                    en="вырастет к 2-й неделе")
    else:
        wlo, whi = round(weight - 5), round(weight - 3)
        bmi2 = round((wlo + whi) / 2 / ((height / 100) ** 2), 1)
        return dict(cw=weight, cb=bmi, wr=f"{wlo}–{whi} кг",
                    ch="−3–5 кг + рельеф", b2=bmi2, waist="−3–5 см",
                    en="вырастет уже к концу 1-й недели")


def visual(f, name):
    return (f"🖼 *ТЫ СЕЙЧАС*\nВес: {f['cw']} кг  |  ИМТ: {f['cb']}\n_{name}_\n\n"
            f"⬇️  8 недель FitState  ⬇️\n\n"
            f"🖼 *ТЫ ЧЕРЕЗ 2 МЕСЯЦА*\nВес: {f['wr']}  |  ИМТ: {f['b2']}\n_{f['ch']}_")


def pay_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Записаться →", url=PAYMENT_URL)]])


def more_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("О нас и команде", callback_data="i_about")],
        [InlineKeyboardButton("Программа подробно", callback_data="i_program")],
        [InlineKeyboardButton("Результаты участников", callback_data="i_results")],
    ])


async def schedule_dojim(uid, context):
    jq = context.application.job_queue
    if not jq:
        return
    arch_key = context.user_data.get("arch_key", "emotional_eater")

    async def d1h(ctx):
        await ctx.bot.send_message(uid,
            "Вижу, что ты ещё думаешь — это нормально.\n\n"
            "Скидка 20% истекла, но запись ещё открыта.\n"
            "Что тебе важнее всего узнать?", reply_markup=more_kb())

    async def dd1(ctx):
        await ctx.bot.send_message(uid,
            "*О нас*\n\n9 лет. 55 000+ участников. Научный подход.\n\n"
            "Мы меняем причину, по которой у тебя не получалось раньше.",
            parse_mode="Markdown", reply_markup=pay_kb())

    async def dd2(ctx):
        await ctx.bot.send_message(uid,
            "*Программа по неделям:*\n\n"
            "📍 1–2: диагностика и настройка\n📍 3–4: первые результаты\n"
            "📍 5–6: закрепление\n📍 7–8: финальный рывок + план на после",
            parse_mode="Markdown", reply_markup=pay_kb())

    async def dd3(ctx):
        arch = ARCHETYPES.get(arch_key, ARCHETYPES["emotional_eater"])
        await ctx.bot.send_message(uid, arch["day3"], reply_markup=pay_kb())

    async def dd5(ctx):
        await ctx.bot.send_message(uid,
            "Поток идёт. Люди с похожими целями уже видят результат.\n\n"
            "Ты можешь присоединиться к следующему.", reply_markup=pay_kb())

    async def dd7(ctx):
        await ctx.bot.send_message(uid,
            "*Набор закрывается через 24 часа.*\n\n"
            "Ты знаешь свою причину. У тебя есть прогноз. Остался один шаг.",
            parse_mode="Markdown", reply_markup=pay_kb())

    jq.run_once(d1h, 3600,   name=f"d1h_{uid}")
    jq.run_once(dd1, 86400,  name=f"dd1_{uid}")
    jq.run_once(dd2, 172800, name=f"dd2_{uid}")
    jq.run_once(dd3, 259200, name=f"dd3_{uid}")
    jq.run_once(dd5, 432000, name=f"dd5_{uid}")
    jq.run_once(dd7, 604800, name=f"dd7_{uid}")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    arch_key = (context.args or [None])[0]
    arch = ARCHETYPES.get(arch_key)
    context.user_data["arch_key"] = arch_key

    if not arch:
        await update.message.reply_text(
            "Привет! 👋\nПройди тест и получи разбор:\n\n"
            "👉 https://vezuncheg.github.io/fitstate")
        return ConversationHandler.END

    await update.message.reply_text("Привет! 👋\n\nПолучил твои ответы. Даю разбор — 1 минута.")
    await update.message.reply_text(f"*{arch['emoji']} Твой тип: {arch['name']}*\n\n{arch['problem']}", parse_mode="Markdown")
    await update.message.reply_text(arch["cycle"])
    await update.message.reply_text(arch["solution"])
    await update.message.reply_text(
        "Хочешь узнать — *каким ты можешь стать за 2 месяца?*\n\nНужно пару вопросов.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Да, хочу узнать →", callback_data="go")],
            [InlineKeyboardButton("Может позже", callback_data="later")],
        ]))
    return ASK_GENDER


async def cb_later(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Хорошо! Когда будешь готов — /start\nМеню: /menu")
    return ConversationHandler.END


async def cb_go(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "Отлично! Отвечай как есть.\n\n*Ты мужчина или женщина?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Мужчина", callback_data="gm"),
            InlineKeyboardButton("Женщина", callback_data="gf"),
        ]]))
    return ASK_GENDER


async def cb_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["gender"] = "male" if update.callback_query.data == "gm" else "female"
    await update.callback_query.message.reply_text("*Сколько тебе лет?*\n\nНапиши число:", parse_mode="Markdown")
    return ASK_AGE


async def got_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text.strip())
        assert 10 <= age <= 100
        context.user_data["age"] = age
        await update.message.reply_text("*Текущий вес в кг?*\n\nНапример: 84", parse_mode="Markdown")
        return ASK_WEIGHT
    except:
        await update.message.reply_text("Напиши число, например: 28")
        return ASK_AGE


async def got_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        w = float(update.message.text.strip().replace(",", "."))
        assert 30 <= w <= 300
        context.user_data["weight"] = w
        await update.message.reply_text("*Рост в см?*\n\nНапример: 178", parse_mode="Markdown")
        return ASK_HEIGHT
    except:
        await update.message.reply_text("Напиши вес, например: 84")
        return ASK_WEIGHT


async def got_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        h = float(update.message.text.strip().replace(",", "."))
        assert 100 <= h <= 250
        context.user_data["height"] = h
        await update.message.reply_text(
            "*Какой результат важнее всего?*", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Убрать лишний жир", callback_data="gl_fat")],
                [InlineKeyboardButton("Набрать мышечную массу", callback_data="gl_muscle")],
                [InlineKeyboardButton("Улучшить форму и рельеф", callback_data="gl_tone")],
                [InlineKeyboardButton("Стать здоровее и энергичнее", callback_data="gl_health")],
            ]))
        return ASK_GOAL
    except:
        await update.message.reply_text("Напиши рост в см, например: 178")
        return ASK_HEIGHT


async def got_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    gmap = {"gl_fat": "fat", "gl_muscle": "muscle", "gl_tone": "tone", "gl_health": "tone"}
    goal = gmap.get(update.callback_query.data, "fat")
    context.user_data["goal"] = goal

    w = context.user_data["weight"]
    h = context.user_data["height"]
    arch_key = context.user_data.get("arch_key", "emotional_eater")
    arch = ARCHETYPES.get(arch_key, ARCHETYPES["emotional_eater"])

    await update.callback_query.message.reply_text("Считаю твой результат... ⏳")

    f = calc(w, h, goal)
    context.user_data["forecast"] = f

    await update.callback_query.message.reply_text(visual(f, arch["name"]), parse_mode="Markdown")
    await update.callback_query.message.reply_text(
        f"*📊 Прогноз на 8 недель:*\n\n"
        f"Сейчас: *{f['cw']} кг*, ИМТ *{f['cb']}*\n\n"
        f"Через 8 недель:\n"
        f"→ Вес: *{f['wr']}* ({f['ch']})\n"
        f"→ ИМТ: *{f['b2']}*\n"
        f"→ Объём: *{f['waist']}*\n"
        f"→ Энергия: {f['en']}\n\n"
        f"_На основе твоих параметров и средних результатов участников с похожим профилем._",
        parse_mode="Markdown")
    await update.callback_query.message.reply_text(arch["tools"])

    uid = update.callback_query.from_user.id
    await update.callback_query.message.reply_text(
        "🎯 *Хочешь достичь этого результата вместе с нами?*\n\n"
        "Набор в поток FitState открыт.\n"
        "Старт: *[дата]*  ·  Длительность: *8 недель*\n\n"
        "✅ Персональный план под твой тип\n"
        "✅ Закрытый Telegram-канал\n"
        "✅ Куратор на связи каждый день\n"
        "✅ Разбор прогресса еженедельно\n\n"
        "⏱ *Скидка 20% — действует 1 час с этого момента*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Оплатить со скидкой →", url=PAYMENT_URL)],
            [InlineKeyboardButton("Расскажи подробнее", callback_data="more_info")],
        ]))

    await schedule_dojim(uid, context)
    return ConversationHandler.END


async def cb_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Что важнее всего узнать?", reply_markup=more_kb())


async def cb_i_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "*О нас и команде*\n\n9 лет. 55 000+ участников.\nНаучный подход — алгоритмы на основе ВОЗ.\n\nМы меняем причину, по которой у тебя не получалось.",
        parse_mode="Markdown", reply_markup=pay_kb())


async def cb_i_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "*Программа по неделям:*\n\n📍 1–2: диагностика и настройка\n📍 3–4: первые результаты\n📍 5–6: закрепление\n📍 7–8: финальный рывок + план на после",
        parse_mode="Markdown", reply_markup=pay_kb())


async def cb_i_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    arch_key = context.user_data.get("arch_key", "emotional_eater")
    arch = ARCHETYPES.get(arch_key, ARCHETYPES["emotional_eater"])
    await update.callback_query.message.reply_text(
        f"*Результаты участников:*\n\n{arch['proof']}",
        parse_mode="Markdown", reply_markup=pay_kb())


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    arch_key = context.user_data.get("arch_key")
    f = context.user_data.get("forecast")
    arch = ARCHETYPES.get(arch_key)
    txt = "📋 *Главное меню FitState*\n\n"
    if arch and f:
        txt += f"Твой тип: *{arch['emoji']} {arch['name']}*\nПрогноз: {f['wr']} за 8 недель\n\n"
    await update.message.reply_text(txt, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Мой результат", callback_data="my_res")],
            [InlineKeyboardButton("📖 О программе", callback_data="i_program")],
            [InlineKeyboardButton("🏆 Результаты участников", callback_data="i_results")],
            [InlineKeyboardButton("💳 Записаться", url=PAYMENT_URL)],
        ]))


async def cb_my_res(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    arch_key = context.user_data.get("arch_key")
    f = context.user_data.get("forecast")
    arch = ARCHETYPES.get(arch_key)
    if arch and f:
        await update.callback_query.message.reply_text(visual(f, arch["name"]), parse_mode="Markdown")
        await update.callback_query.message.reply_text(
            f"*Твой тип:* {arch['emoji']} {arch['name']}\n*Прогноз:* {f['wr']} ({f['ch']}) за 8 недель",
            parse_mode="Markdown")
    else:
        await update.callback_query.message.reply_text("Пройди тест:\n👉 https://vezuncheg.github.io/fitstate")


def main():
    if not TOKEN:
        logger.error("BOT_TOKEN не установлен!")
        return

    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            ASK_GENDER: [
                CallbackQueryHandler(cb_go, pattern="^go$"),
                CallbackQueryHandler(cb_later, pattern="^later$"),
                CallbackQueryHandler(cb_gender, pattern="^g[mf]$"),
            ],
            ASK_AGE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, got_age)],
            ASK_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_weight)],
            ASK_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_height)],
            ASK_GOAL:   [CallbackQueryHandler(got_goal, pattern="^gl_")],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CallbackQueryHandler(cb_more,     pattern="^more_info$"))
    app.add_handler(CallbackQueryHandler(cb_i_about,  pattern="^i_about$"))
    app.add_handler(CallbackQueryHandler(cb_i_program,pattern="^i_program$"))
    app.add_handler(CallbackQueryHandler(cb_i_results,pattern="^i_results$"))
    app.add_handler(CallbackQueryHandler(cb_my_res,   pattern="^my_res$"))

    logger.info("FitState bot started ✅")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
