# Hardware Schematics & Electrical Interface Guide

**Project:** Haptic Needle Digital Twin (Unreal Engine 5)  
**Document:** Sensor Interface Circuit Schematics & Assembly Manual  
**Document Revision:** 1.0.0  
**Target Hardware:** 9-Channel Piezoelectric / Piezoresistive Transducer Array & Microcontroller Interface  
**Companion Software:** `Source/RMVR/SensorScript/APizeoSensorInput.cpp`, `Arduino Test Pizeo.py`

---

## 1. System Architecture & Transduction Principles

The haptic needle insertion twin interfaces a 9-channel sensor array (Channels 0 through 8) with an Arduino microcontroller. Sensor signals represent discrete physical contact events, acoustic shockwaves (e.g., needle "pop" through tissue layers), operator grip pressure, and skin-traction dynamics. The Arduino microcontroller reads analog transient voltages, converts them into validated event triggers, and transmits digit identifiers (`'0'` through `'8'` followed by `\n`) across USB Serial at **115,200 baud** to the Unreal Engine 5 receiver (`APizeoSensorInput`).

```
 +-----------------------------------------------------------------------------------+
 |                             PHYSICAL INTERACTION LAYER                            |
 |                                                                                   |
 |  [Cannula / Needle Grip Sensors]                 [Silicone Arm Phantom Sensors]   |
 |  • Ch 0: Thumb Grip Pad                          • Ch 5: Forearm Skin Traction    |
 |  • Ch 1: Index Stabilizer                        • Ch 6: Dorsal Vein Wall Pop     |
 |  • Ch 2: Catheter Advance Flange                 • Ch 7: Deep Fascia Over-Puncture|
 |  • Ch 3: Hub Axial Stress                        • Ch 8: Arm Boundary Margin      |
 |  • Ch 4: Bevel Acoustic Pickup                                                    |
 +----------------------------------------+------------------------------------------+
                                          | Analog Transients (0 - 50V unprotected)
                                          v
 +-----------------------------------------------------------------------------------+
 |                        SIGNAL CONDITIONING & PROTECTION RAIL                      |
 |                                                                                   |
 |  • 1.0 MΩ Bleed Resistors: Discharges capacitive charge accumulation (tau ~ RC)   |
 |  • 5.1V Zener Diodes (1N4733A): Clamps high-voltage inductive/piezo strike spikes  |
 |  • 1.0 kΩ Series Resistors: Limits current into microcontroller ADC ESD rails     |
 +----------------------------------------+------------------------------------------+
                                          | Safe 0.0V - 5.0V Analog Signals
                                          v
 +-----------------------------------------------------------------------------------+
 |                        MICROCONTROLLER (Arduino Mega / Nano)                      |
 |                                                                                   |
 |  • 10-bit Successive Approximation ADC (Pins A0 - A8)                             |
 |  • Refractory Debounce Filter (50 ms window against mechanical ring-down)         |
 |  • Serial Packet Formatter: Transmits ASCII '0'..'8' @ 115200 baud                |
 +----------------------------------------+------------------------------------------+
                                          | USB Virtual COM Port (115200 baud)
                                          v
 +-----------------------------------------------------------------------------------+
 |                        UNREAL ENGINE 5 DIGITAL TWIN ENGINE                        |
 |                                                                                   |
 |  • APizeoSensorInput::SerialWorker() worker thread polling COM port               |
 |  • OnPiezoHit(SensorIndex) Dynamic Multicast Delegate Broadcast                   |
 |  • Constraint Validator: Permits/prohibits virtual needle advancement             |
 +-----------------------------------------------------------------------------------+
```

