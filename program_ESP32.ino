#include <WiFi.h>
#include <PubSubClient.h>
#include "DHT.h"
#include "time.h"
#include <LiquidCrystal_I2C.h>

// ==================== LCD ====================
LiquidCrystal_I2C lcd(0x27, 16, 2);   // Ganti 16,2 ke 20,4 bila pakai LCD 20x4

// ==================== WIFI ====================
#define WIFI_SSID     "Mahya Madelta"
#define WIFI_PASSWORD "datangpergikembali#"

// ==================== MQTT ====================
#define MQTT_BROKER "broker.hivemq.com"
#define MQTT_PORT 1883
#define MQTT_TOPIC_PUB "iot/sensor/tralalilo_trolia/data"
#define MQTT_TOPIC_SUB "iot/sensor/tralalilo_trolia/control"

// ==================== PIN SENSOR & AKTUATOR ====================
#define DO_PIN   4
#define DHTPIN   2
#define AOUT_PIN 34
#define LED_PIN    5
#define BUZZER_PIN 18

#define DHTTYPE DHT11

// ==================== KALIBRASI SOIL ====================
#define DRY_VALUE  4095
#define WET_VALUE  0

// ==================== OBJEK ====================
WiFiClient espClient;
PubSubClient client(espClient);
DHT dht(DHTPIN, DHTTYPE);

// ==================== PREDIKSI TERAKHIR ====================
String lastPrediction = "STANDBY";

// ==================== WAKTU (WIB) ====================
const char* ntpServer = "pool.ntp.org";
const long  gmtOffset_sec = 7 * 3600;
const int   daylightOffset_sec = 0;


// ==================== CALLBACK MQTT ====================
void callback(char* topic, byte* payload, unsigned int length) {
  String msg = "";

  for (int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }

  Serial.print("📩 Pesan Masuk: ");
  Serial.println(msg);

  lastPrediction = msg;   // Simpan prediksi & tampilkan di LCD

  if (msg == "POMPA_ON") {
    digitalWrite(LED_PIN, HIGH);
    digitalWrite(BUZZER_PIN, LOW);
  }
  else if (msg == "ALARM_ON") {
    digitalWrite(LED_PIN, LOW);
    digitalWrite(BUZZER_PIN, HIGH);
  }
  else if (msg == "STANDBY") {
    digitalWrite(LED_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);
  }
}


// ==================== WIFI CONNECT ====================
void connectWiFi() {
  Serial.print("Menghubungkan WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi Tersambung");
}


// ==================== MQTT CONNECT ====================
void connectMQTT() {
  while (!client.connected()) {
    Serial.print("Menghubungkan MQTT...");

    if (client.connect("ESP32_SMART_GARDEN_LCD")) {
      Serial.println("✅ MQTT Tersambung!");
      client.subscribe(MQTT_TOPIC_SUB);
      Serial.println("Mendengarkan topic kontrol...");
    } else {
      Serial.print("❌ Gagal, code: ");
      Serial.println(client.state());
      delay(2000);
    }
  }
}


// ==================== WAKTU ====================
void getTimeData(String &isoTime) {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    isoTime = "1970-01-01T00:00:00";
    return;
  }
  char buffer[30];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", &timeinfo);
  isoTime = buffer;
}


// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);

  pinMode(DO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  dht.begin();
  analogSetAttenuation(ADC_11db);

  // LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SMART GARDEN");
  lcd.setCursor(0, 1);
  lcd.print("Initializing...");
  delay(1500);

  connectWiFi();
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);

  client.setServer(MQTT_BROKER, MQTT_PORT);
  client.setCallback(callback);

  Serial.println("Sistem Siap...");
}


// ==================== LOOP ====================
void loop() {

  if (!client.connected()) connectMQTT();
  client.loop();

  int ldr = digitalRead(DO_PIN);
  ldr = (ldr == 0) ? 1 : 0;

  float hum = dht.readHumidity();
  float temp = dht.readTemperature();
  float soilADC = analogRead(AOUT_PIN);

  if (isnan(hum) || isnan(temp)) return;

  float soilPercent =
      ((float)(DRY_VALUE - soilADC) / (DRY_VALUE - WET_VALUE)) * 100.0;
  soilPercent = constrain(soilPercent, 0, 100);

  // ==== TAMPILKAN DI LCD ====
  lcd.clear();
  lcd.setCursor(0, 0);

  // BARIS 1
  lcd.print("T:");
  lcd.print(temp, 1);
  lcd.print("C H:");
  lcd.print(hum, 0);

  // BARIS 2
  lcd.setCursor(0, 1);
  lcd.print("Soil:");
  lcd.print(soilPercent, 0);
  lcd.print("% ");

  if (lastPrediction == "POMPA_ON") lcd.print("P:ON");
  else if (lastPrediction == "ALARM_ON") lcd.print("A:ON");
  else lcd.print("OK");

  // ==== KIRIM MQTT ====
  String waktuISO;
  getTimeData(waktuISO);

  String payload = "{";
  payload += "\"waktu\":\"" + waktuISO + "\",";
  payload += "\"suhu\":" + String(temp) + ",";
  payload += "\"kelembaban_udara\":" + String(hum) + ",";
  payload += "\"ldr\":" + String(ldr) + ",";
  payload += "\"kelembaban_tanah\":" + String(soilPercent);
  payload += "}";

  client.publish(MQTT_TOPIC_PUB, payload.c_str());

  Serial.println(payload);

  delay(2000);
}
