import streamlit as st
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import pandas as pd
import json
import time

# ================= KONEKSI MQTT =================
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_DATA = "iot/sensor/tralalilo_trolia/data"
TOPIC_CONTROL = "iot/sensor/tralalilo_trolia/control"

# ================= SETUP HALAMAN =================
st.set_page_config(page_title="Smart Garden", page_icon="🌱", layout="wide")

# ================= INISIALISASI SESSION STATE (UTAMA) =================
# Pastikan variabel ini ada sebelum script berjalan lebih jauh
if "data_log" not in st.session_state:
    st.session_state.data_log = []

if "latest_status" not in st.session_state:
    st.session_state.latest_status = "STANDBY"

# ================= FUNGSI MQTT (BACKGROUND THREAD) =================

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("✅ Connected to MQTT Broker!")
        client.subscribe([(TOPIC_DATA, 0), (TOPIC_CONTROL, 0)])

# PERHATIKAN: Fungsi ini TIDAK BOLEH pakai st.session_state
def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode("utf-8")

        # 'userdata' adalah dictionary biasa yang kita titipkan saat start_mqtt
        # Ini aman diakses dari thread manapun
        
        if topic == TOPIC_DATA:
            data = json.loads(payload)
            data['anomali'] = False 
            # Masukkan ke buffer (antrian) di userdata
            userdata['buffer'].append(data)
                
        elif topic == TOPIC_CONTROL:
            # Masukkan status ke userdata
            userdata['status'] = payload

    except Exception as e:
        print(f"Error parsing MQTT: {e}")

# ================= START MQTT (CACHE) =================
@st.cache_resource
def start_mqtt():
    # 1. Buat Shared Memory (Tas Penitipan)
    # Ini adalah variabel Python biasa (bukan Streamlit session)
    shared_memory = {'buffer': [], 'status': 'STANDBY'}
    
    # 2. Masukkan tas ini ke dalam client MQTT
    client = mqtt.Client(CallbackAPIVersion.VERSION2, userdata=shared_memory)
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect(BROKER, PORT, 60)
    client.loop_start()
    
    # Kembalikan client DAN tas-nya agar bisa dibaca Streamlit
    return client, shared_memory

# Jalankan fungsi ini sekali saja
client, shared_memory = start_mqtt()

# ================= SINKRONISASI DATA (THREAD -> STREAMLIT) =================
# Bagian ini berjalan di Thread Utama Streamlit
# Tugasnya memindahkan data dari 'Tas' (shared_memory) ke 'Session State'

# 1. Ambil status terbaru dari tas
if shared_memory['status']:
    st.session_state.latest_status = shared_memory['status']

# 2. Ambil data sensor dari antrian buffer
if len(shared_memory['buffer']) > 0:
    # Pindahkan semua data di antrian ke data_log utama
    for data in shared_memory['buffer']:
        st.session_state.data_log.append(data)
    
    # Kosongkan antrian setelah dipindah
    shared_memory['buffer'].clear()
    
    # Jaga agar log tidak terlalu panjang (Maks 100 baris)
    if len(st.session_state.data_log) > 100:
        st.session_state.data_log = st.session_state.data_log[-100:]

# ================= FUNGSI KIRIM PERINTAH =================
def send_command(command):
    client.publish(TOPIC_CONTROL, command, retain=True)
    # Update manual ke shared memory agar responsif
    shared_memory['status'] = command 
    st.session_state.latest_status = command
    st.toast(f"Perintah: {command}", icon="📡")

# ================= TAMPILAN DASHBOARD =================

st.title("🌱 Smart Garden Monitoring System")

# --- 1. METRICS ---
if len(st.session_state.data_log) > 0:
    last_data = st.session_state.data_log[-1]
    
    ldr_text = "☀️ Terang" if last_data['ldr'] == 1 else "🌑 Gelap"
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🌡️ Suhu", f"{last_data['suhu']} °C")
    col2.metric("💧 Udara", f"{last_data['kelembaban_udara']} %")
    col3.metric("🌱 Tanah", f"{last_data['kelembaban_tanah']} %")
    col4.metric("💡 Cahaya", ldr_text)
else:
    st.info("⏳ Menunggu data masuk dari MQTT...")

st.divider()

# --- 2. KONTROL & GRAFIK ---
col_ctrl, col_graph = st.columns([1, 2])

with col_ctrl:
    st.subheader("Panel Kendali")
    
    status_now = st.session_state.latest_status
    if status_now == "POMPA_ON":
        st.success(f"Status: **MENYIRAM (ON)**")
    elif status_now == "ALARM_ON":
        st.error(f"Status: **BAHAYA (ALARM)**")
    else:
        st.info(f"Status: **STANDBY**")

    st.write("---")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💦 Siram", use_container_width=True):
            send_command("POMPA_ON")
        if st.button("🔇 Stop", use_container_width=True):
            send_command("STANDBY")
    with c2:
        if st.button("🚨 Alarm", use_container_width=True):
            send_command("ALARM_ON")

with col_graph:
    st.subheader("Grafik Real-time")
    if len(st.session_state.data_log) > 0:
        df = pd.DataFrame(st.session_state.data_log)
        df['waktu'] = pd.to_datetime(df['waktu'])
        # Tampilkan grafik
        st.area_chart(df[['waktu', 'suhu', 'kelembaban_tanah']].set_index('waktu'), color=["#FF4B4B", "#0068C9"])

# --- 3. TABEL DATA ---
with st.expander("📝 Log Data", expanded=True):
    if len(st.session_state.data_log) > 0:
        df_log = pd.DataFrame(st.session_state.data_log)
        # Data editor
        st.data_editor(
            df_log.sort_values(by="waktu", ascending=False),
            column_config={"anomali": st.column_config.CheckboxColumn("Anomali?", default=False)},
            disabled=["waktu", "suhu", "kelembaban_udara", "kelembaban_tanah", "ldr"],
            use_container_width=True
        )

# --- AUTO REFRESH ---
time.sleep(2)
st.rerun()