### 1.1 Why Protection & Discharge Circuitry is Mandatory
1. **Piezoelectric Voltage Spikes:** Lead zirconate titanate (PZT) ceramic disks operate in the $d_{33}$ longitudinal and $d_{31}$ transverse piezoelectric modes. When subjected to a rapid mechanical impact (such as a needle strike against a cartilage substrate or a snap-through puncture of a vein wall), high-impedance PZT disks can generate open-circuit transients exceeding **30V to 80V**. Directly exposing an ATmega328P or ATmega2560 ADC input pin (rated for absolute maximum $V_{CC} + 0.5\text{ V} \approx 5.5\text{ V}$) to such voltages will blow the microcontroller's internal clamping diodes and permanently damage the ADC multiplexer.
2. **5.1V Zener Diode Clamping:** A 1N4733A 5.1V 1W Zener diode connected antiparallel across the signal line clamps any positive voltage spike to precisely $5.1\text{ V}$, safely within the input tolerance of the ADC, while clamping reverse-polarity recoil swings to $-0.7\text{ V}$.
3. **1.0 MΩ Bleed / Pull-Down Resistor:** Piezo elements behave electrically as high-impedance voltage sources in series with an internal capacitance ($C_{\text{piezo}} \approx 10\text{ nF} - 30\text{ nF}$). Without a bleed path, charges accumulated from repeated flexing remain trapped on the electrodes, creating a DC voltage offset that saturates the ADC and prevents subsequent hits from registering. A $1.0\text{ M}\Omega$ resistor establishes an RC discharge time constant:
   $$\tau = R \cdot C \approx 1.0\times 10^6\,\Omega \times 15\times 10^{-9}\,\text{F} = 15\text{ ms}$$
   This allows sharp mechanical transients to be captured by the ADC while rapidly bleeding the charge back to 0V ground within 30–50 ms.
4. **1.0 kΩ Series Resistor:** Inserted between the Zener clamp and the MCU ADC pin to limit transient clamp current to under $5\text{ mA}$ during sub-microsecond rise times before the Zener diode fully enters avalanche breakdown.

---

## 2. Circuit Schematics

### 2.1 Single-Channel Conditioning Circuit (Channel $n$, $n \in [0..8]$)

```
                           PIEZO TRANSDUCER / FSR
                           +--------------------+
                           |                    |
                           |   PIEZO CERAMIC    |
                           |      DISC / FSR    |
                           |                    |
                           +---------+----------+
                                     | Positive (Red Lead)
                                     |
                                     +---------------------------+
                                     |                           |
                                     |                           |
                                 +---+---+                       |
                                 |       |                       |
                                 |  1MΩ  | [R_BLEED]             |
                                 | 1/4W  | Discharge             |
                                 |       | Resistor              |
                                 +---+---+                       |
                                     |                           |
                                     +--------------------+      |
                                     |                    |      |
                                     |                 +--+--+   |
                                     |                 |  /  |   |
                                     |      1N4733A    | /   |   |
                                     |       5.1V      |/    |   |
                                     |    ZENER DIODE  +-----+   |
                                     |                 |  |  |   |
                                     |                 +--+--+   |
                                     |                    | Cathode (Barred side)
                                     |                    |      |
                                     +--------------------+------+
                                     |
                                     |
                                 +---+---+
                                 |  1kΩ  | [R_SERIES]
                                 | 1/4W  | Current Limiter
                                 +---+---+
                                     |
                                     v
                        TO ARDUINO ANALOG PIN A[n]
                        (e.g., A0 for Channel 0)


                                     |
                           +---------+----------+
                           | Negative (Black)   |
                           | Common Ground Rail |
                           +---------+----------+
                                     |
                                     v
                            COMMON GND RAIL (0V)
```

---

### 2.2 Complete 9-Channel Multi-Bus Schematic (Arduino Mega 2560 Direct Architecture)

The Arduino Mega 2560 features 16 native ADC channels (`A0` to `A15`), allowing all 9 channels (`Ch 0` to `Ch 8`) to be sampled concurrently without external analog multiplexing.

