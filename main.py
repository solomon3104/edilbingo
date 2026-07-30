import asyncio
import logging
import random
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ==========================================
# 1. Configuration
# ==========================================
BOT_TOKEN = "8991264173:AAFvK1SoSWmvVphY4FmESa09JgRbWaI75ag"
WEB_APP_URL = "https://solomon3104.github.io/edilbingo/bingoapp/"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

# CORS Config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. Advanced Unique Bingo Engine Logic
# ==========================================
class BingoEngine:
    @staticmethod
    def generate_card(card_id: int):
        # Using card_id as a unique seed to guarantee every single card 
        # is completely different in numbers and layout positions.
        rng = random.Random(card_id)
        card = {
            'B': rng.sample(range(1, 16), 5),
            'I': rng.sample(range(16, 31), 5),
            'N': rng.sample(range(31, 46), 5),
            'G': rng.sample(range(46, 61), 5),
            'O': rng.sample(range(61, 76), 5)
        }
        card['N'][2] = 'FREE'
        return card

    @staticmethod
    def check_regular_win(card: dict, drawn_balls: list) -> bool:
        drawn = set(drawn_balls)
        drawn.add('FREE')

        # Horizontal
        for i in range(5):
            if all(card[col][i] in drawn for col in ['B', 'I', 'N', 'G', 'O']):
                return True

        # Vertical
        for col in ['B', 'I', 'N', 'G', 'O']:
            if all(num in drawn for num in card[col]):
                return True

        # Diagonal
        d1 = [card['B'][0], card['I'][1], card['N'][2], card['G'][3], card['O'][4]]
        d2 = [card['B'][4], card['I'][3], card['N'][2], card['G'][1], card['O'][0]]
        if all(n in drawn for n in d1) or all(n in drawn for n in d2):
            return True

        # 4 Corners
        corners = [card['B'][0], card['O'][0], card['B'][4], card['O'][4]]
        if all(c in drawn for c in corners):
            return True

        return False

    @staticmethod
    def check_superbingo_win(card: dict, drawn_balls: list) -> bool:
        drawn = set(drawn_balls)
        drawn.add('FREE')

        for col in ['B', 'I', 'N', 'G', 'O']:
            for num in card[col]:
                if num not in drawn:
                    return False
        return True

# ==========================================
# 3. FastAPI WebApp Endpoints
# ==========================================
@app.get("/api/get-card-data")
async def get_card_data(card_id: int):
    card = BingoEngine.generate_card(card_id)
    return {"card_id": card_id, "card": card}

@app.post("/api/verify-bingo")
async def verify_bingo(request: Request):
    data = await request.json()
    room_type = data.get("room_type", "regular")
    card_data = data.get("card")
    drawn_balls = data.get("drawn_balls", [])

    if room_type == "superbingo":
        is_winner = BingoEngine.check_superbingo_win(card_data, drawn_balls)
    else:
        is_winner = BingoEngine.check_regular_win(card_data, drawn_balls)

    return {"is_winner": is_winner}

# ==========================================
# 4. Telegram Bot Commands
# ==========================================
@dp.message(Command("start"))
@dp.message(Command("play"))
async def play_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🎮 PLAY | 10 ብር",
                web_app=WebAppInfo(url=f"{WEB_APP_URL}?room=regular")
            )
        ],
        [
            InlineKeyboardButton(
                text="🔥 SuperBingo | 50 ብር",
                web_app=WebAppInfo(url=f"{WEB_APP_URL}?room=superbingo")
            )
        ]
    ])
    await message.answer(
        "🕹 **PLAY IN:**\nChoose a room to join the game:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(Command("balance"))
async def balance_cmd(message: types.Message):
    await message.answer("💳 **የእርስዎ ቀሪ ሂሳብ:** 500.00 ETB")

@dp.message(Command("deposit"))
async def deposit_cmd(message: types.Message):
    await message.answer("📥 **ገንዘብ ለማስገባት (Deposit):**\nእባክዎን የቴሌግራም ብር ወይም የባንክ አማራጭ ይምረጡ።")

@dp.message(Command("withdraw"))
async def withdraw_cmd(message: types.Message):
    await message.answer("📤 **ገንዘብ ለማውጣት (Withdraw):**\nማውጣት የሚፈልጉትን መጠን ያስገቡ።")

@dp.message(Command("history"))
async def history_cmd(message: types.Message):
    await message.answer("📜 **የግብይት ታሪክ:**\nምንም አይነት ግብይት አልተመዘገበም።")

@dp.message(Command("instructions"))
async def instructions_cmd(message: types.Message):
    info = (
        "📖 **የቢንጎ ጨዋታ ህጎች:**\n\n"
        "1️⃣ **መደበኛ ጨዋታ (10 ብር):**\n"
        "• እስከ 450 ካርዶች መምረጫ።\n"
        "• ህግ: 1 አግድም/ቋሚ/ሰያፍ መስመር ወይም 4ቱ መአዘኖች ሲዘጋ BINGO ማለት ይችላሉ።\n\n"
        "2️⃣ **SuperBingo (50 ብር):**\n"
        "• በሳምንት 2 ቀን ከቀኑ 9:00 ሰአት የሚጀመር።\n"
        "• እስከ 900 ካርዶች መምረጫ።\n"
        "• ህግ: ሙሉ በሙሉ (Full House) ሲዘጋ ብቻ።"
    )
    await message.answer(info, parse_mode="Markdown")

@dp.message(Command("register"))
async def register_cmd(message: types.Message):
    await message.answer("✅ በስኬት ተመዝግበዋል!")

# ==========================================
# 5. App Starter
# ==========================================
async def main():
    logging.basicConfig(level=logging.INFO)
    print("EdilBingo Bot is starting...")
    
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    
    asyncio.create_task(server.serve())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

