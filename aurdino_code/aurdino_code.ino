#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <WiFiClient.h>   // ✅ ADD THIS

WiFiClient client;        // ✅ CREATE CLIENT OBJECT
HTTPClient http;

#define SS_PIN D2
#define RST_PIN D1
#define BUZZER D0

MFRC522 mfrc522(SS_PIN, RST_PIN);

const char* ssid = "Manikanta";
const char* password = "12341234";

// Flask API URL
const char* serverUrl = "http://10.50.251.18:5000/scan";

void setup() {
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();

  pinMode(BUZZER, OUTPUT);

  WiFi.begin(ssid, password);
  Serial.print("Connecting...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
}

void loop() {
  if (!mfrc522.PICC_IsNewCardPresent()) return;
  if (!mfrc522.PICC_ReadCardSerial()) return;

  String uid = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uid += String(mfrc522.uid.uidByte[i], HEX);
  }

  Serial.println("Scanned UID: " + uid);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(client, serverUrl);
    http.addHeader("Content-Type", "application/json");

    String jsonData = "{\"uid\":\"" + uid + "\"}";
    int httpResponseCode = http.POST(jsonData);

    String response = http.getString();
    Serial.println(response);

    if (httpResponseCode != 200) {
      digitalWrite(BUZZER, HIGH);
      delay(500);
      digitalWrite(BUZZER, LOW);
    }

    http.end();
  }

  delay(2000);
}