#include <WiFi.h>
#include <PubSubClient.h>
#include <WiFiManager.h>
#include <ArduinoJson.h>

WiFiClient espClient;
PubSubClient client(espClient);

String mqtt_server = "192.168.100.189";

const int irSensorB = 2;  // GPIO2
bool lastState = HIGH;
unsigned long lastTriggerTime = 0;

void connectMQTT() {
    client.setServer(mqtt_server.c_str(), 1883);
    while (!client.connected()) {
        Serial.print("Connecting to MQTT Broker: ");
        Serial.println(mqtt_server);
        if (client.connect("ESP32_B_Debug")) {
            Serial.println("✅ Connected to MQTT Broker!");
        } else {
            Serial.println("❌ MQTT Connect Failed. Retrying...");
            delay(2000);
        }
    }
}

void setupWiFiAndMQTT() {
    WiFiManager wifiManager;
    wifiManager.resetSettings();

    WiFiManagerParameter mqtt_param("mqtt", "MQTT Broker IP", mqtt_server.c_str(), 40);
    wifiManager.addParameter(&mqtt_param);

    if (!wifiManager.startConfigPortal("ESP32-Setup #B-Debug")) {
        Serial.println("❌ Failed to start config portal. Restarting...");
        ESP.restart();
    }

    mqtt_server = mqtt_param.getValue();
    Serial.println("✅ MQTT Server Set To: " + mqtt_server);
}

void setup() {
    Serial.begin(115200);
    Serial.println("🔧 DEBUG MODE STARTED");

    setupWiFiAndMQTT();
    connectMQTT();

    pinMode(irSensorB, INPUT_PULLUP);
    Serial.println("✅ Sensor GPIO2 set to INPUT_PULLUP");
}

void loop() {
    if (!client.connected()) {
        Serial.println("⚠️ MQTT disconnected. Reconnecting...");
        connectMQTT();
    }
    client.loop();

    bool currentState = digitalRead(irSensorB);
    Serial.print("GPIO2 = ");
    Serial.println(currentState);  // พล็อตใน Serial Plotter ได้

    // ตรวจจับ edge: HIGH → LOW
    if (lastState == HIGH && currentState == LOW) {
        Serial.println("🔥 SENSOR TRIGGER DETECTED (HIGH → LOW)");
        client.publish("fitness_test/athlete_status_B", "Passed");
        lastTriggerTime = millis();
    }

    // ตรวจจับ false LOW ค้าง
    if (currentState == LOW && lastState == LOW) {
        unsigned long duration = millis() - lastTriggerTime;
        if (duration > 5000) {
            Serial.print("⛔ LOW ค้างนานเกินไป (");
            Serial.print(duration);
            Serial.println("ms) → มีโอกาส false trigger จาก ESP32 หรือสาย");
        }
    }

    lastState = currentState;
    delay(100);  // พอสำหรับดูกราฟหรือพล็อต
}