```
+=============================================================================================================+
|                                    9-CHANNEL ANALOG SENSOR INTERFACE BUS                                    |
+=============================================================================================================+

  SENSOR ELEMENT                     PROTECTION & BLEED STAGE                       ARDUINO MEGA 2560
 ----------------                    ------------------------                       -----------------
  CH 0: Thumb Grip    (+) ---+-------[ 1MΩ ]---+---[ 1N4733A 5.1V ]---+---[ 1kΩ ]---> ANALOG PIN A0
  (15mm Piezo)        (-) ---|--- GND          |   (Cathode to Sig)   |
                             +-----------------+----------------------+

  CH 1: Index Stab.   (+) ---+-------[ 1MΩ ]---+---[ 1N4733A 5.1V ]---+---[ 1kΩ ]---> ANALOG PIN A1
  (15mm Piezo)        (-) ---|--- GND          |                      |
                             +-----------------+----------------------+

  CH 2: Catheter Wing (+) ---+-------[ 1MΩ ]---+---[ 1N4733A 5.1V ]---+---[ 1kΩ ]---> ANALOG PIN A2
  (FSR / Piezo)       (-) ---|--- GND          |                      |
                             +-----------------+----------------------+

  CH 3: Hub Junction  (+) ---+-------[ 1MΩ ]---+---[ 1N4733A 5.1V ]---+---[ 1kΩ ]---> ANALOG PIN A3
  (20mm Piezo)        (-) ---|--- GND          |                      |
                             +-----------------+----------------------+

  CH 4: Bevel Stylet  (+) ---+-------[ 1MΩ ]---+---[ 1N4733A 5.1V ]---+---[ 1kΩ ]---> ANALOG PIN A4
  (Micro Piezo/Film)  (-) ---|--- GND          |                      |
                             +-----------------+----------------------+

  CH 5: Skin Anchor   (+) ---+-------[ 1MΩ ]---+---[ 1N4733A 5.1V ]---+---[ 1kΩ ]---> ANALOG PIN A5
  (27mm Piezo)        (-) ---|--- GND          |                      |
                             +-----------------+----------------------+

  CH 6: Vein Target   (+) ---+-------[ 1MΩ ]---+---[ 1N4733A 5.1V ]---+---[ 1kΩ ]---> ANALOG PIN A6
  (20mm Piezo)        (-) ---|--- GND          |                      |
                             +-----------------+----------------------+

  CH 7: Deep Fascia   (+) ---+-------[ 1MΩ ]---+---[ 1N4733A 5.1V ]---+---[ 1kΩ ]---> ANALOG PIN A7
  (20mm Piezo)        (-) ---|--- GND          |                      |
                             +-----------------+----------------------+

  CH 8: Arm Perimeter (+) ---+-------[ 1MΩ ]---+---[ 1N4733A 5.1V ]---+---[ 1kΩ ]---> ANALOG PIN A8
  (27mm Piezo)        (-) ---|--- GND          |                      |
                             +-----------------+----------------------+

  COMMON BUS:
  GND (All Sensor - Leads, All 1M Resistor Bottoms, All Zener Anodes) -------------> POWER BUS GND
  VCC (+5V Power Rail from Arduino for optional FSR bias voltage) ------------------> POWER BUS +5V
  COMMUNICATION:
  USB Type-B Port ------------------------------------------------------------------> HOST PC (COMx @ 115200)
+=============================================================================================================+
```

---

### 2.3 Alternative Architecture: Arduino Nano V3 + CD74HC4067 Multiplexer

For ultra-compact installations where an Arduino Nano is preferred (which possesses only 8 analog pins `A0`–`A7`), a CD74HC4067 16-channel analog multiplexer routes Channels 0–8 into single pin `A0` using digital selection lines `D2`, `D3`, `D4`, `D5`:

```
           +-------------------------------------------------------------+
           |                 CD74HC4067 16:1 ANALOG MUX                  |
           |                                                             |
 Ch 0-8 -->| C0 - C8 (Each conditioned with 1MΩ pull-down & 5.1V Zener)  |
           |                                                             |
           | SIG (Common Analog Output) -------> Arduino Nano Pin A0     |
           | S0 (Channel Select Bit 0) --------> Arduino Nano Pin D2     |
           | S1 (Channel Select Bit 1) --------> Arduino Nano Pin D3     |
           | S2 (Channel Select Bit 2) --------> Arduino Nano Pin D4     |
           | S3 (Channel Select Bit 3) --------> Arduino Nano Pin D5     |
           | EN (Active Low Enable) -----------> GND                     |
           | VCC / GND ------------------------> +5V / GND               |
           +-------------------------------------------------------------+
```

