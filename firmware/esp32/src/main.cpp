/**
 * OMNISOUND ESP32 - Thin Client Architecture
 * MINIMAL MEMORY FOOTPRINT - MAXIMUM BATTERY EFFICIENCY
 *
 * THIS FIRMWARE DOES MINIMAL PROCESSING:
 * - Captures raw audio from I2S MEMS microphone
 * - Streams raw PCM to connected device via WebSocket
 * - Receives processed motor angles from device
 * - Controls servos with received angles
 *
 * ALL AUDIO PROCESSING (FFT, BEAT DETECTION, MOTOR MAPPING)
 * IS DONE ON THE CONNECTED DEVICE (PHONE/COMPUTER)
 *
 * Hardware: ESP32 + I2S MEMS Microphone + PCA9685 Servo Driver
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ESPmDNS.h>
#include <DNSServer.h>
#include <ESP32Servo.h>
#include <Preferences.h>

// I2S audio capture - hardware specific
// Stubbed for CI compilation; real code runs on actual ESP32
#ifndef PIO_CI_BUILD
  #include <driver/i2s.h>
  #define HAS_I2S 1
#else
  #define HAS_I2S 0
#endif

// ============================================
// CONFIGURATION - EDIT THESE VALUES
// ============================================
#define DEVICE_NAME "OMNISOUND"        // WiFi AP name = website name
#define CAPTIVE_PORTAL_DOMAIN "omnisound.local"
#define WS_PORT 81                     // WebSocket port
#define HTTP_PORT 80                   // Web server port

// Audio Configuration - Minimal processing
#define I2S_WS_PIN 25                  // I2S WS pin
#define I2S_SCK_PIN 26                 // I2S SCK pin
#define I2S_SD_PIN 27                  // I2S SD pin (data)
#define SAMPLE_RATE 16000              // Low sample rate saves memory
#define AUDIO_BUFFER_SIZE 512           // Small buffer = low memory

// Motor Configuration
#define MOTOR_COUNT 4
#define USE_PCA9685 false              // Set true if using PCA9685
#define PWM_FREQUENCY 50               // Servo frequency

// Motor pins (direct PWM - change if using different pins)
#if USE_PCA9685
#define PCA9685_ADDR 0x40
#else
const uint8_t MOTOR_PINS[MOTOR_COUNT] = {13, 14, 27, 26};
#endif

// ============================================
// GLOBAL VARIABLES - MINIMAL FOOTPRINT
// ============================================
Preferences prefs;

// WiFi - Access Point mode
IPAddress apIP(192, 168, 1, 1);
IPAddress netMask(255, 255, 255, 0);

// WebSocket
WebSocketsServer webSocket = WebSocketsServer(WS_PORT);

// Web server for captive portal
DNSServer dnsServer;

// Audio buffer - Pre-allocated to avoid fragmentation
static int16_t audioBuffer[AUDIO_BUFFER_SIZE];
static size_t audioBytesRead = 0;

// Motor angles (received from connected device)
static float motorAngles[MOTOR_COUNT];
static bool motorAnglesValid[MOTOR_COUNT] = {false, false, false, false};

// Status
static bool clientConnected = false;
static unsigned long lastAudioSend = 0;
static unsigned long lastStatusBroadcast = 0;
static uint32_t audioChunksSent = 0;
static uint32_t commandsReceived = 0;

// Servo objects
#if !USE_PCA9685
static Servo servos[MOTOR_COUNT];
#endif

// ============================================
// FORWARD DECLARATIONS
// ============================================
void initAudio();
void initMotors();
void initWiFiAP(const char* ssid, const char* pass);
void initWebSocket();
void initWebServer();
void handleWebSocketEvent(uint8_t num, WStype_t type, uint8_t *payload, size_t length);
void processCommand(const char* json);
void sendAudioChunk();
void broadcastStatus();
void updateMotors();
String getHTML();
String getJS();
String getCSS();

// ============================================
// SETUP
// ============================================
void setup() {
    Serial.begin(115200);
    Serial.println("\n\n=== OMNISOUND ESP32 - Thin Client Mode ===");
    Serial.println("Minimal processing - Maximum efficiency");

    // Load saved configuration
    prefs.begin("omnisound");
    String savedSSID = prefs.getString("ssid", "");
    String savedPass = prefs.getString("pass", "");

    // Initialize components
    initMotors();
    initAudio();
    initWiFiAP(savedSSID.c_str(), savedPass.c_str());
    initWebSocket();
    initWebServer();

    // Initialize all motors to center
    for (int i = 0; i < MOTOR_COUNT; i++) {
        motorAngles[i] = 90.0;
        motorAnglesValid[i] = true;
    }

    Serial.println("\n=== READY ===");
    Serial.printf("WiFi Network: %s\n", DEVICE_NAME);
    Serial.printf("Website: http://%s.local or http://192.168.1.1\n", DEVICE_NAME);
    Serial.printf("WebSocket: ws://192.168.1.1:%d\n", WS_PORT);
}

// ============================================
// MAIN LOOP - MINIMAL WORK
// ============================================
void loop() {
    // Handle WebSocket clients
    webSocket.loop();

    // Send audio data to connected client (every ~32ms for 512 samples @ 16kHz)
    if (clientConnected && millis() - lastAudioSend > 20) {
        sendAudioChunk();
        lastAudioSend = millis();
    }

    // Broadcast status every 100ms
    if (clientConnected && millis() - lastStatusBroadcast > 100) {
        broadcastStatus();
        lastStatusBroadcast = millis();
    }

    // Update motor positions
    updateMotors();

    // Handle DNS for captive portal
    dnsServer.processNextRequest();
}

// ============================================
// AUDIO INITIALIZATION - I2S MEMS MIC
// ============================================
void initAudio() {
    Serial.println("Initializing I2S microphone...");

#ifndef PIO_CI_BUILD
    // Real I2S setup using ESP-IDF driver (available on actual ESP32 hardware)
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 4,
        .dma_buf_len = 128,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0
    };

    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_SCK_PIN,
        .ws_io_num = I2S_WS_PIN,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_SD_PIN
    };

    i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_NUM_0, &pin_config);
#endif

    Serial.printf("I2S microphone initialized: %d Hz\n", SAMPLE_RATE);
}

// ============================================
// MOTOR INITIALIZATION
// ============================================
void initMotors() {
    Serial.println("Initializing motors...");

#if USE_PCA9685
    // PCA9685 initialization would go here
    // Wire library required
#else
    // Direct servo attachment
    for (int i = 0; i < MOTOR_COUNT; i++) {
        servos[i].attach(MOTOR_PINS[i], 500, 2500);
        servos[i].write(90);  // Center position
        delay(50);
    }
#endif

    Serial.printf("Initialized %d motors\n", MOTOR_COUNT);
}

// ============================================
// WiFi ACCESS POINT - CAPTIVE PORTAL
// ============================================
void initWiFiAP(const char* ssid, const char* pass) {
    Serial.println("Starting WiFi Access Point...");

    // Use provided SSID or default
    const char* apName = DEVICE_NAME;
    const char* apPass = "12345678";  // Minimum 8 chars for WPA2

    WiFi.mode(WIFI_AP);
    WiFi.softAPConfig(apIP, apIP, netMask);
    WiFi.softAP(apName, apPass);

    // Start mDNS
    MDNS.begin(DEVICE_NAME);
    MDNS.addService("http", "tcp", HTTP_PORT);
    MDNS.addService("ws", "tcp", WS_PORT);

    Serial.printf("AP started: %s\n", apName);
    Serial.printf("Password: %s\n", apPass);
}

// ============================================
// WEBSOCKET SERVER
// ============================================
void initWebSocket() {
    webSocket.begin();
    webSocket.onEvent(handleWebSocketEvent);
    Serial.printf("WebSocket server started on port %d\n", WS_PORT);
}

// ============================================
// CAPTIVE PORTAL WEB SERVER
// ============================================
#include <WebServer.h>
WebServer server(HTTP_PORT);

void initWebServer() {
    // Main page
    server.on("/", []() {
        server.send(200, "text/html", getHTML());
    });

    // JavaScript (inline for single request)
    server.on("/app.js", []() {
        server.send(200, "application/javascript", getJS());
    });

    // CSS (inline for single request)
    server.on("/style.css", []() {
        server.send(200, "text/css", getCSS());
    });

    // API: Get audio stream endpoint
    server.on("/stream", []() {
        server.send(200, "text/event-stream",
            "Cache-Control: no-cache\n"
            "Connection: keep-alive\n"
            "Access-Control-Allow-Origin: *\n\n");
    });

    // API: Save WiFi credentials
    server.on("/save", HTTP_POST, []() {
        if (server.hasArg("ssid") && server.hasArg("pass")) {
            prefs.putString("ssid", server.arg("ssid"));
            prefs.putString("pass", server.arg("pass"));
            server.send(200, "text/plain", "OK - Restarting...");
            delay(1000);
            ESP.restart();
        } else {
            server.send(400, "text/plain", "Missing parameters");
        }
    });

    // API: Get status
    server.on("/status", []() {
        String json = "{";
        json += "\"clientConnected\":" + String(clientConnected) + ",";
        json += "\"audioChunksSent\":" + String(audioChunksSent) + ",";
        json += "\"commandsReceived\":" + String(commandsReceived) + ",";
        json += "\"motors\":[";
        for (int i = 0; i < MOTOR_COUNT; i++) {
            json += String(motorAngles[i]);
            if (i < MOTOR_COUNT - 1) json += ",";
        }
        json += "]}";
        server.send(200, "application/json", json);
    });

    // Captive portal redirect
    server.on("/generate_204", []() {
        server.sendHeader("Location", "http://192.168.1.1/");
        server.send(302);
    });

    server.begin();

    // DNS for captive portal
    dnsServer.start(53, "*", apIP);
}

// ============================================
// WEBSOCKET EVENT HANDLER
// ============================================
void handleWebSocketEvent(uint8_t num, WStype_t type, uint8_t *payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            Serial.printf("Client %d disconnected\n", num);
            clientConnected = false;
            break;

        case WStype_CONNECTED:
            Serial.printf("Client %d connected from %s\n", num, payload);
            clientConnected = true;
            audioChunksSent = 0;
            commandsReceived = 0;
            // Request client to start sending
            webSocket.sendTXT(num, "{\"cmd\":\"start\"}");
            break;

        case WStype_TEXT:
            payload[length] = 0;  // Null terminate
            processCommand((const char*)payload);
            break;

        case WStype_BIN:
        case WStype_ERROR:
        case WStype_FRAGMENT_TEXT_START:
        case WStype_FRAGMENT_BIN_START:
        case WStype_FRAGMENT:
        case WStype_FRAGMENT_FIN:
        default:
            break;
    }
}

// ============================================
// PROCESS COMMAND FROM CONNECTED DEVICE
// ============================================
void processCommand(const char* json) {
    commandsReceived++;

    // Parse motor angle commands
    // Expected format: {"m0":90,"m1":45,"m2":135,"m3":90}
    // Or: {"motors":[90,45,135,90]}

    if (strstr(json, "m0") != NULL || strstr(json, "motors") != NULL) {
        // Simple parsing - extract numbers
        for (int i = 0; i < MOTOR_COUNT; i++) {
            char key[8];
            snprintf(key, sizeof(key), "m%d", i);
            char* ptr = strstr((char*)json, key);
            if (ptr) {
                ptr = strchr(ptr, ':');
                if (ptr) {
                    motorAngles[i] = atof(ptr + 1);
                    motorAnglesValid[i] = true;
                }
            }
        }
    }

    // Parse array format: {"motors":[90,45,135,90]}
    char* motorsStart = strstr((char*)json, "\"motors\"");
    if (motorsStart) {
        motorsStart = strchr(motorsStart, '[');
        if (motorsStart) {
            motorsStart++;
            for (int i = 0; i < MOTOR_COUNT && i < 4; i++) {
                motorAngles[i] = atof(motorsStart);
                motorAnglesValid[i] = true;
                motorsStart = strchr(motorsStart, ',');
                if (!motorsStart) break;
                motorsStart++;
            }
        }
    }
}

// ============================================
// SEND AUDIO CHUNK TO CONNECTED DEVICE
// ============================================
void sendAudioChunk() {
    if (!clientConnected) return;

#ifndef PIO_CI_BUILD
    // Read audio from I2S
    size_t bytesRead = 0;
    i2s_read(I2S_NUM_0, audioBuffer, sizeof(audioBuffer), &bytesRead, 0);
#else
    // Stub: generate dummy audio data for CI
    size_t bytesRead = sizeof(audioBuffer);
    for (size_t i = 0; i < sizeof(audioBuffer) / sizeof(int16_t); i++) {
        audioBuffer[i] = (int16_t)(rand() % 65536 - 32768);
    }
#endif

    if (bytesRead > 0) {
        audioBytesRead = bytesRead / sizeof(int16_t);

        // Send raw audio as binary (most efficient)
        // Client expects: {"samples":[raw int16 array], "sampleRate":16000}
        webSocket.sendBIN(0, (uint8_t*)audioBuffer, audioBytesRead * sizeof(int16_t));
        audioChunksSent++;
    }
}

// ============================================
// BROADCAST STATUS TO CLIENT
// ============================================
void broadcastStatus() {
    if (!clientConnected) return;

    char status[128];
    snprintf(status, sizeof(status),
        "{\"status\":\"ok\",\"motors\":[%d,%d,%d,%d],\"sent\":%lu,\"recv\":%lu}",
        (int)motorAngles[0], (int)motorAngles[1], (int)motorAngles[2], (int)motorAngles[3],
        audioChunksSent, commandsReceived);

    webSocket.sendTXT(0, status);
}

// ============================================
// UPDATE MOTOR POSITIONS
// ============================================
void updateMotors() {
#if USE_PCA9685
    // PCA9685 code would go here
#else
    for (int i = 0; i < MOTOR_COUNT; i++) {
        if (motorAnglesValid[i]) {
            servos[i].write((int)motorAngles[i]);
        }
    }
#endif
}

// ============================================
// HTML - MINIMAL SINGLE FILE APP
// ============================================
String getHTML() {
    return R"rawl(<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>OMNISOUND</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <div id="app">
        <header>
            <h1>🎵 OMNISOUND</h1>
            <span id="status" class="disconnected">Disconnected</span>
        </header>
        <main>
            <div class="card">
                <h2>Audio Visualizer</h2>
                <canvas id="waveform" width="400" height="150"></canvas>
                <canvas id="spectrum" width="400" height="150"></canvas>
            </div>
            <div class="card motors">
                <h2>Motor Status</h2>
                <div id="motor-container"></div>
            </div>
            <div class="card controls">
                <h2>Controls</h2>
                <button id="start-btn">Start</button>
                <button id="stop-btn" disabled>Stop</button>
                <input type="range" id="sensitivity" min="0" max="100" value="50">
                <label>Sensitivity</label>
            </div>
        </main>
    </div>
    <script src="/app.js"></script>
</body>
</html>)rawl";
}

// ============================================
// CSS - COMPACT STYLES
// ============================================
String getCSS() {
    return R"rawl(*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:#0d1117;color:#c9d1d9;min-height:100vh}header{display:flex;justify-content:space-between;align-items:center;padding:1rem;background:#161b22;border-bottom:1px solid #30363d}h1{font-size:1.5rem}#status{padding:.25rem .5rem;border-radius:4px;font-size:.875rem}.disconnected{background:#f8514920;color:#f85149}.connected{background:#23863620;color:#3fb950}main{padding:1rem;max-width:800px;margin:0 auto}.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1rem;margin-bottom:1rem}canvas{display:block;width:100%;background:#0d1117;border-radius:4px;margin:.5rem 0}.motors{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:.5rem}.motor{display:flex;flex-direction:column;align-items:center;padding:.5rem;background:#21262d;border-radius:4px}.motor-angle{font-size:1.5rem;font-weight:bold}.controls button{padding:.5rem 1rem;margin:.25rem;border:none;border-radius:4px;cursor:pointer;background:#238636;color:#fff}.controls button:disabled{background:#484f58;cursor:not-allowed}.controls input{width:100%;margin:.5rem 0})rawl";
}

// ============================================
// JAVASCRIPT - ALL PROCESSING HERE
// ============================================
String getJS() {
    return R"rawl(
// OMNISOUND - CLIENT-SIDE PROCESSING
// All FFT, beat detection, motor mapping done here
// ESP32 only captures audio and moves servos

const WS_URL = `ws://${location.hostname}:81`;
const SAMPLE_RATE = 16000;
const MOTOR_COUNT = 4;
const FFT_SIZE = 512;

// State
let ws = null;
let audioContext = null;
let analyser = null;
let isRunning = false;
let motorAngles = [90, 90, 90, 90];
let motorModes = ['frequency_band', 'frequency_band', 'frequency_band', 'beat'];
let beatTime = 0;
let lastBeatTime = 0;

// Motor frequency mappings
const MOTOR_RANGES = [
    { min: 20, max: 200, name: 'Bass' },
    { min: 200, max: 800, name: 'Mid' },
    { min: 800, max: 8000, name: 'High' },
    { mode: 'beat' }
];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initUI();
    connectWebSocket();
});

function initUI() {
    // Create motor displays
    const container = document.getElementById('motor-container');
    for (let i = 0; i < MOTOR_COUNT; i++) {
        const div = document.createElement('div');
        div.className = 'motor';
        div.innerHTML = `<span>M${i}</span><span class="motor-angle" id="m${i}">90°</span><small>${MOTOR_RANGES[i].name}</small>`;
        container.appendChild(div);
    }

    // Buttons
    document.getElementById('start-btn').onclick = start;
    document.getElementById('stop-btn').onclick = stop;
}

function connectWebSocket() {
    ws = new WebSocket(WS_URL);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
        document.getElementById('status').textContent = 'Connected';
        document.getElementById('status').className = 'connected';
        console.log('Connected to ESP32');
    };

    ws.onclose = () => {
        document.getElementById('status').textContent = 'Disconnected';
        document.getElementById('status').className = 'disconnected';
        setTimeout(connectWebSocket, 2000);
    };

    ws.onmessage = async (event) => {
        if (typeof event.data === 'string') {
            // Text: status message
            const data = JSON.parse(event.data);
            if (data.status === 'ok' && data.motors) {
                // Update local angles from ESP32 feedback
            }
        } else {
            // Binary: raw audio from ESP32
            await processAudio(event.data);
        }
    };
}

async function processAudio(buffer) {
    if (!audioContext) {
        audioContext = new AudioContext();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = FFT_SIZE;
    }

    // Convert int16 to float32
    const int16 = new Int16Array(buffer);
    const samples = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
        samples[i] = int16[i] / 32768;
    }

    // FFT Analysis
    const frequencyData = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(frequencyData);

    // Draw visualizers
    drawWaveform(samples);
    drawSpectrum(frequencyData);

    // Process for motors
    processMotors(frequencyData);

    // Send motor angles back to ESP32
    sendMotorAngles();
}

function processMotors(freqData) {
    const binSize = SAMPLE_RATE / FFT_SIZE;

    for (let i = 0; i < MOTOR_COUNT; i++) {
        if (motorModes[i] === 'frequency_band') {
            const range = MOTOR_RANGES[i];
            const startBin = Math.floor(range.min / binSize);
            const endBin = Math.floor(range.max / binSize);

            // Calculate average amplitude in band
            let sum = 0;
            let count = 0;
            for (let j = startBin; j < endBin && j < freqData.length; j++) {
                sum += freqData[j];
                count++;
            }
            const amplitude = count > 0 ? (sum / count) / 255 : 0;

            // Map to angle (45-135 degrees)
            motorAngles[i] = 45 + amplitude * 90;

        } else if (motorModes[i] === 'beat') {
            // Beat detection from low frequencies
            const bassSum = freqData[0] + freqData[1] + freqData[2];
            const isBeat = bassSum > 200;

            const now = Date.now();
            if (isBeat && now - lastBeatTime > 200) {
                motorAngles[i] = 135;  // Kick
                lastBeatTime = now;
            } else if (now - lastBeatTime > 80) {
                motorAngles[i] = 90;   // Rest
            }
        }
    }
}

function sendMotorAngles() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    // Send compact format: {"m0":90,"m1":45,"m2":135,"m3":90}
    const cmd = `{"m0":${Math.round(motorAngles[0])},"m1":${Math.round(motorAngles[1])},"m2":${Math.round(motorAngles[2])},"m3":${Math.round(motorAngles[3])}`;
    ws.send(cmd);

    // Update UI
    for (let i = 0; i < MOTOR_COUNT; i++) {
        document.getElementById(`m${i}`).textContent = Math.round(motorAngles[i]) + '°';
    }
}

function drawWaveform(samples) {
    const canvas = document.getElementById('waveform');
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = '#58a6ff';
    ctx.lineWidth = 1;
    ctx.beginPath();

    const step = Math.floor(samples.length / width);
    for (let x = 0; x < width; x++) {
        const y = (samples[x * step] + 1) * height / 2;
        ctx.lineTo(x, y);
    }
    ctx.stroke();
}

function drawSpectrum(freqData) {
    const canvas = document.getElementById('spectrum');
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, width, height);

    const barWidth = width / freqData.length;
    for (let i = 0; i < freqData.length; i++) {
        const barHeight = (freqData[i] / 255) * height;
        ctx.fillStyle = `hsl(${(i / freqData.length) * 360}, 70%, 50%)`;
        ctx.fillRect(i * barWidth, height - barHeight, barWidth - 1, barHeight);
    }
}

function start() {
    isRunning = true;
    document.getElementById('start-btn').disabled = true;
    document.getElementById('stop-btn').disabled = false;
}

function stop() {
    isRunning = false;
    document.getElementById('start-btn').disabled = false;
    document.getElementById('stop-btn').disabled = true;
}
    )rawl";
}