import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
PAYMENT_URL = "https://fitstate.ru/pay"  # заглушка — заменить на реальную

# ── СОСТОЯНИЯ ДИАЛОГА ──
ASK_GENDER, ASK_AGE, ASK_WEIGHT, ASK_HEIGHT, ASK_GOAL, SHOW_RESULT = range(6)

# ── АРХЕТИПЫ ──
ARCHETYPES = {
    "emotional_eater": {
        "emoji": "😰",
        "name": "Эмоциональный едок",
        "problem": (
            "Ты не срываешься потому что «слабый».\n"
            "Ты срываешься, потому что мозг выучил паттерн:\n"
            "стресс → еда → легче.\n\n"
            "Это не вопрос силы воли — это вопрос замены одного инструмента на другой.\n"
            "Без работы с этим — любая диета или режим временные.\n"
            "Ты уже знаешь это по опыту."
        ),
        "cycle": (
            "🔴 Что именно происходит у тебя:\n\n"
            "→ Стресс или усталость активируют тягу к еде\n"
            "→ Ты ешь — становится чуть легче\n"
            "→ Потом вина → ещё стресс → снова ешь\n"
            "→ Круг замкнулся"
        ),
        "solution": (
            "✅ Что реально помогает в твоём случае:\n\n"
            "→ Научиться замечать триггер до того, как рука потянулась\n"
            "→ Заменить еду другим быстрым инструментом снятия стресса\n"
            "→ Убрать провоцирующие ситуации заранее\n\n"
            "Это навык. Ему можно научиться за 3–4 недели."
        ),
        "tools": (
            "🛠 Что именно уберём в твоём случае:\n\n"
            "Для эмоционального едока работаем в трёх направлениях:\n\n"
            "1️⃣ Техники прерывания триггера — заметишь импульс до того, как съел\n"
            "2️⃣ Быстрые замены — 3–4 инструмента, которые дают облегчение без еды\n"
            "3️⃣ Структура питания — убираем ситуации, где срыв наиболее вероятен"
        ),
        "day3_content": (
            "📌 Топ-3 ошибки эмоционального едока:\n\n"
            "1. Держать дома «запасы» любимой еды — мозг знает, что она там есть\n"
            "2. Пропускать приёмы пищи — голод усиливает любой эмоциональный триггер\n"
            "3. Бороться с желанием силой воли — нужно не бороться, а переключать\n\n"
            "Ни одна из этих ошибок не про слабость. Все они про отсутствие инструмента."
        ),
        "social_proof": (
            "Анна, 34 года — такой же тип, минус 11 кг за 8 недель.\n"
            "Главное — перестала есть от стресса уже на 2-й неделе.\n\n"
            "Михаил, 31 год — похудел на 9 кг. Говорит, что впервые в жизни "
            "не сорвался ни разу за весь поток."
        ),
    },
    "social_hostage": {
        "emoji": "🍕",
        "name": "Социальный заложник",
        "problem": (
            "Наедине с собой ты держишься отлично.\n"
            "Но любое застолье, компания или праздник — и всё рушится.\n\n"
            "Тебе сложно отказывать и выбирать в социальных ситуациях.\n"
            "Это не слабость характера — это отсутствие конкретной стратегии."
        ),
        "cycle": (
            "🔴 Что именно происходит у тебя:\n\n"
            "→ Всю неделю держишься — приходит праздник\n"
            "→ Неловко отказывать, не хочешь выделяться\n"
            "→ Ешь и пьёшь «как все» — прогресс обнуляется\n"
            "→ Снова начинаешь с понедельника"
        ),
        "solution": (
            "✅ Что реально помогает в твоём случае:\n\n"
            "→ Конкретные сценарии для каждой ситуации: кафе, корпоратив, застолье\n"
            "→ Фразы-ответы, которые не обидят и не выделят тебя\n"
            "→ Правило 80/20 — как позволять себе без ущерба результату\n\n"
            "Это навык, а не сила воли."
        ),
        "tools": (
            "🛠 Что именно уберём в твоём случае:\n\n"
            "1️⃣ Социальные триггеры — научишься вести себя в компании без срывов\n"
            "2️⃣ Гибкая система питания — чтобы любой праздник не ломал прогресс\n"
            "3️⃣ Коммуникация — как отказывать так, чтобы никто не обижался"
        ),
        "day3_content": (
            "📌 Топ-3 ошибки социального заложника:\n\n"
            "1. Ждать «подходящего момента» — в социальной жизни его не будет\n"
            "2. Пытаться избегать мероприятий — это не жизнь\n"
            "3. Есть «про запас» перед выходом — это не работает\n\n"
            "Решение не в отказе от социальной жизни, а в правилах поведения внутри неё."
        ),
        "social_proof": (
            "Катя, 29 лет — похудела на 8 кг не отказываясь ни от одной вечеринки.\n"
            "Просто научилась другим правилам поведения на них.\n\n"
            "Дмитрий, 36 лет — за 8 недель минус 10 кг. Работа с клиентами в ресторанах каждую неделю — и ни одного срыва."
        ),
    },
    "metabolic_skeptic": {
        "emoji": "⚖️",
        "name": "Метаболический скептик",
        "problem": (
            "Ешь немного, стараешься, делаешь всё по инструкции.\n"
            "А результата нет. Или есть, но минимальный.\n\n"
            "Кажется, что с твоим организмом что-то не так.\n"
            "На самом деле — стандартные советы просто не подходят для твоей ситуации."
        ),
        "cycle": (
            "🔴 Что именно происходит у тебя:\n\n"
            "→ Ешь мало — вес стоит или растёт\n"
            "→ Добавляешь тренировки — всё равно нет результата\n"
            "→ Думаешь «мне не дано» или «сломан метаболизм»\n"
            "→ Опускаешь руки"
        ),
        "solution": (
            "✅ Что реально помогает в твоём случае:\n\n"
            "→ Точный расчёт твоего реального коридора калорий\n"
            "→ Перезапуск обмена веществ через правильный — не минимальный — дефицит\n"
            "→ Работа с гормональным фоном через режим сна и стресс\n\n"
            "Метаболизм не сломан. Ему просто дают неправильный сигнал."
        ),
        "tools": (
            "🛠 Что именно уберём в твоём случае:\n\n"
            "1️⃣ Точная калорийность — рассчитаем реальный дефицит именно для тебя\n"
            "2️⃣ Состав питания — соотношение БЖУ, которое запускает жиросжигание\n"
            "3️⃣ Режим — сон и стресс влияют на вес сильнее, чем многие думают"
        ),
        "day3_content": (
            "📌 Почему «мало ешь, но не худеешь» — это объяснимо:\n\n"
            "1. Хроническое недоедание замедляет метаболизм — тело переходит в режим экономии\n"
            "2. Скрытые калории в «здоровых» продуктах — орехи, масла, соусы\n"
            "3. Кортизол от стресса блокирует жиросжигание даже при дефиците\n\n"
            "Каждый из этих пунктов решаем. Просто нужен правильный подход."
        ),
        "social_proof": (
            "Ирина, 38 лет — 2 года не могла сдвинуться с места.\n"
            "За 8 недель минус 7 кг. Оказалось — ела слишком мало.\n\n"
            "Сергей, 33 года — тренировался 4 раза в неделю без результата.\n"
            "Поменяли питание — за поток минус 9 кг и плюс видимые мышцы."
        ),
    },
    "starter_stopper": {
        "emoji": "🔁",
        "name": "Стартер-стопер",
        "problem": (
            "В начале мотивация огромная — ты готов к любым жертвам.\n"
            "Но через 10–14 дней она испаряется, и всё начинается заново.\n\n"
            "Ты уже несколько раз проходил этот круг.\n"
            "Проблема не в тебе — проблема в том, что ты работаешь на силе воли.\n"
            "А она конечна у всех."
        ),
        "cycle": (
            "🔴 Что именно происходит у тебя:\n\n"
            "→ Мощный старт — мотивация на максимуме\n"
            "→ Через 1–2 недели энтузиазм падает\n"
            "→ Один пропуск → ощущение провала → бросаешь\n"
            "→ Через время — снова «с понедельника»"
        ),
        "solution": (
            "✅ Что реально помогает в твоём случае:\n\n"
            "→ Заменить мотивацию системой — она не исчезает\n"
            "→ Внешние точки контроля: куратор, группа, ежедневные касания\n"
            "→ Маленькие wins вместо большой цели — мозг остаётся вовлечённым\n\n"
            "Когда есть система и окружение — мотивация просто не нужна."
        ),
        "tools": (
            "🛠 Что именно уберём в твоём случае:\n\n"
            "1️⃣ Система вместо силы воли — ежедневная структура, которой легко следовать\n"
            "2️⃣ Куратор и группа — внешняя поддержка, которая не даёт выпасть\n"
            "3️⃣ Протокол срыва — что делать, если пропустил, чтобы не бросить совсем"
        ),
        "day3_content": (
            "📌 Почему стартер-стопер всегда останавливается на 2-й неделе:\n\n"
            "1. Первоначальная мотивация — эмоциональная, она быстро гаснет\n"
            "2. Нет системы на случай сложного дня — один пропуск = провал\n"
            "3. Цель слишком далеко — мозг не видит прогресса и теряет интерес\n\n"
            "Всё это решается не силой воли, а правильной архитектурой процесса."
        ),
        "social_proof": (
            "Олег, 27 лет — начинал 6 раз за 2 года.\n"
            "В потоке FitState впервые прошёл все 8 недель. Минус 8 кг.\n\n"
            "Настя, 31 год — говорит, что группа и куратор сделали то,\n"
            "что сила воли не смогла за 3 года попыток."
        ),
    },
}