---

## 3. Complete Pinout & Anatomical / Cannula Mapping Table

The table below maps hardware microcontroller pins to the channel indices emitted over the serial stream (`0` through `8`) and matches them with their clinical anatomical location, sensing modality, and role in Unreal Engine 5's insertion logic gate system.

| Channel Index | Arduino Mega Pin | Nano+Mux Channel | Sensor Type & Size | Physical Anatomical / Cannula Location | Sensing Role & Description | UE5 Insertion Logic Constraint |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **0** | `A0` | `C0` | 15 mm PZT Disc / FSR | **Cannula Grip: Primary Thumb Pad** | Measures thumb grip compression during needle positioning and alignment. | **Required Active:** Insertion is locked if thumb contact is absent. |
| **1** | `A1` | `C1` | 15 mm PZT Disc / FSR | **Cannula Grip: Index Finger Stabilizer** | Confirms two-point operator stabilization prior to skin puncture. | **Required Active:** Prevents single-finger uncontrolled needle advance. |
| **2** | `A2` | `C2` | 10 mm Thin FSR / Disc | **Cannula Push-Off Flange (Wing)** | Detects index finger sliding the catheter sleeve forward over the needle stylet. | **Gated Stage:** Catheter forward motion allowed only after vein entry pop (Ch 6). |
| **3** | `A3` | `C3` | 20 mm PZT Disc | **Needle Shaft / Hub Junction** | Captures axial mechanical strain and bending moments along the needle cannula. | **Safety Monitor:** Warns operator if bending force exceeds structural safety limits. |
| **4** | `A4` | `C4` | Micro Acoustic PZT / Film | **Needle Bevel & Stylet Core** | High-frequency acoustic pickup capturing tissue puncture shockwaves transmitted up cannula. | **Transient Trigger:** Emits puncture click and advances state machine on skin breach. |
| **5** | `A5` | `C5` | 27 mm PZT Disc | **Phantom: Forearm Skin Anchor** | Detects non-dominant hand traction stretching the skin taut before insertion. | **Pre-Condition:** Puncture disallowed if skin is slack (simulates rolling vein prevention). |
| **6** | `A6` | `C6` | 20 mm PZT Disc | **Phantom: Dorsal Venous Network Site** | Detects primary vein wall puncture "pop" and tactile give into lumen. | **Success Condition:** Triggers virtual venous flashback animation and blood return. |
| **7** | `A7` | `C7` | 20 mm PZT Disc | **Phantom: Deep Fascia / Periosteum** | Detects needle over-insertion striking deep fascial layer or simulated bone margin. | **Forbidden Condition:** Triggers failed attempt penalty, haematoma warning, and lockout. |
| **8** | `A8` | `C8` | 27 mm PZT Disc | **Phantom: Radial / Ulnar Margin Anchor** | Detects excessive patient arm movement or incorrect arm rest angle during procedure. | **Boundary Check:** Forces pause/reset if patient arm phantom shifts prematurely. |

---

## 4. Physical Assembly & Sensor Integration Guide

```
                      +=========================================+
                      |       NEEDLE / CANNULA SENSOR RIG       |
                      +=========================================+

                       Thumb Pad Sensor (Ch 0)
                              +-----+
                              | [0] |
                              +--+--+
                                 |  Cannula Hub Housing
           Needle Bevel          |  +-------------+    Push-off Wing (Ch 2)
              |                  |  |             |      +-----+
              v                  v  |             |      | [2] |
         ============\===========|==+====|========|======+-----+
                      \          |       |  [3]   |
                       \         |       +--------+
                        \        |     Hub Stress Sensor (Ch 3)
                         \       |
                          \      v
                           +----+ [1]
                           Index Stabilizer (Ch 1)
```

