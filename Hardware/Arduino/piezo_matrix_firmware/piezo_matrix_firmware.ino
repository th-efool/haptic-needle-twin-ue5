/**
 * =====================================================================================
 *  HAPTIC NEEDLE TWIN (UE5) - 9-CHANNEL PIEZO / TACTILE SENSOR MATRIX FIRMWARE
 * =====================================================================================
 *  File: piezo_matrix_firmware.ino
 *  Target Architecture: Arduino AVR (Nano / Uno / Mega 2560), SAMD21, ESP32, Teensy
 *  Default Baud Rate:   115200 bps
 *  Receiver:            APizeoSensorInput.cpp (Unreal Engine 5 Digital Twin)
 * -------------------------------------------------------------------------------------
 *  DESCRIPTION:
 *  Production-ready firmware for a 3x3 (9-channel) piezoelectric / tactile sensor
 *  matrix simulating cannula/needle insertion puncture dynamics.
 *
 *  The firmware implements:
 *    1. Baseline ambient noise calibration on boot and on-demand recalibration.
 *    2. Adaptive thresholding with dynamic noise floor tracking (EMA).
 *    3. Asymmetric software debouncing & mechanical ringing damping (refractory lockout).
 *    4. Strict serial framing matching UE5 APizeoSensorInput parser: sends '0\n' - '8\n'.
 *    5. Interactive Serial debugging & diagnostics (toggleable via 'D' or compile flag).
 *    6. Configurable pin mappings for Arduino Nano/Uno (A0-A7 + D2) and Mega (A0-A8).
 * -------------------------------------------------------------------------------------
 *  PHYSICAL SENSOR COUPLING & HARDWARE SCHEMATIC:
 *
 *          Piezo Ceramic / PVDF Element          Arduino ADC Input Pin
 *                 +------------+
 *          (+) ---|            |-------------------+----------> Pin (e.g. A0)
 *                 |   SENSOR   |                   |
 *                 |  DISC /    |                  [R1] 1M Ohm Bleeder Resistor
 *                 |   MATRIX   |                   |
 *          (-) ---|            |---------+         |
 *                 +------------+         |         |
 *                                        |         |
 *                                       GND       GND
 *
 *  ELECTRICAL DESIGN NOTES:
 *  1. Bleeder Resistor (R1, 1M Ohm - 10M Ohm):
 *     Piezo elements act as capacitors that accumulate static charge under stress.
 *     A parallel bleeder resistor provides a DC discharge path to ground, establishing
 *     a stable zero-volt baseline and preventing ADC saturation.
 *  2. Clamping Protection (Optional, recommended for high impact):
 *     A Schottky diode (e.g., BAT54S or 1N5817) connected between ADC Pin and GND
 *     protects against negative voltage undershoots during mechanical recoil.
 *  3. Acoustic / Mechanical Cross-Talk Isolation:
 *     Mount each sensor disc on a silicone elastomer / EVA foam damping ring.
 *     Without dampening, needle puncture vibration travels through the acrylic / 3D-printed
 *     substrate and triggers adjacent sensors in the 3x3 matrix.
 * =====================================================================================
 */

#include <Arduino.h>

// =====================================================================================
// 1. HARDWARE SELECTION & PIN MAPPING CONFIGURATION
// =====================================================================================

// Supported Board Types:
#define BOARD_TYPE_AUTO     0   // Auto-detect based on compiler board definitions
#define BOARD_TYPE_NANO_UNO 1   // Arduino Nano / Uno (Pins A0-A7 + Digital D2)
#define BOARD_TYPE_MEGA     2   // Arduino Mega 2560 (Pins A0-A8 all true analog)
#define BOARD_TYPE_CUSTOM   3   // Custom user-defined pin assignments

// Select your board configuration here (or leave as AUTO):
#define SELECTED_BOARD BOARD_TYPE_AUTO

// Number of tactile matrix channels
#define NUM_CHANNELS 9