# ── РАСЧЁТ ПРОГНОЗА ──
def calculate_forecast(weight: float, height: float, age: int, goal: str) -> dict:
    bmi = round(weight / ((height / 100) ** 2), 1)

    if goal == "fat":
        if bmi > 30:
            loss_min, loss_max = 8, 12
        elif bmi > 25:
            loss_min, loss_max = 6, 9
        else:
            loss_min, loss_max = 4, 7
        w_min = round(weight - loss_max)
        w_max = round(weight - loss_min)
        bmi_after = round((w_min + w_max) / 2 / ((height / 100) ** 2), 1)
        waist = f"-{loss_min + 1}–{loss_max - 1} см"
        return {
            "current_weight": weight, "current_bmi": bmi,
            "weight_range": f"{w_min}–{w_max} кг",
            "weight_loss": f"-{loss_min}–{loss_max} кг жира",
            "bmi_after": bmi_after, "waist": waist,
            "energy": "заметно вырастет к 3-й неделе",
            "goal_text": "убрать лишний жир"
        }
    elif goal == "muscle":
        gain_min, gain_max = 3, 6
        w_min = round(weight + gain_min)
        w_max = round(weight + gain_max)
        return {
            "current_weight": weight, "current_bmi": bmi,
            "weight_range": f"{w_min}–{w_max} кг",
            "weight_loss": f"+{gain_min}–{gain_max} кг мышц",
            "bmi_after": round(bmi + 0.8, 1), "waist": "без изменений",
            "energy": "вырастет к 2-й неделе",
            "goal_text": "набрать мышечную массу"
        }
    else:  # tone / health
        loss_min, loss_max = 3, 5
        w_min = round(weight - loss_max)
        w_max = round(weight - loss_min)
        bmi_after = round((w_min + w_max) / 2 / ((height / 100) ** 2), 1)
        return {
            "current_weight": weight, "current_bmi": bmi,
            "weight_range": f"{w_min}–{w_max} кг",
            "weight_loss": f"-{loss_min}–{loss_max} кг + рельеф",
            "bmi_after": bmi_after, "waist": f"-3–5 см",
            "energy": "вырастет уже к концу 1-й недели",
            "goal_text": "улучшить форму и рельеф"
        }


