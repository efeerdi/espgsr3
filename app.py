import streamlit as st
import requests
import re
from datetime import datetime
import pandas as pd
import time

# --- KONFİGÜRASYON ---
FIREBASE_URL = "https://espgsr3-default-rtdb.europe-west1.firebasedatabase.app/history.json"

st.set_page_config(page_title="ESP32-C6 Panel", page_icon="📈", layout="wide")

# --- YAN MENÜ AYARLARI ---
st.sidebar.header("⚙️ Kontrol Paneli")
refresh_rate = st.sidebar.slider("Yenileme Hızı (Saniye)", 1, 60, 3)
st.sidebar.write(f"⏱️ Mevcut hız: {refresh_rate}s")

# Veritabanını temizlemek istersen bir buton (isteğe bağlı)
if st.sidebar.button("🗑️ Geçmişi Temizle (Manuel)"):
    st.sidebar.warning("Bu işlem Firebase'deki tüm verileri siler!")
    # requests.delete(FIREBASE_URL) # Dikkatli kullan!

st.title("📈 ESP32-C6 Sensör Geçmişi")

# --- FONKSİYONLAR ---
def fetch_data():
    try:
        response = requests.get(FIREBASE_URL)
        return response.json() if response.status_code == 200 else {}
    except:
        return {}

def parse_history(firebase_data):
    parsed_records = []
    if not firebase_data: return []
    
    for push_id, record in firebase_data.items():
        raw_text = record.get('data', '')
        timestamp_ms = record.get('timestamp', 0)
        
        dt_object = datetime.fromtimestamp(timestamp_ms / 1000.0)
        time_str = dt_object.strftime("%H:%M:%S")
            
        pattern = r"#\d+%([^%]+)%([^#]+)#"
        matches = re.findall(pattern, raw_text)
        
        row_data = {"Zaman": time_str, "Timestamp": timestamp_ms} 
        for match in matches:
            row_data[match[0].strip()] = match[1].strip()
        parsed_records.append(row_data)
        
    return parsed_records

# --- ANA EKRAN ---
raw_data = fetch_data()

if raw_data:
    records = parse_history(raw_data)
    df = pd.DataFrame(records)
    df = df.sort_values(by="Timestamp", ascending=False).drop(columns=["Timestamp"])
    
    # Metrik Kartları
    latest = df.iloc[0]
    st.subheader(f"🔴 Son Veri ({latest['Zaman']})")
    cols = st.columns(len(df.columns)-1)
    for i, col_name in enumerate([c for c in df.columns if c != 'Zaman']):
        cols[i].metric(label=col_name, value=latest[col_name])

    st.divider()

    # Grafik ve Tablo
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📉 Grafik")
        chart_df = df.set_index('Zaman').iloc[::-1]
        for c in chart_df.columns:
            chart_df[c] = pd.to_numeric(chart_df[c], errors='coerce')
        st.line_chart(chart_df)
    
    with c2:
        st.subheader("📜 Kayıtlar")
        st.dataframe(df, use_container_width=True, height=400)
else:
    st.info("Veri bekleniyor...")

# DİNAMİK BEKLEME SÜRESİ
time.sleep(refresh_rate)
st.rerun()