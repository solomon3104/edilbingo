# main.py

import asyncio
import logging
import random
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN", "8991264173:AAFvK1SoSWmvVphY4FmESa09JgRbWaI75ag")
WEB_APP_URL = "https://solomon3104.github.io/edilbingo/bingoapp/"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

class BingoEngine:
    @staticmethod
    def generate_card(card_id: int):
        rng = random.Random(card_id * 99991)
        card = {
            'B': sorted(rng.sample(range(1, 16), 5)),
            'I': sorted(rng.sample(range(16, 31), 5)),
            'N': sorted(rng.sample(range(31, 46), 5)),
            'G': sorted(rng.sample(range(46, 61), 5)),
            'O': sorted(rng.sample(range(61, 76), 5))
        }
        card['N'][2] = 'FREE'
        return card

    @staticmethod
    def check_win(card: dict, drawn_balls: list):
        drawn = set(drawn_balls)
        drawn.add('FREE')

        for i in range(5):
            if all(card[col][i] in drawn for col in ['B', 'I', 'N', 'G', 'O']):
                return True, f"አግድም መስመር {i+1} (Horizontal)"

        for col in ['B', 'I', 'N', 'G', 'O']:
            if all(num in drawn for num in card[col]):
                return True, f"ቋሚ መስመር {col} (Vertical)"

        d1 = [card['B'][0], card['I'][1], card['N'][2], card['G'][3], card['O'][4]]
        d2 = [card['B'][4], card['I'][3], card['N'][2], card['G'][1], card['O'][0]]
        if all(n in drawn for n in d1): 
            return True, "ሰያፍ መስመር (Diagonal TL-BR)"
        if all(n in drawn for n in d2): 
            return True, "ሰያፍ መስመር (Diagonal BL-TR)"

        corners = [card['B'][0], card['O'][0], card['B'][4], card['O'][4]]
        if all(c in drawn for c in corners): 
            return True, "4ቱ መአዘኖች (4 Corners)"

        return False, None

class GameManager:
    def __init__(self):
        self.phase = "SELECTION"
        self.timer = 30
        self.sold_cards = set()
        self.locked_cards = set()
        self.drawn_balls = []
        self.all_balls = list(range(1, 76))
        random.shuffle(self.all_balls)
        self.winners = []

    async def run_loop(self):
        while True:
            self.phase = "SELECTION"
            self.sold_cards.clear()
            self.locked_cards.clear()
            self.drawn_balls.clear()
            self.winners.clear()
            self.all_balls = list(range(1, 76))
            random.shuffle(self.all_balls)

            for t in range(30, 0, -1):
                self.timer = t
                await asyncio.sleep(1)

            self.phase = "PLAYING"
            self.timer = 0
            
            while self.phase == "PLAYING" and self.all_balls:
                ball = self.all_balls.pop(0)
                self.drawn_balls.append(ball)
                await asyncio.sleep(3)

                if self.winners:
                    self.phase = "WINNER"
                    break

            if self.phase == "WINNER":
                for t in range(15, 0, -1):
                    self.timer = t
                    await asyncio.sleep(1)

game_manager = GameManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(game_manager.run_loop())
    asyncio.create_task(dp.start_polling(bot))
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/game-state")
async def get_state():
    total_cards = len(game_manager.sold_cards)
    derash_pool = round(total_cards * 10.0 * 0.80, 2)
    prize_per_winner = round(derash_pool / len(game_manager.winners), 2) if game_manager.winners else 0.0

    return {
        "phase": game_manager.phase,
        "timer": game_manager.timer,
        "sold_count": total_cards,
        "drawn_balls": game_manager.drawn_balls,
        "current_ball": game_manager.drawn_balls[-1] if game_manager.drawn_balls else None,
        "recent_balls": game_manager.drawn_balls[-4:-1][::-1] if len(game_manager.drawn_balls) > 1 else [],
        "derash": derash_pool,
        "players": max(total_cards, 1),
        "winners": game_manager.winners,
        "prize_per_winner": prize_per_winner,
        "locked_cards": list(game_manager.locked_cards)
    }

@app.get("/api/get-card-data")
async def get_card_data(card_id: int):
    card = BingoEngine.generate_card(card_id)
    return {"card_id": card_id, "card": card}

@app.post("/api/select-card")
async def select_card(request: Request):
    data = await request.json()
    card_id = data.get("card_id")
    if game_manager.phase == "SELECTION":
        game_manager.sold_cards.add(card_id)
        return {"status": "success"}
    return {"status": "game_already_started"}

@app.post("/api/claim-bingo")
async def claim_bingo(request: Request):
    data = await request.json()
    card_id = data.get("card_id")
    player_name = data.get("player_name", "ተጫዋች")
    
    if card_id in game_manager.locked_cards:
        return {
            "status": "locked",
            "is_winner": False,
            "message": f"ካርድ #{card_id} በስህተት ጥሪ ምክንያት ታስሯል!"
        }

    card = BingoEngine.generate_card(card_id)
    is_win, pattern = BingoEngine.check_win(card, game_manager.drawn_balls)

    if is_win and game_manager.phase in ["PLAYING", "WINNER"]:
        if not any(w["card_id"] == card_id for w in game_manager.winners):
            game_manager.winners.append({
                "name": player_name,
                "card_id": card_id,
                "pattern": pattern
            })
            game_manager.phase = "WINNER"
        return {"status": "success", "is_winner": True}
    else:
        game_manager.locked_cards.add(card_id)
        return {
            "status": "false_bingo",
            "is_winner": False,
            "message": f"ያልተሟላ BINGO! ካርድ #{card_id} ከጨዋታ ውጭ ሆኗል (ታስሯል)!"
        }

@dp.message(Command("start"))
@dp.message(Command("play"))
async def play_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 PLAY | 10 ብር", web_app=WebAppInfo(url=f"{WEB_APP_URL}?room=regular"))],
        [InlineKeyboardButton(text="🔥 SuperBingo | 50 ብር", web_app=WebAppInfo(url=f"{WEB_APP_URL}?room=superbingo"))]
    ])
    await message.answer("🕹 **እንኳን ወደ EdilBingo በደህና መጡ!**\nእባክዎን መጫወት የሚፈልጉበትን ክፍል ይምረጡ:", reply_markup=keyboard, parse_mode="Markdown")

@dp.message(Command("balance"))
async def balance_cmd(message: types.Message):
    await message.answer("💳 **የእርስዎ ቀሪ ሂሳብ:** 500.00 ETB")

@dp.message(Command("instructions"))
async def instructions_cmd(message: types.Message):
    info = (
        "📖 **የቢንጎ ጨዋታ ህጎች:**\n\n"
        "1️⃣ **የሽልማት መጠን:** ከጠቅላላ የተሸጡ ካርዶች 80% ክፍያ ወደ ደራሽ ሂሳብ ይገባል።\n"
        "2️⃣ **ከአንድ በላይ አሸናፊዎች:** ከአንድ በላይ ተጫዋቾች በአንድ ጊዜ ቢንጎ ካሉ ደራሹ ለአሸናፊዎች እኩል ይከፋፈላል።\n"
        "3️⃣ **የስህተት ቢንጎ (ታስሯል):** ያልተሟላ መስመር ላይ BINGO ካሉ የተሳሳተው ካርድ ብቻ ይታሰራል፤ ሌላኛው ካርድዎ ይቀጥላል።"
    )
    await message.answer(info, parse_mode="Markdown")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