# ── ФОРМАТИРОВАНИЕ ЗАГЛУШКИ ВИЗУАЛА ──
def format_visual(forecast: dict, archetype_name: str) -> str:
    return (
        f"🖼 *ТЫ СЕЙЧАС*\n"
        f"Вес: {forecast['current_weight']} кг | ИМТ: {forecast['current_bmi']}\n"
        f"_{archetype_name}_\n"
        f"\n"
        f"⬇️ 8 недель программы FitState ⬇️\n"
        f"\n"
        f"🖼 *ТЫ ЧЕРЕЗ 2 МЕСЯЦА*\n"
        f"Вес: {forecast['weight_range']} | ИМТ: {forecast['bmi_after']}\n"
        f"_{forecast['weight_loss']}_"
    )


# ── /start ──
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    archetype_key = args[0] if args else None

    user_id = update.effective_user.id
    context.user_data["archetype"] = archetype_key
    context.user_data["user_id"] = user_id

    arch = ARCHETYPES.get(archetype_key)

    if arch:
        await update.message.reply_text(
            f"Привет! 👋\n\n"
            f"Я получил твои ответы с теста.\n"
            f"Сейчас дам тебе персональный разбор — займёт 1 минуту."
        )
        await update.message.reply_text(
            f"*{arch['emoji']} Твой тип: {arch['name']}*\n\n{arch['problem']}",
            parse_mode="Markdown"
        )
        await update.message.reply_text(arch["cycle"])
        await update.message.reply_text(arch["solution"])
    else:
        await update.message.reply_text(
            "Привет! 👋\n\n"
            "Я — FitState бот.\n"
            "Пройди тест на сайте, чтобы получить персональный разбор:\n\n"
            "👉 https://vezuncheg.github.io/fitstate"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Хочешь узнать — *каким ты можешь стать за 2 месяца*, если убрать именно эту причину?\n\n"
        "Я рассчитаю персонально под тебя — нужно пару вопросов.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Да, хочу узнать →", callback_data="start_params")],
            [InlineKeyboardButton("Может позже", callback_data="later")],
        ])
    )
    return ASK_GENDER


