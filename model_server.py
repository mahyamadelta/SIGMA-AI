import json
import joblib
import paho.mqtt.client as mqtt
import pandas as pd
import time

# --- 1. KONFIGURASI ---
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_DATA = "iot/sensor/tralalilo_trolia/data"
TOPIC_REPLY = "iot/sensor/tralalilo_trolia/control"
MODEL_FILE = "smart_garden_model.pkl"

# --- VARIABEL STATUS TERAKHIR (State Machine) ---
last_command_sent = None  # Menyimpan perintah terakhir yang dikirim
last_action_time = 0      # Untuk timer (opsional)

# --- 2. LOAD MODEL ---
print("⏳ Memuat Model AI...")
try:
    model = joblib.load(MODEL_FILE)
    print("✅ Model berhasil dimuat!")
except FileNotFoundError:
    print(f"❌ Error: File model tidak ditemukan.")
    exit()

label_map = {0: "IDEAL", 1: "SIRAM", 2: "WARNING"}

# --- 3. FUNGSI MQTT ---
def on_connect(client, userdata, flags, rc):
    print(f"✅ Terhubung ke Broker! Subscribe ke: {TOPIC_DATA}")
    client.subscribe(TOPIC_DATA)

def on_message(client, userdata, msg):
    # Kita gunakan variabel global untuk menyimpan status terakhir
    global last_command_sent, last_action_time
    
    try:
        payload_str = msg.payload.decode("utf-8")
        data_json = json.loads(payload_str)
        
        # Ekstrak data untuk AI
        input_df = pd.DataFrame([[
            data_json['suhu'],
            data_json['kelembaban_udara'],
            data_json['kelembaban_tanah'],
            data_json['ldr']
        ]], columns=['Suhu', 'Kelembaban_Udara', 'Kelembaban_Tanah', 'LDR'])

        # Prediksi
        prediksi_index = model.predict(input_df)[0]
        hasil_teks = label_map[prediksi_index]
        
        # --- LOGIKA BARU: STATE CHANGE DETECTION ---
        # Tentukan perintah berdasarkan prediksi
        current_command = ""
        if prediksi_index == 1:
            current_command = "POMPA_ON"
        elif prediksi_index == 2:
            current_command = "ALARM_ON"
        else:
            current_command = "STANDBY"

        # Cek apakah perintah BERBEDA dengan yang terakhir dikirim?
        # Jika sama, JANGAN kirim apa-apa (biar dashboard tidak terganggu)
        if current_command != last_command_sent:
            
            # [Opsional] Fitur Debouncing/Delay
            # Mencegah perubahan terlalu cepat (misal minimal 5 detik baru boleh ganti status)
            if (time.time() - last_action_time) > 2: 
                
                print(f"⚠️ PERUBAHAN STATUS DETEKSI: {last_command_sent} -> {current_command}")
                print(f"   Data Sensor: Tanah={data_json['kelembaban_tanah']}%, Suhu={data_json['suhu']}C")
                
                # Kirim perintah BARU ke MQTT
                # retain=True agar status tersimpan di broker (Dashboard langsung update saat buka)
                client.publish(TOPIC_REPLY, current_command, retain=True)
                
                # Update status terakhir
                last_command_sent = current_command
                last_action_time = time.time()
                
            else:
                print(f"⏳ Status berubah tapi ditahan (Debouncing)...")
        else:
            # Jika status sama, diam saja (Heartbeat log)
            print(f"💤 Status Stabil: {hasil_teks} (Tidak kirim perintah)")

    except Exception as e:
        print(f"Error processing: {e}")

# --- 4. MAIN LOOP ---
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_forever()