### 4.1 Cannula & Training Needle Assembly
1. **Surface Preparation:** Clean the plastic cannula hub (standard 18-gauge or 20-gauge BD Insyte-style catheter) with 99% isopropyl alcohol (IPA) to eliminate molding release oils.
2. **Mounting Grip Sensors (Ch 0 & Ch 1):**
   - Apply a $0.05\text{ mm}$ strip of high-shear double-sided Kapton tape or a tiny drop of cyanoacrylate (Loctite 401) to the lateral grip wings.
   - Bond 15mm piezoelectric ceramic discs (brass plate facing outward, ceramic side facing inward) or 10mm FSRs to the thumb and index finger contact points.
   - Insulate solder joints with UV-cured optical adhesive or marine-grade heat-shrink tubing to prevent human body perspiration from shorting high-impedance lines.
3. **Catheter Push-Off Flange Sensor (Ch 2):**
   - Affix a miniature thin-film pressure sensor or 10mm piezo disc directly to the trailing shoulder of the catheter push-tab.
   - Route lead wires along the top spine of the cannula with a slack loop to allow forward catheter travel without snapping wire leads.
4. **Hub Junction & Acoustic Transducer (Ch 3 & Ch 4):**
   - The stainless steel needle shaft acts as an acoustic waveguide for transient stress waves.
   - Mount the ceramic acoustic pickup (Ch 4) directly against the rear metallic needle collar inside the clear flashback chamber using rigid cyanoacrylate. This mechanical coupling ensures that high-frequency vibrations from the bevel cutting tissue are faithfully transmitted to the transducer.
   - Secure the 20mm axial strain piezo (Ch 3) between the hub rear and the grip barrel.
5. **Lead Wire Sizing & Strain Relief:**
   - Use ultra-flexible **32 AWG to 36 AWG enameled copper magnet wire** or silicone-jacketed stranded wire for all needle-borne connections. Rigid wiring alters the tactile weight and hand-feel of the needle, compromising simulation fidelity.
   - Bundle all 5 needle leads into a single lightweight spiral sleeve, securing the bundle at the rear of the hub with heat-shrink tubing.

---

### 4.2 Medical Phantom Arm Sensor Mounting

```
        +====================================================================+
        |                 SILICONE PHANTOM ARM LAYER STACK                   |
        +====================================================================+

   Top Surface (Air)
   ---------------------------------------------------------------------------
   [ Ch 5: Skin Anchor Piezo ]                  [ Dermal Layer: Shore 00-30 ]
   ---------------------------------------------------------------------------
          \
           v  Subcutaneous Fat Layer (Silicone Gel / EcoFlex)
             ======================================================
             |   Simulated Vein Tubing (Latex / Thin Silicone)    |
             |                                                    |
             |        +-----------------------------------+       |
             |        | [ Ch 6: Dorsal Vein Wall Sensor ] |       |
             |        +-----------------------------------+       |
             ======================================================
          /
   ---------------------------------------------------------------------------
   [ Ch 7: Deep Fascia / Periosteum Strike Sensor (Under Vein Tube) ]
   ---------------------------------------------------------------------------
   Rigid Structural Arm Core (Rigid Polyurethane / Wood Skeleton)
   ---------------------------------------------------------------------------
   [ Ch 8: Radial / Margin Stability Sensor (Arm Periphery Anchor) ]
   ===========================================================================
```

1. **Phantom Layer Composition:**
   - **Epidermis / Dermis:** Platinum-cure silicone elastomer (Smooth-On Ecoflex 00-30 or Dragon Skin 10) mixed with flesh-tone silicone pigment. Shore hardness of 10A–30A replicates human subcutaneous resistance.
   - **Simulated Veins:** 4.0 mm OD / 3.0 mm ID thin-walled red latex or silicone tubing filled with simulated blood solution (water + glycerol + red dye).
2. **Sensor Positioning:**
   - **Ch 5 (Forearm Skin Traction):** Surface-bonded 15 mm proximal to the intended puncture zone. Measures shear deformation when the clinician's thumb stretches the patient's skin taut.
   - **Ch 6 (Dorsal Vein Wall Pop):** Embedded directly beneath the anterior surface of the vein tubing. Acoustic shockwaves from needle bevel penetration compress the piezo against the backing cushion, generating a sharp negative-to-positive transient pulse.
   - **Ch 7 (Deep Fascia Strike):** Bonded to the rigid substrate beneath the vein lumen (depth: $8.0\text{ mm}$ below skin surface). Triggers if the needle pierces through both walls of the vein (transfixion).
   - **Ch 8 (Arm Boundary Anchor):** Mounted to the distal arm cradle to ensure baseline stabilization.