async def later_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "Хорошо! Когда будешь готов — просто напиши мне.\n\n"
        "А пока держи полезное: /menu"
    )
    return ConversationHandler.END


async def start_params_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "Отлично! Несколько вопросов — отвечай как есть.\n\n"
        "*Ты мужчина или женщина?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Мужчина", callback_data="gender_male"),
                InlineKeyboardButton("Женщина", callback_data="gender_female"),
            ]
        ])
    )
    return ASK_GENDER


async def gender_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["gender"] = "male" if "male" in update.callback_query.data else "female"
    await update.callback_query.message.reply_text(
        "*Сколько тебе лет?*\n\nНапиши число:",
        parse_mode="Markdown"
    )
    return ASK_AGE


async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text.strip())
        if not 10 <= age <= 100:
            raise ValueError
        context.user_data["age"] = age
        await update.message.reply_text(
            "*Твой текущий вес (кг)?*\n\nНапиши число, например: 84",
            parse_mode="Markdown"
        )
        return ASK_WEIGHT
    except ValueError:
        await update.message.reply_text("Напиши просто число, например: 28")
        return ASK_AGE


async def ask_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text.strip().replace(",", "."))
        if not 30 <= weight <= 300:
            raise ValueError
        context.user_data["weight"] = weight
        await update.message.reply_text(
            "*Рост (см)?*\n\nНапиши число, например: 178",
            parse_mode="Markdown"
        )
        return ASK_HEIGHT
    except ValueError:
        await update.message.reply_text("Напиши вес в кг, например: 84")
        return ASK_WEIGHT


