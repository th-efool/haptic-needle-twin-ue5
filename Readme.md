# Haptic Needle Twin (UE5)


![Status](https://img.shields.io/badge/status-research--prototype-yellow.svg)
![Engine](https://img.shields.io/badge/engine-Unreal%20Engine%205-black.svg)
![Domain](https://img.shields.io/badge/domain-Digital%20Twin%20%7C%20Medical%20Simulation-blue.svg)
![Hardware](https://img.shields.io/badge/hardware-Arduino-green.svg)
![Focus](https://img.shields.io/badge/focus-Soft--Body%20Electronics-informational.svg)

A real‑time **Unreal Engine 5 digital twin** for simulating **cannula / needle insertion** using **haptic‑augmented physical inputs**. The system connects an **Arduino-based touch sensor array** to UE5, where sensor signals act as *hard constraints* on whether insertion is allowed, mimicking correct vs incorrect clinical technique.

This project explores the intersection of:

* **Medical simulation**
* **Digital twins**
* **Haptics & soft‑body electronics**
* **Human–machine interaction**

---

## Core Idea

A physical setup (Arduino + touch sensors) represents the **real-world needle / cannula interaction**.

* **Correct sensor activation pattern** → UE5 allows cannula insertion
* **Incorrect / premature / misaligned touch** → insertion is blocked

This enforces *procedural correctness* rather than simple animation playback, turning UE5 into a **logic‑validated twin**, not just a visual one.

---

## System Architecture

```
[ Touch Sensors ]
        │
        ▼
[ Arduino ]  ── Serial / USB ──►  [ Unreal Engine 5 ]
                                       │
                                       ▼
                             Digital Twin + Logic Gate
```

### Data Flow

1. Touch sensors detect pressure/contact
2. Arduino samples & encodes sensor state
3. Data streamed over Serial
4. UE5 parses input in real time
5. Insertion logic validates sensor pattern
6. Needle/cannula state updates accordingly

---

## Hardware Setup

* **Arduino** (Uno / Nano / compatible)
* **Touch / pressure sensors** (capacitive or resistive)
* Optional:

  * Flexible or soft‑body conductive materials
  * Custom sensor matrices for research

> Sensor placement and timing are treated as *semantic input*, not binary buttons.

---

## Unreal Engine Side

* **Engine:** Unreal Engine 5.x
* **Input:** Serial communication (custom reader / plugin)
* **Logic Layer:**

  * Sensor validation gates
  * Insertion permission checks
  * Error state handling

### Insertion Rules (Example)

* All required sensors must be active
* Activation order must match expected sequence
* No forbidden sensor may trigger

Failing any rule immediately blocks insertion.

---

## Research Focus

This project is **not** about simple VR animation.

It investigates:

* Soft‑body electronics as *intent sensors*
* Real‑time constraint enforcement in digital twins
* Translating tactile correctness into simulation logic
* Training systems where *wrong touch = physical impossibility*

---

## Use Cases

* Medical training simulators
* Cannula / needle insertion practice
* Haptic‑augmented digital twins
* Research into soft electronic sensing

---

## Current Status

* Arduino ↔ UE5 serial communication established
* Touch sensor input mapped to UE logic
* Cannula insertion gated by sensor correctness
* Ongoing experimentation with soft‑body sensing

---

## Future Work

* Physics‑based soft tissue response
* Force feedback / haptic resistance
* Higher‑resolution sensor matrices
* ML‑based pattern recognition for touch validation

---

## Disclaimer

This is a **research & simulation project**, not a certified medical device. It is intended for experimentation, learning, and prototyping only.

