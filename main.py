import streamlit as st
import pandas as pd
import numpy as np
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz

# --- 1. 環境校時 (強制台灣時區) ---
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=3000, key="tmf_ultimate_v6")

st.set_page_config(page_title="TMF 3分K 交易監控", layout="wide")
st.title("TMF 微台全 3分K 交易系統")

# --- 2. 🔑 Token 設定與強效登入 ---
MY_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wOSAyMDozOToxOSIsInVzZXJfaWQiOiJhcmljYTUxNSIsImVtYWlsIjoiZXZlbmNoZW41MTVAZ21haWwuY29tIiwiaXAiOiIxMjQuNi4xMS4yMTYifQ.NkLHnTiAp10uKfrc8qkt0YevD-Cc1XV062O1u3lBvh4"

def fast_login(token):
    api = DataLoader()
    # 嘗試所有可能的登入函式名稱
    for func in ['login', 'login_by_token', 'login_token']:
        if hasattr(api, func):
            try:
                getattr(api, func)(api_token=token)
                return api
            except:
                continue
    return api

api_client = fast_login(MY_TOKEN)

# --- 3. 數據抓取 (增加備援與容錯) ---
@st.cache_data(ttl=3)
def get_safe_data(token):
    now_tw = datetime.now(tw_tz)
    # 抓取包含昨日的數據以確保 MA 指標正常
    start_dt = (now_tw - timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        df = api_client.taiwan_futures_tick(futures_id="TMF", date=start_dt)
        if df is None or df.empty:
            return None, "API 回傳空值，請確認 TMF 目前是否有交易"
        return df, "OK"
    except Exception as e:
        return None, f"連線錯誤: {str(e)}"

# --- 4. 運算核心 (3分K) ---
def calc_indicators(df):
    # 欄位標準化
    p_col = 'price' if 'price' in df.columns else 'deal_price'
    df['date'] = pd.to_datetime(df['date'] + ' ' + df['time'])
    df = df.set_index('date')
    
    # 轉換 OHLC
    ohlc = df[p_col].resample('3min').ohlc()
    ohlc['volume'] = df['qty'].resample('3min').sum() if 'qty' in df.columns else 0
    df_3m = ohlc.dropna().reset_index()
    
    # 指標計算
    df_3m['ma5'] = df_3m['close'].rolling(5).mean()
    df_3m['ma20'] = df_3m['close'].rolling(20).mean()
    
    # 買賣積分 (範例)
    df_3m['buy_score'] = (df_3m['close'] > df_3m['ma5']).astype(int) * 5
    df_3m['sell_score'] = (df_3m['close'] < df_3m['ma5']).astype(int) * 5
    return df_3m

# --- 5. UI 顯示 ---
now_str = datetime.now(tw_tz).strftime('%H:%M:%S')
st.write(f"⏰ **台灣站點時間**: {now_str}")

raw_df, status = get_safe_data(MY_TOKEN)

if status == "OK":
    st.success(f"✅ 數據同步中 (共 {len(raw_df)} 筆 Tick)")
    df_final = calc_indicators(raw_df)
    
    if not df_final.empty:
        last = df_final.iloc[-1]
        
        # 燈號渲染 (Rich 對消邏輯)
        r_raw = min(3, int(last['buy_score'] // 5))
        g_raw = min(3, int(last['sell_score'] // 5))
        f_red = max(0, r_raw - g_raw)
        f_green = g_raw

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🔴 買進紅燈")
            st.markdown("".join([f'<div style="width:70px;height:70px;background:{"red" if i<f_red else "#220000"};border-radius:50%;display:inline-block;margin:10px;border:3px solid white;"></div>' for i in range(3)]), unsafe_allow_html=True)
            st.metric("當前指數", f"{last['close']:.0f}")
        with c2:
            st.markdown("### 🟢 賣出綠燈")
            st.markdown("".join([f'<div style="width:70px;height:70px;background:{"#00FF00" if i<f_green else "#002200"};border-radius:50%;display:inline-block;margin:10px;border:3px solid white;"></div>' for i in range(3)]), unsafe_allow_html=True)
            st.metric("買進積分", f"{int(last['buy_score'])}/20")

        st.markdown("---")
        st.write("📊 **即時 3分K 指標數據表**")
        st.dataframe(df_final.tail(10))
    else:
        st.warning("⏳ 3分K 棒尚未生成，請等待下一根 K 棒...")
else:
    st.error(f"📡 {status}")
    st.info("提示：如果持續看到 'data' 錯誤，請確認你的 FinMind 官網是否可以正常登入，或嘗試重啟 Streamlit 服務。")