async def ask_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        height = float(update.message.text.strip().replace(",", "."))
        if not 100 <= height <= 250:
            raise ValueError
        context.user_data["height"] = height
        await update.message.reply_text(
            "*Какой результат для тебя важнее всего?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Убрать лишний жир", callback_data="goal_fat")],
                [InlineKeyboardButton("Набрать мышечную массу", callback_data="goal_muscle")],
                [InlineKeyboardButton("Улучшить форму и рельеф", callback_data="goal_tone")],
                [InlineKeyboardButton("Стать здоровее и энергичнее", callback_data="goal_health")],
            ])
        )
        return ASK_GOAL
    except ValueError:
        await update.message.reply_text("Напиши рост в см, например: 178")
        return ASK_HEIGHT


async def ask_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    goal_map = {"goal_fat": "fat", "goal_muscle": "muscle", "goal_tone": "tone", "goal_health": "tone"}
    goal = goal_map.get(update.callback_query.data, "fat")
    context.user_data["goal"] = goal

    weight = context.user_data["weight"]
    height = context.user_data["height"]
    age = context.user_data["age"]
    archetype_key = context.user_data.get("archetype", "emotional_eater")
    arch = ARCHETYPES.get(archetype_key, ARCHETYPES["emotional_eater"])

    await update.callback_query.message.reply_text("Считаю твой результат... ⏳")

    forecast = calculate_forecast(weight, height, age, goal)
    context.user_data["forecast"] = forecast

    # Заглушка визуала
    visual_text = format_visual(forecast, arch["name"])
    await update.callback_query.message.reply_text(visual_text, parse_mode="Markdown")

    # Прогноз детально
    await update.callback_query.message.reply_text(
        f"*📊 Твой персональный прогноз на 8 недель:*\n\n"
        f"Текущий вес: *{forecast['current_weight']} кг*\n"
        f"ИМТ сейчас: *{forecast['current_bmi']}*\n\n"
        f"*Через 8 недель по программе FitState:*\n"
        f"→ Вес: *{forecast['weight_range']}* ({forecast['weight_loss']})\n"
        f"→ ИМТ: *{forecast['bmi_after']}*\n"
        f"→ Объём: *{forecast['waist']}*\n"
        f"→ Энергия: {forecast['energy']}\n\n"
        f"_Реалистичный прогноз на основе твоих параметров и средних результатов участников с похожим профилем._",
        parse_mode="Markdown"
    )

    await update.callback_query.message.reply_text(arch["tools"])

    # Оффер
    await send_offer(update.callback_query.message, context)
    return SHOW_RESULT


async def send_offer(message, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["offer_sent_at"] = datetime.now().isoformat()

    await message.reply_text(
        "🎯 *Хочешь достичь этого результата вместе с нами?*\n\n"
        "Сейчас открыт набор в поток FitState.\n"
        "Старт: *[дата потока]*  ·  Длительность: *8 недель*\n"
        "Формат: закрытый Telegram-канал + куратор + сообщество\n\n"
        "Специально для тебя — *скидка 20% действует 1 час* с этого момента.\n\n"
        "✅ Персональный план под твой архетип\n"
        "✅ Ежедневный контент в закрытом канале\n"
        "✅ Куратор на связи каждый день\n"
        "✅ Разбор прогресса еженедельно\n"
        "✅ Сообщество участников\n\n"
        "⏱ *Стоимость: [ЦЕНА] руб.* (скидка 20% — осталось 60 минут)",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Оплатить со скидкой →", callback_data="pay", url=PAYMENT_URL)],
            [InlineKeyboardButton("Расскажи подробнее", callback_data="more_info")],
        ])
    )

    # Планируем дожим через 1 час
    if context.job_queue:
        uid = context.user_data["user_id"]
        context.job_queue.run_once(dojim_hour, when=3600, data=uid, name=f"dojim_1h_{uid}")
        context.job_queue.run_once(dojim_day1, when=86400, data=uid, name=f"dojim_d1_{uid}")
        context.job_queue.run_once(dojim_day2, when=172800, data=uid, name=f"dojim_d2_{uid}")
        context.job_queue.run_once(dojim_day3, when=259200, data=uid, name=f"dojim_d3_{uid}")
        context.job_queue.run_once(dojim_day5, when=432000, data=uid, name=f"dojim_d5_{uid}")
        context.job_queue.run_once(dojim_day7, when=604800, data=uid, name=f"dojim_d7_{uid}")


