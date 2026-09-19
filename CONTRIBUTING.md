# Contributing to Haptic Needle Twin (UE5)

Thank you for your interest in contributing to the **Haptic Needle Twin (UE5)** research project. This repository hosts an academic and experimental digital twin framework designed to investigate the intersection of **tactile sensing**, **soft-body electronics**, **logic-gated simulation**, and **medical procedural training** in Unreal Engine 5.

We welcome contributions from academic researchers, biomedical simulation engineers, haptics specialists, and Unreal Engine developers. To maintain scientific integrity, computational reproducibility, and code quality, please adhere to the guidelines outlined below.

---

## Table of Contents

1. [Academic Research Protocols & Ethics](#1-academic-research-protocols--ethics)
   - [Non-Clinical Research Disclaimer](#non-clinical-research-disclaimer)
   - [Scientific Reproducibility & Open Science](#scientific-reproducibility--open-science)
   - [Authorship & Attribution](#authorship--attribution)
   - [Contribution Tracks](#contribution-tracks)
2. [Code Style & Development Standards](#2-code-style--development-standards)
   - [Unreal Engine 5 (C++) Standards](#unreal-engine-5-c-standards)
   - [Python Standards (PEP 8)](#python-standards-pep-8)
   - [Firmware & Hardware Interfacing Standards](#firmware--hardware-interfacing-standards)
3. [Pull Request (PR) Process](#3-pull-request-pr-process)
   - [Branching Strategy](#branching-strategy)
   - [Commit Convention](#commit-convention)
   - [PR Submission Checklist](#pr-submission-checklist)
   - [Peer Review & Acceptance](#peer-review--acceptance)
4. [Bug & Issue Reporting Guidelines](#4-bug--issue-reporting-guidelines)
   - [Submitting a Report](#submitting-a-report)
   - [Issue Classification](#issue-classification)
5. [Artifact & Simulation Verification Guidelines](#5-artifact--simulation-verification-guidelines)
   - [Hardware-in-the-Loop (HIL) Validation](#hardware-in-the-loop-hil-validation)
   - [Software Serial Emulator Validation](#software-serial-emulator-validation)
   - [Logic-Gated Insertion State Verification](#logic-gated-insertion-state-verification)
   - [OpenXR & XR Tracking Verification](#openxr--xr-tracking-verification)

---

## 1. Academic Research Protocols & Ethics

### Non-Clinical Research Disclaimer
The Haptic Needle Twin is an **academic research and prototyping framework**, not a certified medical device. It is intended solely for scientific investigation, technical demonstration, and training method development. Under no circumstances should software or algorithms from this repository be deployed in clinical procedures or clinical diagnostic workflows.

### Scientific Reproducibility & Open Science
All research contributions (e.g., sensor transfer functions, deformation models, needle-tissue interaction logic) must prioritize reproducibility:
- **Parameter Transparency:** Avoid hardcoding uncalibrated magic numbers. Expose mechanical, electrical, and geometrical parameters via configuration assets, DataTables, or explicit `UPROPERTY(EditAnywhere, Category="...")` specifiers.
- **Experimental Provenance:** When introducing experimental datasets, sensor calibration curves, or mathematical formulations, document their derivation, sensor specifications (e.g., piezo type, ADC resolution, voltage dividers), and data acquisition conditions.
- **Deterministic Evaluation:** When introducing logic-gating rules or validation constraints, ensure test cases or emulator configurations are provided so other researchers can recreate the experimental conditions.

### Authorship & Attribution
Substantial academic contributions (such as developing novel soft-sensor integration architectures, publishing validated needle-tissue biomechanical models, or conducting empirical user studies using this twin) warrant scholarly attribution:
- Contributors who contribute significant research modules or validation studies are eligible for inclusion in academic publications originating from this repository.
- Ensure all external algorithms, papers, or third-party datasets referenced in your code include formal academic citations in comments and in [`CITATION.cff`](CITATION.cff).

### Contribution Tracks
Contributions typically fall into one of two tracks:
1. **Scientific / Theoretical Track:**
   - Novel sensor-to-logic mappings and constraint-satisfaction algorithms.
   - Haptic feedback profiles, force-displacement models, and soft-tissue deformation logic.
   - User training telemetry, procedural error taxonomies, and analytics pipelines.
2. **Systems / Engineering Track:**
   - Unreal Engine 5 rendering, physics pipeline, and OpenXR hand/eye-tracking optimizations.
   - High-throughput, low-latency asynchronous serial communication bridges.
   - Cross-platform build stability (Windows Win64, Linux, OpenXR runtime targets).
   - Tooling, emulators, and continuous integration workflows.

---

## 2. Code Style & Development Standards

### Unreal Engine 5 (C++) Standards
Our C++ codebase adheres strictly to the official [Epic Games Unreal Engine Coding Standard](https://dev.epicgames.com/documentation/en-us/unreal-engine/epic-cplusplus-coding-standard-for-unreal-engine) and the project's [`.editorconfig`](.editorconfig).

#### 1. Naming Conventions & Type Prefixes
Every type and variable name must follow Unreal Engine's standard prefix rules:
- **`A`**: Classes derived from `AActor` (e.g., `APiezoSensorReceiver`, `ACannulaActor`).
- **`U`**: Classes derived from `UObject` or `UActorComponent` (e.g., `USensorLogicComponent`).
- **`F`**: Structs and general non-UObject types (e.g., `FSensorReading`, `FInsertionConstraintGate`).
- **`T`**: Templates (e.g., `TArray<T>`, `TMap<K, V>`).
- **`E`**: Enumerations (e.g., `ESensorInsertionState`).
- **`I`**: Abstract interface classes (e.g., `IHapticFeedbackDevice`).
- **`S`**: Slate widgets (e.g., `SSensorTelemetryWidget`).
- **`b`**: Boolean variables (e.g., `bIsInsertionPermitted`, `bSensorArrayActive`).

Names must use **PascalCase** for classes, structs, methods, properties, and enumerations. Do not use snake_case or camelCase in C++ code.

#### 2. Memory Management & Object Lifetime
- Leverage Unreal's reflection system with `UPROPERTY()` and `UFUNCTION()` macros where garbage collection, serialization, or Blueprint exposure is required.
- For non-UObject memory management, use Unreal smart pointers:
  - `TSharedPtr` / `TSharedRef` for shared ownership outside UObject graphs.
  - `TWeakObjectPtr<T>` to safely reference UObjects without preventing garbage collection.
  - `TUniquePtr<T>` for exclusive ownership.
- Never retain dangling raw C++ pointers to `UObject` instances across frames.

#### 3. Header Organization
- Place `#pragma once` at the very top of all headers.
- Include `CoreMinimal.h` before other engine headers.
- Always place the generated header as the **last** include in any header declaring UObjects, UStructs, or UEnums:
  ```cpp
  #pragma once

  #include "CoreMinimal.h"
  #include "GameFramework/Actor.h"
  #include "PiezoSensorReceiver.generated.h"
  ```

#### 4. Concurrency & Serial Communication
- Serial port reads, socket polling, and sensor hardware I/O must run on dedicated background threads (e.g., using `FRunnable` / `FRunnableThread` or `FNonAbandonableTask`).
- Thread-safe queues (`TCircularQueue`, `TQueue<T, EQueueMode::Mpsc>`) must be used to marshal sensor readings from the hardware thread into the UE5 game thread.
- **Never block the Game Thread** with synchronous serial reads or hardware timeouts.

---

### Python Standards (PEP 8)
Python utilities (e.g., [`Arduino Test Pizeo.py`](Arduino%20Test%20Pizeo.py), synthetic sensor emulators, data visualization scripts, and telemetry parsers) must comply with **PEP 8**:

1. **Formatting:**
   - 4 spaces per indentation level; no tabs.
   - Maximum line length of 88–100 characters.
   - Clean spacing around operators and after commas.
2. **Naming:**
   - `snake_case` for module names, function names, and variable names.
   - `PascalCase` for class names (e.g., `PiezoSerialEmulator`).
   - `UPPER_SNAKE_CASE` for global constants (e.g., `DEFAULT_BAUD_RATE = 115200`).
3. **Typing & Documentation:**
   - Use Python 3.10+ type annotations for function signatures.
   - Provide docstrings formatted in Google or Sphinx/NumPy style explaining input parameters, return values, and raised exceptions.
4. **Thread & Resource Safety:**
   - GUI loops (Tkinter, PyQt) must remain responsive; long-running serial I/O tasks must run in daemon worker threads.
   - Ensure serial connections are wrapped in `try...finally` blocks or explicit `shutdown()` methods to release OS COM port locks on process exit.

---

### Firmware & Hardware Interfacing Standards
For Arduino, ESP32, or custom microcontroller firmware interfacing with the digital twin:
- **Default Baud Rate:** Standardize on **115200 baud** (8 data bits, no parity, 1 stop bit) unless an application-specific high-bandwidth requirement is formally documented.
- **Framing & Protocol:**
  - Standard sensor messages should be newline-delimited ASCII (`<sensor_index>\n` or `<sensor_id>,<timestamp_ms>,<voltage_mv>\n`) to allow seamless inspection via standard serial monitors.
  - For multi-channel sensor arrays (matrices > 16 elements), document the packet framing, byte packing, and checksum mechanism (CRC-8/CRC-16).
- **Debouncing & Calibration:**
  - Implement non-blocking digital debouncing or thresholding on the microcontroller to avoid flooding the serial buffer.
  - Document sensor pin assignments, pull-up/pull-down resistor configurations, and ADC sampling intervals in markdown alongside the firmware source.

---

## 3. Pull Request (PR) Process

### Branching Strategy
We maintain a Git branch flow tailored for academic stability:
- `main`: Production-ready, stable, and cited releases. Directly corresponds to released tags and Zenodo snapshots.
- `develop`: Primary integration branch for upcoming releases.
- Feature/Research branches:
  - `feature/<feature-name>`: Engineering improvements, UI enhancements, or UE5 engine upgrades.
  - `research/<hypothesis-or-paper>`: Experimental sensor models, soft electronics data channels, or procedural gating rules.
  - `fix/<issue-number>-<description>`: Bug fixes and performance patches.

### Commit Convention
Commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) format:
```text
<type>(<scope>): <short summary>

[optional body explaining motivation, experimental background, and design choices]

[optional footer referencing issues or academic tickets]
```
- Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.
- Example:
  ```text
  feat(serial): implement non-blocking circular buffer for multi-channel piezo input

  Replaces synchronous byte polling with an FRunnable worker thread marshaling
  tactile events through a thread-safe TQueue. Prevents game-thread hitches
  during high-frequency sensor bursts.

  Resolves: #14
  ```

### PR Submission Checklist
Before opening a Pull Request, confirm that:
- [ ] Code compiles cleanly under Unreal Engine 5.6+ with zero warnings (`Win64 Development Editor` target).
- [ ] Unreal C++ naming conventions and `.editorconfig` rules are verified.
- [ ] Python scripts adhere to PEP 8 and run without runtime regressions (`flake8` / `black` recommended).
- [ ] Hardware or emulator verification steps have been executed (see [Section 5](#5-artifact--simulation-verification-guidelines)).
- [ ] Documentation (in [`Readme.md`](Readme.md) or dedicated architecture notes) has been updated to reflect any new parameters or logic gates.
- [ ] If this work affects citations or authorship, updates have been proposed in [`CITATION.cff`](CITATION.cff).

### Peer Review & Acceptance
- Every PR requires review by at least one maintainer or scientific collaborator.
- The reviewer will test the proposed changes against both software emulation and, when applicable, physical hardware.
- All comments must be addressed, and discussions resolved, before merging. Squash-and-merge or rebase-and-merge is used to preserve a clean Git history.

---

## 4. Bug & Issue Reporting Guidelines

### Submitting a Report
If you encounter a defect, simulation artifact, or hardware communication issue, please submit an issue on GitHub with:
1. **Title:** Concise summary prefixed by module (e.g., `[Serial]`, `[LogicGate]`, `[OpenXR]`, `[Physics]`).
2. **Environment Information:**
   - Unreal Engine Version (e.g., 5.6.0)
   - Host OS & Architecture (e.g., Windows 11 x64)
   - Visual Studio / MSVC toolchain version
   - Hardware Setup (Microcontroller model, sensor type, COM port, baud rate)
   - VR Headset & OpenXR runtime (if XR features are tested)
3. **Steps to Reproduce:** Exact sequence of steps, including serial inputs or emulator clicks, to produce the error.
4. **Observed vs. Expected Behavior:** Explanation of what occurred versus what the medical/physical logic should allow.
5. **Logs & Diagnostics:**
   - Attach relevant log snippets from `Saved/Logs/RMVR.log`.
   - Serial monitor captures or terminal outputs from Python scripts.
   - Stack traces or crash dumps (if applicable).

### Issue Classification
- **Critical (Bug):** Unreal Engine crash, serial connection deadlocks, memory leaks, or build breakages.
- **Simulation Inaccuracy (Scientific):** Discrepancies where invalid insertion motions are permitted, sensor hysteresis is improperly handled, or insertion mechanics violate anatomical constraints.
- **Hardware Compatibility (HMI):** Incompatibilities with specific Arduino boards, FTDI drivers, or serial latency issues.
- **Feature Request:** Proposals for new sensor modalities, OpenXR interactions, or tissue deformation physics.

---

## 5. Artifact & Simulation Verification Guidelines

Because this project bridges physical sensors, embedded serial communication, and virtual reality graphics, contributors must verify their artifacts across three testing tiers:

```
┌───────────────────────────────────────────────────────────┐
│              Hardware-in-the-Loop (HIL)                   │
│   [Physical Sensors] ──► [Arduino] ──► [COM Port]         │
└─────────────────────────────┬─────────────────────────────┘
                              │
               OR             ▼
┌───────────────────────────────────────────────────────────┐
│             Software Serial Emulation                     │
│       [Arduino Test Pizeo.py GUI / Synthetic Stream]       │
└─────────────────────────────┬─────────────────────────────┘
                              │  (115200 Baud, Serial)
                              ▼
┌───────────────────────────────────────────────────────────┐
│                  Unreal Engine 5 Core                     │
│  [PiezoSensorReceiver] ──► [Logic Gating State Machine]   │
│             │                               │             │
│             ▼                               ▼             │
│  [Cannula Physics / Visuals]      [OpenXR HMD & Tracking] │
└───────────────────────────────────────────────────────────┘
```

### Hardware-in-the-Loop (HIL) Validation
When testing with physical hardware (Arduino Uno/Nano, piezo sensors, capacitive foils):
1. Connect the microcontroller via USB and verify the device appears in Windows Device Manager (e.g., `COM3`, `COM4`).
2. Flash the target firmware with 115200 baud serial output.
3. Open Unreal Editor, launch the test map in PIE (Play-In-Editor), and establish the serial connection.
4. Tap each sensor in the array and observe real-time telemetry logs. Confirm that latency between physical contact and UE5 event triggering is within acceptable limits (<20 ms).

### Software Serial Emulator Validation
When physical hardware is unavailable, contributors must validate behavior using the Python serial emulator:
1. Setup a virtual COM port pair (e.g., using `com0com`, `socat`, or equivalent virtual null-modem software, e.g., bridging `COM10` ↔ `COM11`).
2. Run the emulator:
   ```bash
   python "Arduino Test Pizeo.py"
   ```
3. Connect the Python GUI to one virtual COM port and point UE5's receiver to the paired port.
4. Execute single-hit tests (`SEND HIT` with specific sensor indices) and randomized bursts (`Random Hit`) to confirm that the UE5 receiver handles high message frequencies without dropping packets or freezing the viewport.

### Logic-Gated Insertion State Verification
The core innovation of this digital twin is **logic-gated possibility**. Validate that the insertion state machine behaves deterministically:
- **Negative Testing (Blocked Insertion):** Attempt to push or manipulate the cannula in the virtual environment without triggering the required touch sensor sequence. The system must hard-block insertion (e.g., zero translation along insertion axis or visual failure indicator).
- **Positive Testing (Permitted Insertion):** Transmit the valid sensor index sequence (mimicking correct clinical grip and anatomical alignment). Confirm the logic gate flips to permitted state and cannula advancement proceeds smoothly.
- **Edge Case Testing (Invalid Sequence / Noise):** Trigger sensor indices out of order or rapid contradictory inputs. Confirm the system gracefully drops into an error/locked state rather than entering an indeterminate condition.

### OpenXR & XR Tracking Verification
When modifying OpenXR or VR interaction modules:
- Verify that hand tracking (`OpenXRHandTracking`) and eye tracking (`OpenXREyeTracker`) components initialize without crashing on non-XR desktop launch.
- Check that target framerates (90 FPS standard for VR HMDs) are sustained and that sensor streaming does not introduce frame drops or head tracking jitter.
- Verify compatibility across target desktop and XR deployment profiles defined in [`RMVR.uproject`](RMVR.uproject).

---

## Code of Conduct
We expect all participants, researchers, and contributors to foster a welcoming, respectful, and scientifically rigorous community. Treat peers with courtesy, welcome diverse perspectives, and uphold the highest standards of scientific honesty and academic ethics.

For questions, collaborations, or research inquiries, please reach out via GitHub Issues or contact the project maintainers.