// 3x3 Matrix Physical Layout Reference:
// [ Ch 0 (A0) ]  [ Ch 1 (A1) ]  [ Ch 2 (A2) ]  -> Top Row
// [ Ch 3 (A3) ]  [ Ch 4 (A4) ]  [ Ch 5 (A5) ]  -> Mid Row (Ch 4: Target Puncture Center)
// [ Ch 6 (A6) ]  [ Ch 7 (A7) ]  [ Ch 8 (D2/A8)] -> Bottom Row

#if (SELECTED_BOARD == BOARD_TYPE_MEGA) || (defined(__AVR_ATmega1280__) || defined(__AVR_ATmega2560__))
    // Arduino Mega 2560: 16 true analog inputs (A0 - A15)
    static const uint8_t CHANNEL_PINS[NUM_CHANNELS] = {
        A0, A1, A2, A3, A4, A5, A6, A7, A8
    };
    static const bool PIN_IS_ANALOG[NUM_CHANNELS] = {
        true, true, true, true, true, true, true, true, true
    };
#elif (SELECTED_BOARD == BOARD_TYPE_NANO_UNO) || (defined(__AVR_ATmega328P__) || defined(__AVR_ATmega168__))
    // Arduino Nano / Uno: Nano provides A0..A7 (8 analog inputs).
    // The 9th channel (Index 8) is mapped to Digital Pin 2 (with internal pullup / external comparator).
    static const uint8_t CHANNEL_PINS[NUM_CHANNELS] = {
        A0, A1, A2, A3, A4, A5, A6, A7, 2
    };
    static const bool PIN_IS_ANALOG[NUM_CHANNELS] = {
        true, true, true, true, true, true, true, true, false
    };
#else
    // Generic / Fallback Pin Mapping
    static const uint8_t CHANNEL_PINS[NUM_CHANNELS] = {
        A0, A1, A2, A3, A4, A5, A6, A7, 2
    };
    static const bool PIN_IS_ANALOG[NUM_CHANNELS] = {
        true, true, true, true, true, true, true, true, false
    };
#endif

// =====================================================================================
// 2. SIGNAL PROCESSING & THRESHOLDING PARAMETERS
// =====================================================================================

// Default sensitivity threshold delta above ambient baseline (ADC units: 0 - 1023)
// A typical light needle touch produces 80-250 ADC delta; a firm puncture produces > 400.
#define DEFAULT_THRESHOLD_DELTA     120

// Minimum threshold delta safety clamp to prevent noise-floor self-triggering
#define MIN_THRESHOLD_DELTA          35

// Baseline calibration sample count during setup
#define CALIBRATION_SAMPLES         256

// Mechanical ringing debouncing refractory window (milliseconds).
// Piezo discs vibrate at their natural resonance (~2 kHz - 5 kHz) for 30-80ms post-hit.
// 100ms prevents double-counting single needle puncture events.
#define DEFAULT_DEBOUNCE_MS         100

// Hysteresis release ratio: signal must fall below (threshold * HYSTERESIS_FACTOR)
// before channel can transition from COOLDOWN back to IDLE.
#define HYSTERESIS_PERCENT           40

// Exponential Moving Average (EMA) shift weight for ambient baseline drift tracking.
// Shift factor of 6 = alpha of 1/64 (~0.015), providing slow drift compensation
// for thermal and dielectric relaxation without tracking dynamic needle hits.
#define EMA_DRIFT_SHIFT              6

// =====================================================================================
// 3. FIRMWARE STATE DEFINITIONS
// =====================================================================================

enum ChannelState : uint8_t {
    STATE_IDLE = 0,             // Normal monitoring; waiting for impact
    STATE_TRIGGERED,            // Hit registered; output transmitted
    STATE_COOLDOWN              // In refractory period; suppressing mechanical ringing
};