async def more_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "Что тебе важнее всего узнать?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("О нас и команде", callback_data="info_about")],
            [InlineKeyboardButton("Программа подробно", callback_data="info_program")],
            [InlineKeyboardButton("Результаты участников", callback_data="info_results")],
        ])
    )


async def info_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "*О нас и команде*\n\n"
        "9 лет работы. 55 000+ участников из России, СНГ, Европы и США.\n"
        "Научный подход — алгоритмы на основе рекомендаций ВОЗ.\n\n"
        "Мы не продаём мотивацию.\n"
        "Мы меняем причину, по которой у тебя не получалось раньше.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Оплатить →", callback_data="pay", url=PAYMENT_URL)]
        ])
    )


async def info_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "*Программа по неделям:*\n\n"
        "📍 Неделя 1–2: диагностика, настройка питания и активности под тебя\n"
        "📍 Неделя 3–4: первые заметные результаты, работа с твоим архетипом\n"
        "📍 Неделя 5–6: закрепление, разбор сложных ситуаций\n"
        "📍 Неделя 7–8: финальный рывок + план на после потока",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Оплатить →", callback_data="pay", url=PAYMENT_URL)]
        ])
    )


async def info_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    arch_key = context.user_data.get("archetype", "emotional_eater")
    arch = ARCHETYPES.get(arch_key, ARCHETYPES["emotional_eater"])
    await update.callback_query.message.reply_text(
        f"*Результаты участников с похожим профилем:*\n\n{arch['social_proof']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Оплатить →", callback_data="pay", url=PAYMENT_URL)]
        ])
    )


# ── ДОЖИМ ──
async def dojim_hour(context: ContextTypes.DEFAULT_TYPE):
    uid = context.job.data
    await context.bot.send_message(
        chat_id=uid,
        text=(
            "Вижу, что ты ещё думаешь — это нормально.\n\n"
            "Скидка 20% истекла, но запись в поток ещё открыта.\n\n"
            "Давай я расскажу подробнее. Что тебе важнее всего узнать?"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("О нас и команде", callback_data="info_about")],
            [InlineKeyboardButton("Программа подробно", callback_data="info_program")],
            [InlineKeyboardButton("Результаты участников", callback_data="info_results")],
        ])
    )


async def dojim_day1(context: ContextTypes.DEFAULT_TYPE):
    uid = context.job.data
    await context.bot.send_message(
        chat_id=uid,
        text=(
            "*Кто мы и почему тебе можно доверять*\n\n"
            "9 лет работы. 55 000+ участников из России, СНГ, Европы и США.\n"
            "Научный подход — алгоритмы на основе рекомендаций ВОЗ.\n\n"
            "Мы не продаём мотивацию.\n"
            "Мы меняем причину, по которой у тебя не получалось раньше.\n\n"
            "👉 Записаться в поток →"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Записаться →", callback_data="pay", url=PAYMENT_URL)]
        ])
    )


async def dojim_day2(context: ContextTypes.DEFAULT_TYPE):
    uid = context.job.data
    await context.bot.send_message(
        chat_id=uid,
        text=(
            "*Что именно происходит в потоке — по неделям:*\n\n"
            "📍 Неделя 1–2: диагностика и настройка под тебя\n"
            "📍 Неделя 3–4: первые результаты, работа с архетипом\n"
            "📍 Неделя 5–6: закрепление, разбор сложных ситуаций\n"
            "📍 Неделя 7–8: финальный рывок + план на после\n\n"
            "👉 Записаться в поток →"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Записаться →", callback_data="pay", url=PAYMENT_URL)]
        ])
    )


