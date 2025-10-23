import telebot, yfinance as yf, pandas as pd, numpy as np
from telebot import types

# ====== YOUR TELEGRAM BOT TOKEN ======
BOT_TOKEN = "8485378124:AAEdXPPRKPA6-1SOA2HCXJjeA9cGa-hCWdI"
bot = telebot.TeleBot(BOT_TOKEN)

# ====== FOREX PAIRS ======
pairs = {"EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"JPY=X","AUD/USD":"AUDUSD=X"}
time_options = ["1m","5m","15m"]

# ====== INDICATORS ======
def ema(series, span): return series.ewm(span=span, adjust=False).mean()
def rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0); down = -delta.clip(upper=0)
    ma_up = up.rolling(period).mean(); ma_down = down.rolling(period).mean()
    rs = ma_up / ma_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))
def macd(series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast); ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow; signal_line = ema(macd_line, signal)
    return macd_line, signal_line

# ====== FETCH DATA ======
def fetch_forex_data(symbol, interval="1m"):
    try:
        data = yf.download(tickers=symbol, period="1d", interval=interval, progress=False)
        data = data.rename(columns={"Open":"o","High":"h","Low":"l","Close":"c"})
        return data.dropna()
    except:
        return None

# ====== SIGNAL STRATEGY ======
def generate_signal(df):
    df["EMA20"]=ema(df["c"],20); df["EMA50"]=ema(df["c"],50); df["RSI14"]=rsi(df["c"],14)
    macd_line, signal_line = macd(df["c"]); df["MACD_Line"]=macd_line; df["Signal_Line"]=signal_line
    last = df.iloc[-1]
    buy = last["EMA20"]>last["EMA50"] and last["RSI14"]>55 and last["MACD_Line"]>last["Signal_Line"]
    sell = last["EMA20"]<last["EMA50"] and last["RSI14"]<45 and last["MACD_Line"]<last["Signal_Line"]
    if buy: return "🔥 STRONG BUY 📈"
    elif sell: return "⚡ STRONG SELL 📉"
    else: return "WAIT ⚖️ (No Clear Signal)"

# ====== TELEGRAM HANDLERS ======
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for p in pairs.keys(): markup.add(types.KeyboardButton(p))
    bot.send_message(message.chat.id,"💱 Select forex pair 👇",reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in pairs)
def select_pair(m):
    pair = m.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for t in time_options: markup.add(types.KeyboardButton(t))
    bot.send_message(m.chat.id,f"{pair} selected.\nNow choose timeframe 👇",reply_markup=markup)
    bot.register_next_step_handler(m, lambda msg: send_signal(msg,pair))

def send_signal(msg,pair):
    if msg.text not in time_options:
        bot.send_message(msg.chat.id,"⚠️ Please select a valid timeframe (1m / 5m / 15m).")
        return
    data = fetch_forex_data(pairs[pair],msg.text)
    if data is None or data.empty:
        bot.send_message(msg.chat.id,"⚠️ Error fetching data. Try again later.")
        return
    signal = generate_signal(data)
    price = float(data["c"].iloc[-1])
    bot.send_message(msg.chat.id,f"📊 *VIP FOREX Signal*\nPair: {pair}\nTimeframe: {msg.text}\nPrice: {price:.5f}\nSignal: {signal}",parse_mode="Markdown")

print("🚀 VIP Forex Bot Running...")
bot.polling(non_stop=True)