struct PiezoChannel {
    uint8_t       pin;
    bool          isAnalog;
    ChannelState  state;
    uint16_t      baseline;          // Calibrated ambient noise baseline (ADC counts)
    uint16_t      noiseSpread;       // Peak-to-peak ambient noise observed during calibration
    uint16_t      thresholdDelta;    // Dynamic trigger threshold delta above baseline
    uint16_t      lastRawValue;      // Most recent raw ADC sample
    uint16_t      peakValue;         // Peak amplitude captured during hit event
    uint32_t      triggerTimestamp;  // millis() timestamp when hit occurred
    uint16_t      debounceMs;        // Channel refractory window in ms
};

// Global state
static PiezoChannel g_Channels[NUM_CHANNELS];
static bool         g_DebugMode = false;         // False for clean UE5 output; True for diagnostics
static uint32_t     g_LastHeartbeatMs = 0;       // Heartbeat interval for debug telemetry
static uint32_t     g_TotalHitsDetected = 0;     // Total hit event counter

// =====================================================================================
// 4. FUNCTION DECLARATIONS
// =====================================================================================
void calibrateBaselines();
void sampleAndProcessChannels();
void handleSerialCommands();
void emitHitEvent(uint8_t channelIndex);
void printDebugBanner();
void printChannelDiagnostics();
void printHelpMenu();

// =====================================================================================
// 5. SETUP ROUTINE
// =====================================================================================
void setup() {
    // Initialize hardware UART at 115200 baud matching APizeoSensorInput.cpp
    Serial.begin(115200);

    // Allow power rails and internal ADC reference to stabilize
    delay(200);

    // Initialize pin modes
    for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
        g_Channels[i].pin = CHANNEL_PINS[i];
        g_Channels[i].isAnalog = PIN_IS_ANALOG[i];
        g_Channels[i].state = STATE_IDLE;
        g_Channels[i].thresholdDelta = DEFAULT_THRESHOLD_DELTA;
        g_Channels[i].debounceMs = DEFAULT_DEBOUNCE_MS;
        g_Channels[i].triggerTimestamp = 0;
        g_Channels[i].peakValue = 0;
        g_Channels[i].lastRawValue = 0;

        if (g_Channels[i].isAnalog) {
            pinMode(g_Channels[i].pin, INPUT);
        } else {
            // Digital pin for channel 8 on Nano/Uno with internal pullup
            pinMode(g_Channels[i].pin, INPUT_PULLUP);
        }
    }

    // Perform baseline ambient noise calibration
    calibrateBaselines();

    // If starting in debug mode, output boot diagnostics
    if (g_DebugMode) {
        printDebugBanner();
    }
}

// =====================================================================================
// 6. MAIN LOOP
// =====================================================================================
void loop() {
    // 1. Fast sensor acquisition and debouncing state machine
    sampleAndProcessChannels();

    // 2. Check for incoming Serial commands (debug toggle, sensitivity, calibration)
    if (Serial.available() > 0) {
        handleSerialCommands();
    }

    // 3. Periodic debug streaming (only active when debug mode is enabled)
    if (g_DebugMode) {
        uint32_t currentMs = millis();
        if (currentMs - g_LastHeartbeatMs >= 500) {
            g_LastHeartbeatMs = currentMs;
            printChannelDiagnostics();
        }
    }
}

// =====================================================================================
// 7. CALIBRATION ROUTINE
// =====================================================================================
/**
 * @brief Samples ambient electrical baseline and noise floor across all channels.
 * Calculates DC offset and peak noise spread to set dynamic trigger thresholds.
 */