async def dojim_day3(context: ContextTypes.DEFAULT_TYPE):
    uid = context.job.data
    # Получаем контент под архетип — используем данные из хранилища
    await context.bot.send_message(
        chat_id=uid,
        text=(
            "Полезное специально для тебя.\n\n"
            "Отправь /content чтобы получить материал под твой тип."
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Записаться в поток →", callback_data="pay", url=PAYMENT_URL)]
        ])
    )


async def dojim_day5(context: ContextTypes.DEFAULT_TYPE):
    uid = context.job.data
    await context.bot.send_message(
        chat_id=uid,
        text=(
            "*Результаты участников прямо сейчас:*\n\n"
            "🔥 Поток идёт. Люди с похожими целями уже видят результат.\n\n"
            "Ты можешь присоединиться к следующему.\n\n"
            "👉 Записаться →"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Записаться →", callback_data="pay", url=PAYMENT_URL)]
        ])
    )


async def dojim_day7(context: ContextTypes.DEFAULT_TYPE):
    uid = context.job.data
    await context.bot.send_message(
        chat_id=uid,
        text=(
            "*Набор в поток закрывается через 24 часа.*\n\n"
            "После этого — только следующий поток через 2 месяца.\n\n"
            "Ты уже знаешь свою причину.\n"
            "У тебя есть прогноз.\n"
            "Осталось один шаг.\n\n"
            "👉 Успеть записаться →"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Успеть записаться →", callback_data="pay", url=PAYMENT_URL)]
        ])
    )


# ── /menu ──
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    arch_key = context.user_data.get("archetype")
    forecast = context.user_data.get("forecast")
    arch = ARCHETYPES.get(arch_key)

    text = "📋 *Главное меню FitState*\n\n"
    if arch and forecast:
        text += (
            f"Твой тип: *{arch['emoji']} {arch['name']}*\n"
            f"Прогноз: {forecast['weight_range']} за 8 недель\n\n"
        )
    text += "Выбери что хочешь сделать:"

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Мой результат", callback_data="my_result")],
            [InlineKeyboardButton("📖 О программе", callback_data="info_program")],
            [InlineKeyboardButton("🏆 Результаты участников", callback_data="info_results")],
            [InlineKeyboardButton("💳 Записаться в поток", callback_data="pay", url=PAYMENT_URL)],
        ])
    )


async def my_result_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    arch_key = context.user_data.get("archetype")
    forecast = context.user_data.get("forecast")
    arch = ARCHETYPES.get(arch_key)

    if arch and forecast:
        visual = format_visual(forecast, arch["name"])
        await update.callback_query.message.reply_text(visual, parse_mode="Markdown")
        await update.callback_query.message.reply_text(
            f"*Твой тип:* {arch['emoji']} {arch['name']}\n"
            f"*Прогноз на 8 недель:* {forecast['weight_range']} ({forecast['weight_loss']})",
            parse_mode="Markdown"
        )
    else:
        await update.callback_query.message.reply_text(
            "Пройди тест на сайте, чтобы получить свой результат:\n"
            "👉 https://vezuncheg.github.io/fitstate"
        )


def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_GENDER: [
                CallbackQueryHandler(start_params_callback, pattern="^start_params$"),
                CallbackQueryHandler(later_callback, pattern="^later$"),
                CallbackQueryHandler(gender_callback, pattern="^gender_"),
            ],
            ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            ASK_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_weight)],
            ASK_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_height)],
            ASK_GOAL: [CallbackQueryHandler(ask_goal, pattern="^goal_")],
            SHOW_RESULT: [],
        },
        fallbacks=[CommandHandler("menu", menu)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(more_info_callback, pattern="^more_info$"))
    app.add_handler(CallbackQueryHandler(info_about, pattern="^info_about$"))
    app.add_handler(CallbackQueryHandler(info_program, pattern="^info_program$"))
    app.add_handler(CallbackQueryHandler(info_results, pattern="^info_results$"))
    app.add_handler(CallbackQueryHandler(my_result_callback, pattern="^my_result$"))

    logger.info("FitState bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
