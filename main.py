import asyncio
import logging
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton, CallbackQuery, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.bot import DefaultBotProperties

logging.basicConfig(level=logging.INFO)

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8624246601:AAEiMrovuM7BqLjj9tOCOC6KprsXlnMWY-g'
OWNER_ID = 8777986259  
FILES = {'bal': 'balances.json', 'itm': 'items.json', 'adm': 'admins.json', 'ban': 'banned.json'}

def load_json(key, default):
    if os.path.exists(FILES[key]):
        with open(FILES[key], 'r', encoding='utf-8') as f: return json.load(f)
    return default

def save_json(key, data):
    with open(FILES[key], 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

user_balances = load_json('bal', {})
items = load_json('itm', [])
admins = load_json('adm', [OWNER_ID])
banned_users = load_json('ban', [])

# --- СОСТОЯНИЯ ---
class FSMA(StatesGroup):
    name = State(); desc = State(); price = State(); cont = State()
    gv_id = State(); gv_am = State(); bn_id = State()
    ad_id = State(); rm_id = State()

class FSMU(StatesGroup):
    qr = State()

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

def is_adm(uid): return uid in admins or uid == OWNER_ID

def main_kb(uid):
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="👤 Профиль"))
    b.row(KeyboardButton(text="🆘 Поддержка"), KeyboardButton(text="🏠 Меню"))
    if is_adm(uid): b.row(KeyboardButton(text="⚙️ Админ-панель"))
    return b.as_markup(resize_keyboard=True)

# --- ОСНОВНОЕ ---
@dp.message(Command("start"))
@dp.message(F.text == "🏠 Меню")
async def start(m: types.Message):
    if m.from_user.id in banned_users: return
    t = f"👋 Здравствуйте, {m.from_user.first_name}!\nВы попали в бота <b>Liberty IVIAX</b>!\n\nЗдесь вы можете приобрести токены по самым приятным ценам!"
    await m.answer(t, reply_markup=main_kb(m.from_user.id))

@dp.message(F.text == "👤 Профиль")
async def prof(m: types.Message):
    u = str(m.from_user.id); b = user_balances.get(u, 0.0)
    await m.answer(f"👤 <b>Профиль</b>\n🆔 ID: <code>{u}</code>\n💰 Баланс: <b>{b}$</b>")