void calibrateBaselines() {
    if (g_DebugMode) {
        Serial.println(F("[CALIB] Starting baseline calibration..."));
    }

    // Temporary accumulation buffers
    uint32_t accumulators[NUM_CHANNELS] = {0};
    uint16_t minObserved[NUM_CHANNELS];
    uint16_t maxObserved[NUM_CHANNELS];

    for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
        minObserved[i] = 1023;
        maxObserved[i] = 0;
    }

    // Warm-up dummy read to clear multiplexer residual charge
    for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
        if (g_Channels[i].isAnalog) {
            analogRead(g_Channels[i].pin);
        }
    }

    // Multi-sample statistical acquisition
    for (uint16_t s = 0; s < CALIBRATION_SAMPLES; s++) {
        for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
            uint16_t sample;
            if (g_Channels[i].isAnalog) {
                sample = analogRead(g_Channels[i].pin);
            } else {
                sample = (digitalRead(g_Channels[i].pin) == LOW) ? 1023 : 0;
            }

            accumulators[i] += sample;
            if (sample < minObserved[i]) minObserved[i] = sample;
            if (sample > maxObserved[i]) maxObserved[i] = sample;
        }
        delayMicroseconds(200);
    }

    // Finalize baseline offsets and adaptive thresholds
    for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
        if (g_Channels[i].isAnalog) {
            g_Channels[i].baseline = (uint16_t)(accumulators[i] / CALIBRATION_SAMPLES);
            g_Channels[i].noiseSpread = maxObserved[i] - minObserved[i];

            // Adaptive safety margin: threshold must exceed peak noise spread by at least 2x
            uint16_t adaptiveDelta = g_Channels[i].noiseSpread * 2 + 30;
            if (adaptiveDelta < DEFAULT_THRESHOLD_DELTA) {
                adaptiveDelta = DEFAULT_THRESHOLD_DELTA;
            }
            g_Channels[i].thresholdDelta = adaptiveDelta;
        } else {
            // Digital channel baseline: 0 = idle (pulled HIGH)
            g_Channels[i].baseline = 0;
            g_Channels[i].noiseSpread = 0;
            g_Channels[i].thresholdDelta = 512;
        }

        g_Channels[i].state = STATE_IDLE;
    }

    if (g_DebugMode) {
        Serial.println(F("[CALIB] Calibration complete. Ready for Unreal Engine 5."));
    }
}

// =====================================================================================
// 8. SENSOR ACQUISITION & PROCESSING ENGINE
// =====================================================================================
/**
 * @brief High-frequency sampling loop with ringing suppression and hysteresis debouncing.
 */
void sampleAndProcessChannels() {
    uint32_t now = millis();

    for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
        PiezoChannel& ch = g_Channels[i];

        // 1. Acquire raw sample
        uint16_t raw;
        if (ch.isAnalog) {
            raw = analogRead(ch.pin);
        } else {
            // Digital tactile switch or comparator: active LOW with pull-up
            raw = (digitalRead(ch.pin) == LOW) ? 1023 : 0;
        }
        ch.lastRawValue = raw;

        // 2. Compute dynamic delta from baseline
        int16_t delta = (int16_t)raw - (int16_t)ch.baseline;
        if (delta < 0) delta = 0; // Positive half-wave pressure spike

        // 3. Execute channel state machine
        switch (ch.state) {
            case STATE_IDLE: {
                // Check if impact spike exceeds trigger threshold
                if ((uint16_t)delta >= ch.thresholdDelta) {
                    ch.state = STATE_TRIGGERED;
                    ch.triggerTimestamp = now;
                    ch.peakValue = raw;

                    // Emit event to Unreal Engine 5 receiver
                    emitHitEvent(i);

                    // Transition to cooldown to suppress mechanical ringing
                    ch.state = STATE_COOLDOWN;
                } else {
                    // Slow baseline drift compensation (EMA) when sensor is idle and undisturbed
                    if (ch.isAnalog && delta < (ch.noiseSpread + 10)) {
                        // baseline = baseline + (raw - baseline) / 64
                        ch.baseline = ch.baseline + (((int32_t)raw - (int32_t)ch.baseline) >> EMA_DRIFT_SHIFT);
                    }
                }
                break;
            }

            case STATE_TRIGGERED: {
                // Immediate transition to cooldown
                ch.state = STATE_COOLDOWN;
                break;
            }

            case STATE_COOLDOWN: {
                // Track peak amplitude during post-impact ringing for diagnostics
                if (raw > ch.peakValue) {
                    ch.peakValue = raw;
                }

                // Verify refractory lockout duration has elapsed
                bool timeExpired = (now - ch.triggerTimestamp) >= ch.debounceMs;

                // Hysteresis check: signal must decay below fraction of trigger threshold
                uint16_t releaseThreshold = (ch.thresholdDelta * HYSTERESIS_PERCENT) / 100;
                bool signalSettled = ((uint16_t)delta <= releaseThreshold);

                if (timeExpired && signalSettled) {
                    ch.state = STATE_IDLE;
                    ch.peakValue = 0;
                }
                break;
            }
        }
    }
}