3. **Acoustic & Mechanical Coupling:**
   - Use a thin layer of degassed clear silicone gel or medical ultrasound coupling gel between the piezo surface and the tubing to eliminate air pockets (which cause acoustic impedance mismatches).
4. **Noise Shielding & Grounding:**
   - High-impedance ($1.0\text{ M}\Omega$) analog circuits are sensitive to 50 Hz/60 Hz electromagnetic induction from ambient AC mains wiring and fluorescent lighting.
   - Line the base of the phantom arm cavity with adhesive conductive copper foil tape connected directly to the Arduino ground bus (`GND`).
   - Use shielded twisted-pair cabling for sensor runs extending beyond $30\text{ cm}$.

---

## 5. Firmware Signal Conditioning & Serial Protocol

### 5.1 Microcontroller Processing Algorithm
The Arduino firmware reads analog pins $A_0$ through $A_8$ inside an optimized high-frequency polling loop:
1. **Analog Read & Noise Floor Subtraction:** Samples 10-bit values ($0 - 1023$, representing $0.0\text{ V} - 5.0\text{ V}$, resolution: $4.88\text{ mV/step}$).
2. **Threshold Comparison:**
   - Grip Sensors (Ch 0, 1): Static threshold $> 120$ (approx. $0.6\text{ V}$) indicates firm pinch hold.
   - Transient Pop Sensors (Ch 4, 6, 7): Dynamic delta threshold $\Delta V / \Delta t > 180$ indicates an acoustic transient puncture shockwave rather than slow drift.
3. **Refractory Lockout (Debounce):** When a channel triggers, a hardware timer locks that channel for **$50\text{ ms}$** to prevent mechanical ring-down oscillations from sending duplicate hit events.
4. **Serial Transmission:** Immediately writes the single-byte ASCII digit followed by a newline:
   ```cpp
   Serial.print(channelIndex);
   Serial.print('\n');
   ```

### 5.2 Reference Arduino Calibration Sketch
```cpp
/*
 * Haptic Needle Twin - 9-Channel Sensor Array Firmware
 * Baud Rate: 115200 bps | Target: Arduino Mega 2560
 */

const int NUM_CHANNELS = 9;
const int analogPins[NUM_CHANNELS] = {A0, A1, A2, A3, A4, A5, A6, A7, A8};
const int thresholds[NUM_CHANNELS] = {120, 120, 100, 150, 180, 110, 170, 200, 130};

unsigned long lastTriggerTime[NUM_CHANNELS] = {0};
const unsigned long DEBOUNCE_MS = 50; // Refractory debounce window

void setup() {
    Serial.begin(115200);
    while (!Serial) { ; } // Wait for serial port connection
    for (int i = 0; i < NUM_CHANNELS; i++) {
        pinMode(analogPins[i], INPUT);
    }
}

void loop() {
    unsigned long currentMillis = millis();

    for (int ch = 0; ch < NUM_CHANNELS; ch++) {
        int rawVal = analogRead(analogPins[ch]);

        if (rawVal > thresholds[ch]) {
            if (currentMillis - lastTriggerTime[ch] >= DEBOUNCE_MS) {
                lastTriggerTime[ch] = currentMillis;
                // Transmit single digit recognized by APizeoSensorInput.cpp
                Serial.println(ch);
            }
        }
    }
}
```

### 5.3 Unreal Engine 5 Ingestion Compatibility
The output transmitted by this circuit and firmware connects directly with `Source/RMVR/SensorScript/APizeoSensorInput.cpp`:
- Character parser: `if (FChar::IsDigit(c)) { int32 SensorIndex = c - '0'; }`
- Triggers dynamic delegate: `OnPiezoHit.Broadcast(SensorIndex);`
- Fires Blueprint event: `OnPizeoHitBP(SensorIndex);`
- Guaranteed sub-$5\text{ ms}$ latency from physical needle puncture to virtual visual twin response.
