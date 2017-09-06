/*
 * ESP8266+LoRaモジュール+GPSモジュールで、
 * スイッチを押されたら緯度経度を取得し、
 * bw, sfを変えながらLoRaで送信し、
 * LoRaモジュールからのレスポンスをプリントする
 */
#include <ESP8266WiFi.h>
#include <SoftwareSerial.h>
#include <TinyGPS++.h>
#include <string.h>

extern "C" {
#include "user_interface.h"
}

static const int LED = 2;
static const int gps_RX = 4, gps_TX = 5;
SoftwareSerial gps_ss(gps_RX, gps_TX, false, 256);
TinyGPSPlus gps;

static const int sw = 16;
static const unsigned long PUSH_SHORT = 1000;

static const int LoRa_RX = 13, LoRa_TX = 12;
static const int LoRa_Rst = 14;
SoftwareSerial LoRa_ss(LoRa_RX, LoRa_TX, false, 256);

void LoRa_reset(void) {
    digitalWrite(LoRa_Rst, LOW);
    delay(100);
    digitalWrite(LoRa_Rst, HIGH);
}

int LoRa_recv(char *buf) {
    char *start = buf;

    while (true) {
        delay(0);
        while (LoRa_ss.available() > 0) {
            *buf++ = LoRa_ss.read();
            if (*(buf-2) == '\r' && *(buf-1) == '\n') {
                *buf = '\0';
                return (buf - start);
            }
        }
    }
}

int LoRa_send(char * msg) {
    char *start = msg;
    while (*msg != '\0') {
        LoRa_ss.write(*msg++);
    }
    return (msg - start);
}

#define NMODE 24
 
struct mode {
    int bw;
    int sf;
    int timeout;
};
struct mode Mode[NMODE] = {
    {3, 12, 5}, {3, 11, 5}, {3, 10, 4}, {3, 9, 3}, {3, 8, 2}, {3, 7, 2},
    {4, 12, 5}, {4, 11, 4}, {4, 10, 3}, {4, 9, 3}, {4, 8, 2}, {4, 7, 2},
    {5, 12, 4}, {5, 11, 3}, {5, 10, 2}, {5, 9, 2}, {5, 8, 2}, {5, 7, 2},
    {6, 12, 3}, {6, 11, 3}, {6, 10, 2}, {6, 9, 2}, {6, 8, 2}, {6, 7, 2},
};

int sendcmd(char *cmd) {
    unsigned long t;
    char buf[64];

//    Serial.print(cmd);
    LoRa_send(cmd);

    while (true) {
        LoRa_recv(buf);
        if (strstr(buf, "OK")) {
//            Serial.print(buf);
            return true;
        } else if (strstr(buf, "NG")) {
//            Serial.print(buf);
            return false;
        }
    }
}

void setMode(int bw, int sf) {
    char buf[64];

    LoRa_send("config\r\n");
    delay(200);
    LoRa_reset();
    delay(1500);

    while (true) {
        LoRa_recv(buf);
        if (strstr(buf, "Mode")) {
            Serial.print(buf);
            break;
        }
    }

    sendcmd("2\r\n");
    sprintf(buf, "bw %d\r\n", bw);
    sendcmd(buf);
    sprintf(buf, "sf %d\r\n", sf);
    sendcmd(buf);
    sendcmd("q 2\r\n");
    sendcmd("w\r\n");

    LoRa_reset();
    Serial.println("LoRa module set to new mode");
    delay(1000);
}

void send2LoRa() {
    char obuf[64], ibuf[64], shortbuf[32];
    char * buf;
    int n;
    unsigned long t;

    strcpy(obuf, "loc=(");
    dtostrf(gps.location.lat(), 12, 8, &obuf[strlen(obuf)]);
    strcat(obuf, ",");
    dtostrf(gps.location.lng(), 12, 8, &obuf[strlen(obuf)]);
    strcat(obuf, ")\r\n");

    strcpy(shortbuf, "loc=(");
    dtostrf(gps.location.lat(), 8, 4, &shortbuf[strlen(shortbuf)]);
    strcat(shortbuf, ",");
    dtostrf(gps.location.lng(), 8, 4, &shortbuf[strlen(shortbuf)]);
    strcat(shortbuf, ")\r\n");

    digitalWrite(LED, HIGH);

    for (int i = 0; i < NMODE; i++) {
        Serial.print("setMode(bw: ");
        Serial.print(Mode[i].bw);
        Serial.print(", sf: ");
        Serial.print(Mode[i].sf);
        Serial.println(")");

        setMode(Mode[i].bw, Mode[i].sf);

        t = millis();
        delay(500);

        Serial.print("send to LoRa: ");
        buf = (i == 0) ? shortbuf : obuf;
        Serial.print(buf);
        LoRa_send(buf);

        while (true) {
            LoRa_recv(ibuf);
            if (strstr(ibuf, "OK")) {
                Serial.print(ibuf);
                break;
            } else if (strstr(ibuf, "NG")) {
                Serial.print(ibuf);
                break;
            }
        }

        if (i != 0) {
            long s;

            s = Mode[i].timeout * 1000 - (millis() - t);
            if (s > 0) {
                Serial.print("delay: ");
                Serial.println(s);
                delay(s);
            }
        }
    }

    digitalWrite(LED, LOW);
}

void setup()
{
    WiFi.mode(WIFI_OFF);

    Serial.begin(115200);
    delay(20);

    pinMode(LED, OUTPUT);
    digitalWrite(LED, LOW);

    gps_ss.begin(9600);

    pinMode(sw, INPUT);

    LoRa_ss.begin(115200);
    pinMode(LoRa_Rst, OUTPUT_OPEN_DRAIN);
    digitalWrite(LoRa_Rst, HIGH);

    LoRa_reset();

    delay(1000); // LoRaモジュールをリセットしてからCPUと通信できるまでに1秒程度かかるようだ

    while (LoRa_ss.available() > 0) {
        char c = LoRa_ss.read();
            if (c < 0x80) {
                Serial.print(c);
            }
    }
    Serial.println(F("\r\nStart"));
}

void loop()
{
    unsigned long gauge = 0;
    char buf[128];

    while (digitalRead(sw) == 0) {
        gauge++;
        delay(0);
    }
    if (gauge > PUSH_SHORT) {
        if (gps.location.isValid()) {
            gps_ss.enableRx(false);
            send2LoRa();
            gps_ss.enableRx(true);
        }
    }
    while (gps_ss.available() > 0) {
        if (gps.encode(gps_ss.read())) {
            break;
        }
    }
}