// =====================================================================================
// 9. SERIAL TRANSMISSION (UE5 COMPATIBILITY)
// =====================================================================================
/**
 * @brief Transmits hit event strictly matching APizeoSensorInput.cpp parser expectations.
 * APizeoSensorInput iterates through the serial buffer searching for ASCII digits:
 *   SensorIndex = c - '0';
 * Format: single digit character followed by newline (e.g. '0\n' .. '8\n').
 *
 * @param channelIndex Sensor index (0 through 8)
 */
void emitHitEvent(uint8_t channelIndex) {
    g_TotalHitsDetected++;

    if (!g_DebugMode) {
        // PRODUCTION MODE FOR UNREAL ENGINE 5:
        // Strictly send digit followed by newline. Do NOT add decorative text or spaces!
        Serial.print(channelIndex);
        Serial.print('\n');
    } else {
        // DIAGNOSTIC DEBUG MODE:
        Serial.print(F("[HIT] Channel: "));
        Serial.print(channelIndex);
        Serial.print(F(" | Raw: "));
        Serial.print(g_Channels[channelIndex].lastRawValue);
        Serial.print(F(" | Baseline: "));
        Serial.print(g_Channels[channelIndex].baseline);
        Serial.print(F(" | Delta: "));
        Serial.print((int16_t)g_Channels[channelIndex].lastRawValue - (int16_t)g_Channels[channelIndex].baseline);
        Serial.print(F(" | Total: "));
        Serial.println(g_TotalHitsDetected);

        // Also output the raw digit line for UE5 parser test verification
        Serial.print(channelIndex);
        Serial.print('\n');
    }
}

// =====================================================================================
// 10. SERIAL COMMAND PROCESSOR & DIAGNOSTICS
// =====================================================================================
/**
 * @brief Handles interactive commands over Serial Monitor without rebooting.
 */
void handleSerialCommands() {
    char cmd = (char)Serial.read();

    switch (cmd) {
        // Toggle Debug Mode
        case 'D':
        case 'd':
            g_DebugMode = !g_DebugMode;
            if (g_DebugMode) {
                Serial.println(F("\n[DBG] === DEBUG MODE ACTIVATED ==="));
                printDebugBanner();
            } else {
                Serial.println(F("\n[DBG] === PRODUCTION MODE ACTIVATED (Clean UE5 Protocol) ==="));
            }
            break;

        // Force Baseline Recalibration
        case 'C':
        case 'c':
            calibrateBaselines();
            break;

        // Increase Sensitivity (Decrease threshold delta)
        case '+':
        case '=':
            for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
                if (g_Channels[i].thresholdDelta > MIN_THRESHOLD_DELTA + 10) {
                    g_Channels[i].thresholdDelta -= 10;
                }
            }
            if (g_DebugMode) {
                Serial.print(F("[CONFIG] Sensitivity INCREASED. New Delta: "));
                Serial.println(g_Channels[0].thresholdDelta);
            }
            break;

        // Decrease Sensitivity (Increase threshold delta)
        case '-':
        case '_':
            for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
                if (g_Channels[i].thresholdDelta < 800) {
                    g_Channels[i].thresholdDelta += 10;
                }
            }
            if (g_DebugMode) {
                Serial.print(F("[CONFIG] Sensitivity DECREASED. New Delta: "));
                Serial.println(g_Channels[0].thresholdDelta);
            }
            break;

        // Print Status / Config Matrix
        case 'P':
        case 'p':
            printChannelDiagnostics();
            break;

        // Synthetic Test Trigger (simulate hit on channel 4 - Target Center)
        case 'T':
        case 't':
            emitHitEvent(4);
            break;

        // Help Menu
        case '?':
        case 'H':
        case 'h':
            printHelpMenu();
            break;

        // Ignore standard line-ending delimiters
        case '\r':
        case '\n':
            break;

        default:
            // Digits '0' - '8' can simulate manual hit triggers for testing
            if (cmd >= '0' && cmd <= '8') {
                uint8_t ch = cmd - '0';
                emitHitEvent(ch);
            }
            break;
    }
}