# --- МАГАЗИН ---
@dp.message(F.text == "🛒 Магазин")
async def shop(m: types.Message):
    if not items: return await m.answer("🛒 Магазин пуст.")
    for i, it in enumerate(items):
        kb = InlineKeyboardBuilder().row(InlineKeyboardButton(text=f"Купить за {it['price']}$", callback_data=f"buy_{i}"))
        await m.answer(f"📦 <b>{it['name']}</b>\n💰 Цена: {it['price']}$", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def buy_call(callback: CallbackQuery):
    idx = int(callback.data.split("_")[-1])
    u, it = str(callback.from_user.id), items[idx]
    bal = float(user_balances.get(u, 0.0))
    if bal >= float(it['price']):
        user_balances[u] = round(bal - float(it['price']), 2); save_json('bal', user_balances)
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        txt = f"👤 <b>{it['name']}</b>\n\n{it['desc']}\n\n⚠️ <b>Внимание: используйте аккаунт сразу!</b>\n\n💰 Цена: {it['price']}$\n📅 Куплен: {now}"
        kb = InlineKeyboardBuilder().row(InlineKeyboardButton(text="🔑 Токен", callback_data=f"tk_{idx}"), InlineKeyboardButton(text="📱 QR", callback_data=f"qr_{idx}"))
        await callback.message.answer(txt, reply_markup=kb.as_markup()); await callback.answer()
    else: await callback.answer("❌ Недостаточно средств!", show_alert=True)

# --- АДМИН ПАНЕЛЬ ---
@dp.message(F.text == "⚙️ Админ-панель")
async def admin_root(m: types.Message):
    if not is_adm(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Товар", callback_data="adm_add"))
    kb.row(InlineKeyboardButton(text="💰 Баланс", callback_data="adm_bal"))
    kb.row(InlineKeyboardButton(text="🚫 Бан", callback_data="adm_ban"))
    kb.row(InlineKeyboardButton(text="🗑 Очистить", callback_data="adm_clr"))
    if m.from_user.id == OWNER_ID:
        kb.row(InlineKeyboardButton(text="👑 +Админ", callback_data="adm_p_a"))
        kb.row(InlineKeyboardButton(text="❌ -Админ", callback_data="adm_m_a"))
    await m.answer("🛠 <b>Панель администратора</b>", reply_markup=kb.as_markup())

# ВЫДАЧА БАЛАНСА
@dp.callback_query(F.data == "adm_bal")
async def ab_1(c: CallbackQuery, state: FSMContext):
    await c.message.answer("Введите ID:"); await state.set_state(FSMA.gv_id); await c.answer()

@dp.message(FSMA.gv_id)
async def ab_2(m: types.Message, state: FSMContext):
    await state.update_data(tid=m.text); await m.answer("Сумма:"); await state.set_state(FSMA.gv_am)

@dp.message(FSMA.gv_am)
async def ab_3(m: types.Message, state: FSMContext):
    d = await state.get_data(); u = d['tid']
    user_balances[u] = round(float(user_balances.get(u, 0.0)) + float(m.text), 2)
    save_json('bal', user_balances); await m.answer(f"✅ Баланс {u} обновлен!"); await state.clear()

# ДОБАВЛЕНИЕ ТОВАРА
@dp.callback_query(F.data == "adm_add")
async def ai_1(c: CallbackQuery, state: FSMContext):
    await c.message.answer("Имя аккаунта:"); await state.set_state(FSMA.name); await c.answer()

@dp.message(FSMA.name)
async def ai_2(m: types.Message, state: FSMContext):
    await state.update_data(n=m.text); await m.answer("Данные:"); await state.set_state(FSMA.desc)

@dp.message(FSMA.desc)
async def ai_3(m: types.Message, state: FSMContext):
    await state.update_data(d=m.text); await m.answer("Цена:"); await state.set_state(FSMA.price)

@dp.message(FSMA.price)
async def ai_4(m: types.Message, state: FSMContext):
    await state.update_data(p=m.text); await m.answer("Файл или текст:"); await state.set_state(FSMA.cont)

@dp.message(FSMA.cont)
async def ai_5(m: types.Message, state: FSMContext):
    d = await state.get_data(); f_id, f_t = m.text, "text"
    if m.document: f_id, f_t = m.document.file_id, "document"
    items.append({"name": d['n'], "desc": d['d'], "price": d['p'], "content": f_id, "type": f_t})
    save_json('itm', items); await state.clear(); await m.answer("✅ Товар добавлен!")

# БАН
@dp.callback_query(F.data == "adm_ban")
async def an_1(c: CallbackQuery, state: FSMContext):
    await c.message.answer("ID для бана:"); await state.set_state(FSMA.bn_id); await c.answer()

@dp.message(FSMA.bn_id)
async def an_2(m: types.Message, state: FSMContext):
    uid = int(m.text); banned_users.append(uid); save_json('ban', banned_users)
    await m.answer(f"🚫 Пользователь {uid} забанен!"); await state.clear()

# УПРАВЛЕНИЕ АДМИНАМИ
@dp.callback_query(F.data == "adm_p_a")
async def ap_1(c: CallbackQuery, state: FSMContext):
    await c.message.answer("ID нового админа:"); await state.set_state(FSMA.ad_id); await c.answer()

@dp.message(FSMA.ad_id)
async def ap_2(m: types.Message, state: FSMContext):
    admins.append(int(m.text)); save_json('adm', admins); await m.answer("✅ Админ добавлен!"); await state.clear()

@dp.callback_query(F.data == "adm_m_a")
async def am_1(c: CallbackQuery, state: FSMContext):
    await c.message.answer("ID для снятия:"); await state.set_state(FSMA.rm_id); await c.answer()

@dp.message(FSMA.rm_id)
async def am_2(m: types.Message, state: FSMContext):
    uid = int(m.text)
    if uid in admins: admins.remove(uid); save_json('adm', admins)
    await m.answer("❌ Админ снят."); await state.clear()

# ОЧИСТКА
@dp.callback_query(F.data == "adm_clr")
async def ac_clr(c: CallbackQuery):
    items.clear(); save_json('itm', items); await c.answer("Магазин очищен!")

# ВХОД
@dp.callback_query(F.data.startswith("tk_"))
async def get_tk(c: CallbackQuery):
    it = items[int(c.data.split("_")[-1])]
    if it['type'] == 'document': await bot.send_document(c.from_user.id, it['content'])
    else: await c.message.answer(f"🔑 Токен: <code>{it['content']}</code>")
    await c.answer()

@dp.callback_query(F.data.startswith("qr_"))
async def qr_req(c: CallbackQuery, state: FSMContext):
    await c.message.answer("📸 Скиньте фото QR:"); await state.set_state(FSMU.qr); await c.answer()

@dp.message(FSMU.qr, F.photo)
async def qr_step2(m: types.Message, state: FSMContext):
    kb = InlineKeyboardBuilder().row(InlineKeyboardButton(text="✅ Ок", callback_data=f"ok_{m.from_user.id}"), InlineKeyboardButton(text="❌ Нет", callback_data=f"no_{m.from_user.id}"))
    await bot.send_photo(OWNER_ID, m.photo[-1].file_id, caption=f"QR от <code>{m.from_user.id}</code>", reply_markup=kb.as_markup())
    await m.answer("⏳ Отправлено админу."); await state.clear()

@dp.callback_query(F.data.startswith(("ok_", "no_")))
async def adm_dec(c: CallbackQuery):
    act, uid = c.data.split("_")
    msg = "✅ Вход подтвержден!" if act == "ok" else "❌ Отклонено."
    await bot.send_message(int(uid), msg); await c.message.edit_caption(caption=f"Результат: {act}"); await c.answer()

@dp.message(F.text == "🆘 Поддержка")
async def supp(m: types.Message): await m.answer("👨‍💻 Поддержка: @imLiberral")

async def main():
    await bot.delete_webhook(drop_pending_updates=True); await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
  
