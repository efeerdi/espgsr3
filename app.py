import streamlit as st
import requests
import re
from datetime import datetime
import pandas as pd
import time

# --- KONFİGÜRASYON ---
# Firebase URL'sinin sonuna .json eklenmiş hali
FIREBASE_URL = "https://espgsr3-default-rtdb.europe-west1.firebasedatabase.app/history.json"

st.set_page_config(page_title="ESP32-C6 Panel", page_icon="📈", layout="wide")

# --- YAN MENÜ (SIDEBAR) AYARLARI ---
st.sidebar.header("⚙️ Kontrol Paneli")

# Sayfa yenileme hızı ayarı
refresh_rate = st.sidebar.slider("Yenileme Hızı (Saniye)", min_value=1, max_value=60, value=3)
st.sidebar.write(f"⏱️ Mevcut hız: {refresh_rate} saniye")

st.sidebar.divider()

# Veri çekme limiti ayarı (Veritabanı dolsa bile paneli hızlandırmak için)
data_limit = st.sidebar.number_input("Görüntülenecek Son Veri Sayısı", min_value=10, max_value=1000, value=100, step=10)
st.sidebar.info("Performans için sadece en son gelen veriler ekranda tutulur.")

st.title("📈 ESP32-C6 Sensör Geçmişi")

# --- FONKSİYONLAR ---

def fetch_data(limit):
    """Firebase'den sadece son 'limit' kadar veriyi çeker"""
    try:
        # Firebase REST API için sorgu parametreleri
        params = {
            'orderBy': '"timestamp"',
            'limitToLast': limit
        }
        response = requests.get(FIREBASE_URL, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    except Exception as e:
        st.sidebar.error(f"Bağlantı hatası: {e}")
        return {}

def parse_history(firebase_data):
    """Firebase'den gelen karmaşık veriyi tablo formatına çevirir"""
    parsed_records = []
    
    # Eğer veri boşsa veya 'null' döndüyse boş liste dön
    if not firebase_data or not isinstance(firebase_data, dict): 
        return []
    
    for push_id, record in firebase_data.items():
        # Bazen hatalı boş kayıtlar gelebilir, onları atla
        if not isinstance(record, dict):
            continue
            
        raw_text = record.get('data', '')
        timestamp_ms = record.get('timestamp', 0)
        
        # Zamanı okunabilir formata çevir
        if timestamp_ms > 0:
            dt_object = datetime.fromtimestamp(timestamp_ms / 1000.0)
            time_str = dt_object.strftime("%H:%M:%S") # İstersen %d/%m/%Y ekleyebilirsin
        else:
            time_str = "Bilinmiyor"
            
        # Regex ile BLE metnini parçala (Örn: #ID%KEY%VALUE#)
        pattern = r"#\d+%([^%]+)%([^#]+)#"
        matches = re.findall(pattern, raw_text)
        
        row_data = {"Zaman": time_str, "Timestamp": timestamp_ms} 
        
        # Bulunan değerleri sözlüğe ekle
        for match in matches:
            key = match[0].strip()
            value = match[1].strip()
            row_data[key] = value
            
        parsed_records.append(row_data)
        
    return parsed_records

# --- ANA EKRAN İŞLEMLERİ ---

# Veriyi çek
raw_data = fetch_data(data_limit)

if raw_data:
    # Veriyi Pandas Tablosuna (DataFrame) çevir
    records = parse_history(raw_data)
    
    if len(records) > 0:
        df = pd.DataFrame(records)
        
        # Zaman damgasına göre sırala (En yeni en üstte)
        df = df.sort_values(by="Timestamp", ascending=False).drop(columns=["Timestamp"])
        
        # En son gelen veriyi al
        latest_data = df.iloc[0]
        
        st.subheader(f"🔴 Canlı Veriler (Son Okuma: {latest_data['Zaman']})")
        
        # Sadece sayısal/sensör değerlerini bul (Zaman sütunu hariç)
        metric_cols = [col for col in df.columns if col != 'Zaman']
        
        # Metrik kartlarını oluştur
        cols = st.columns(len(metric_cols))
        for idx, col_name in enumerate(metric_cols):
            cols[idx].metric(label=col_name, value=latest_data[col_name])

        st.divider()

        # Grafik ve Tabloyu yan yana diz
        col1, col2 = st.columns([5, 3])
        
        with col1:
            st.subheader("📉 Zaman İçinde Değişim")
            
            # Grafik için veriyi hazırla (Eskiden yeniye doğru akması için ters çeviriyoruz)
            chart_df = df.copy()
            chart_df = chart_df.set_index('Zaman').iloc[::-1]
            
            # Sütunları sayı formatına (Float/Int) zorla ki grafik çizilebilsin
            for c in metric_cols:
                chart_df[c] = pd.to_numeric(chart_df[c], errors='coerce')
                
            st.line_chart(chart_df)
        
        with col2:
            st.subheader(f"📜 Son {len(df)} Kayıt")
            # Tabloyu ekrana sığdır
            st.dataframe(df, use_container_width=True, height=400)
    else:
        st.warning("Veriler parçalanamadı. Gönderilen veri formatını kontrol edin.")
else:
    st.info("Veritabanı boş veya cihazdan veri bekleniyor...")

# --- DİNAMİK YENİLEME DÖNGÜSÜ ---
# Kullanıcının yan menüden seçtiği süre kadar bekle ve sayfayı baştan yükle
time.sleep(refresh_rate)
st.rerun()