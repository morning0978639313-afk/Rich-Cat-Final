import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 系統環境設定 (鎖定 v1.19.0 穩定版排版)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 紅綠燈戰術終端", layout="wide")
st_autorefresh(interval=60 * 1000, key="datarefresh") 

# 自定義 CSS 讓標題更醒目 (適配舊版 Streamlit)
st.markdown("""<style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .status-box { padding: 10px; border-radius: 5px; margin: 5px 0; }
</style>""", unsafe_allow_html=True)

st.title("🐱 RICH CAT 紅綠燈戰術終端")
st.write(f"🕒 數據更新時間：`{datetime.now(pytz.timezone('Asia/Taipei')).strftime('%H:%M:%S')}`")

# 2. 暴力資料引擎 V5：修復 0 值與欄位類型問題
@st.cache_data(ttl=60)
def get_war_room_data():
    try:
        dl = DataLoader()
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=40)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            # 徹底去重並格式化
            df = df.loc[:, ~df.columns.duplicated()].copy()
            df.columns = [str(c).strip().lower() for c in df.columns]
            rename_map = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}
            df = df.rename(columns=rename_map)
            
            # 修正數值類型，避免顯示為 0
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 過濾無效資料
            df = df[df['Close'] > 0]
            
            # 均線系統：5MA, 10MA, 20MA
            df['5MA'] = df['Close'].rolling(window=5).mean()
            df['10MA'] = df['Close'].rolling(window=10).mean()
            df['20MA'] = df['Close'].rolling(window=20).mean()
            return df
    except: pass
    return None

df = get_war_room_data()

# 3. 完整 40 指標戰術核心
if df is not None and len(df) >= 3:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    day_h, day_l, open_p = df['High'].max(), df['Low'].min(), df.iloc[0]['Open']
    diff = day_h - day_l

    # --- 買進信號判定 (20條精華) ---
    b_sigs = []
    if all(df['Close'].tail(3) > df['Open'].tail(3)): b_sigs.append("B:實體連三紅") # 指標14
    if last['Close'] >= (day_l + diff * 0.382): b_sigs.append("B:0.382支撐") # 指標1/2
    if last['Close'] > last['5MA']: b_sigs.append("B:站上5MA") # 指標11
    if last['Close'] > last['20MA']: b_sigs.append("B:站上20MA") # 指標12
    if last['Volume'] > 5000: b_sigs.append("B:單根破5000口") # 指標20
    if last['Close'] > open_p: b_sigs.append("B:守穩開盤價") # 指標7/8
    if last['Close'] > prev['High'] and last['Volume'] > prev['Volume']: b_sigs.append("B:帶量突前高") # 指標4

    # --- 賣出信號判定 (20條精華) ---
    s_sigs = []
    if all(df['Close'].tail(3) < df['Open'].tail(3)): s_sigs.append("S:實體連三綠") # 指標14
    if last['Close'] < (day_l + diff * 0.618): s_sigs.append("S:跌破0.618") # 指標1
    if last['Close'] < last['5MA']: s_sigs.append("S:跌破5MA") # 指標11
    if last['Close'] < open_p: s_sigs.append("S:開盤價之下") # 指標8
    if last['High'] < prev['High']: s_sigs.append("S:高點降低") # 指標4
    if last['Volume'] > 5000 and last['Close'] < last['Open']: s_sigs.append("S:爆量收黑") # 指標19

    # --- 燈號計算 (互斥邏輯) ---
    r_light = min(3, (1 if b_sigs else 0) + (len(b_sigs) // 2)) # 調整權重讓燈更容易亮
    g_light = min(3, (1 if s_sigs else 0) + (len(s_sigs) // 2))
    f_red = max(0, r_light - g_light)
    f_green = max(0, g_light - r_light)

    # 4. 版面配置：戰情監控區 (適配 v1.19.0)
    # 第一排：燈號與信號列表
    t1, t2 = st.columns(2)
    with t1:
        st.markdown(f'<p class="big-font" style="color:red;">🔴 買進強勢度</p>', unsafe_allow_html=True)
        st.write("🔴" * f_red + "⚪" * (3 - f_red))
        if b_sigs: st.success("已達成：" + " | ".join(b_sigs))
    with t2:
        st.markdown(f'<p class="big-font" style="color:green;">🟢 賣出強勢度</p>', unsafe_allow_html=True)
        st.write("🟢" * f_green + "⚪" * (3 - f_green))
        if s_sigs: st.error("已達成：" + " | ".join(s_sigs))

    st.markdown("---")

    # 第二排：核心點位看板
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("即時價", f"{last['Close']:,.0f}", f"{last['Close']-prev['Close']:,.0f}")
    m2.metric("5MA位階", f"{last['5MA']:,.1f}")
    m3.metric("今日高/低", f"{day_h:,.0f} / {day_l:,.0f}")
    m4.metric("最新音量", f"{int(last['Volume'])}")

    # 第三排：強哥關鍵位階
    st.markdown("### 🛡️ 關鍵支撐壓力區")
    c_p, c_s = st.columns(2)
    c_p.error(f"🚀 壓力區 (0.618)：**{day_l + diff * 0.618:,.2f}**")
    c_s.success(f"🛡️ 支撐區 (0.382)：**{day_l + diff * 0.382:,.2f}**")

else:
    st.warning("📊 戰術終端啟動中... 若數值仍為 0 請檢查交易時間或執行 Reboot App。")