/**
 * @brief Prints system banner and hardware configuration table.
 */
void printDebugBanner() {
    Serial.println(F("========================================================="));
    Serial.println(F("   HAPTIC NEEDLE TWIN - 9-CHANNEL PIEZO SENSOR MATRIX   "));
    Serial.println(F("   Firmware Version: 1.0.0 | Baud: 115200 bps           "));
    Serial.println(F("   Target: Unreal Engine 5 APizeoSensorInput Receiver   "));
    Serial.println(F("========================================================="));
    Serial.println(F("Commands: [D]ebug Toggle | [C]alibrate | [+] / [-] Sens  "));
    Serial.println(F("          [P]rint Status | [T]est Hit  | [?] Help        "));
    Serial.println(F("---------------------------------------------------------"));
}

/**
 * @brief Prints tabular view of current sensor readings and baselines.
 */
void printChannelDiagnostics() {
    Serial.println(F("\n--- SENSOR MATRIX STATUS ---"));
    Serial.println(F("CH | Pin | Type    | Raw  | Base | Noise | Thresh | State"));
    Serial.println(F("---------------------------------------------------------"));

    for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
        PiezoChannel& ch = g_Channels[i];

        Serial.print(F(" "));
        Serial.print(i);
        Serial.print(F(" | "));

        if (ch.pin < 10) Serial.print(F(" "));
        Serial.print(ch.pin);
        Serial.print(F("  | "));

        Serial.print(ch.isAnalog ? F("Analog ") : F("Digital"));
        Serial.print(F(" | "));

        if (ch.lastRawValue < 100) Serial.print(F(" "));
        if (ch.lastRawValue < 10)  Serial.print(F(" "));
        Serial.print(ch.lastRawValue);
        Serial.print(F("  | "));

        if (ch.baseline < 100) Serial.print(F(" "));
        if (ch.baseline < 10)  Serial.print(F(" "));
        Serial.print(ch.baseline);
        Serial.print(F("  | "));

        if (ch.noiseSpread < 10) Serial.print(F(" "));
        Serial.print(ch.noiseSpread);
        Serial.print(F("    | "));

        Serial.print(ch.baseline + ch.thresholdDelta);
        Serial.print(F("    | "));

        switch (ch.state) {
            case STATE_IDLE:       Serial.println(F("IDLE")); break;
            case STATE_TRIGGERED:  Serial.println(F("HIT!")); break;
            case STATE_COOLDOWN:   Serial.println(F("COOL")); break;
        }
    }
    Serial.println(F("---------------------------------------------------------"));
}

/**
 * @brief Prints interactive command help menu.
 */
void printHelpMenu() {
    Serial.println(F("\n=== HAPTIC NEEDLE MATRIX FIRMWARE HELP ==="));
    Serial.println(F(" D / d  : Toggle Debug Mode (verbose diagnostics vs clean UE5 stream)"));
    Serial.println(F(" C / c  : Run Ambient Baseline Noise Calibration"));
    Serial.println(F(" + / =  : Increase sensitivity (lowers impact threshold)"));
    Serial.println(F(" - / _  : Decrease sensitivity (raises impact threshold)"));
    Serial.println(F(" P / p  : Print Channel Diagnostics Table"));
    Serial.println(F(" T / t  : Send synthetic needle impact on Channel 4 (Center)"));
    Serial.println(F(" 0 - 8  : Send synthetic needle impact on specified Channel"));
    Serial.println(F(" ? / H  : Display this help message"));
    Serial.println(F("==========================================\n"));
}
