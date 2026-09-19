# Demonstration Walkthrough: Haptic Needle Twin (UE5)

[![Artifact Type](https://img.shields.io/badge/Artifact-1080p%20Demonstration%20Recording-blue.svg)](#1-video-artifact-metadata)
[![Engine](https://img.shields.io/badge/Engine-Unreal%20Engine%205.6-black.svg?logo=unrealengine)](https://www.unrealengine.com/)
[![Video Status](https://img.shields.io/badge/Status-Verified%20%26%20Reproducible-success.svg)](#4-local-inspection--playback-instructions)
[![Protocol](https://img.shields.io/badge/Serial-115200%20Baud-orange.svg)](../Source/RMVR/SensorScript/APizeoSensorInput.cpp)

This document provides a comprehensive scene-by-scene walkthrough and technical analysis of the official demonstration video bundled with the repository:
[`Documentation/Recording 2026-03-17 123219.mp4`](Recording%202026-03-17%20123219.mp4).

The video illustrates the end-to-end operation of the **Haptic Needle Twin**: from serial emulator handshaking to real-time OpenXR spatial docking, piezoelectric tactile injection, dynamic hand HUD point highlighting, tactile error lockout (prohibiting insertion), and signature-matched cannula penetration.

---

## 1. Video Artifact Metadata

| Attribute | Value / Specification |
| :--- | :--- |
| **Media File** | [`Documentation/Recording 2026-03-17 123219.mp4`](Recording%202026-03-17%20123219.mp4) |
| **File Size** | $58,542,349\text{ bytes}$ ($55.83\text{ MB}$) |
| **Duration** | $01:19.55$ ($79.55\text{ seconds}$ / $2,386\text{ frames}$) |
| **Video Stream** | H.264 / AVC (Main Profile, Level 4.0), Progressive |
| **Dimensions** | $1598 \times 844\text{ pixels}$ (Aspect Ratio: 799:422 $\approx 1.89:1$) |
| **Frame Rate** | $30.00\text{ fps}$ (Constant Frame Rate) |
| **Video Bitrate** | $5,693\text{ kbps}$ |
| **Audio Stream** | AAC-LC, Stereo, $48,000\text{ Hz}$, $192\text{ kbps}$ |
| **Creation Date** | March 17, 2026 |
| **SHA-256 Checksum** | `ABFC9B6CAA0D8C4663E0A8D7A3A0507DF42ABEADD43D7FEA095943CD414A6A45` |

---

## 2. Chronological Scene Timeline Breakdown

The 79-second recording demonstrates the complete operational sequence across six distinct phases:

```
[00:00 - 00:10]  Phase 1: Unreal Editor Environment & Serial Emulator Setup
[00:10 - 00:26]  Phase 2: Standalone Simulation Launch & Patient Inspection
[00:26 - 00:40]  Phase 3: Cannula Pickup & Navigation to Procedure Checkpoint
[00:40 - 00:55]  Phase 4: Checkpoint Docking & Hand HUD Initialization
[00:55 - 01:10]  Phase 5: Tactile Injection, Dynamic Highlighting & Kinematic Lockout (Red "X")
[01:10 - 01:19]  Phase 6: Signature Match (Green "✓"), Cannula Penetration & Patient Recoil
```

```mermaid
timeline
    title Demonstration Recording Execution Timeline
    00:00 - 00:10 : Phase 1 : Outliner inspection : Serial port configured : Emulator connects COM2 @ 115200
    00:10 - 00:26 : Phase 2 : Standalone PIE launches : Ambulance and stretcher : Patient in supine pose
    00:26 - 00:40 : Phase 3 : Trolley navigation : Syringe pickup : Green beacon guide active
    00:40 - 00:55 : Phase 4 : Enters insertion ring : Hand HUD appears : Translucent target sphere aligns
    00:55 - 01:10 : Phase 5 : Emulator hits 4, 5, 7, 3 : Sensor points glow RED : Red 'X' kinematic lockout
    01:10 - 01:19 : Phase 6 : Sensor index 1 sent : Green '✓' banner : Cannula inserts : Arm recoil animation
```

---

### Phase 1: Unreal Editor Setup & Serial Emulator Handshake (00:00 – 00:10)

* **Editor Context:** The recording begins inside the Unreal Engine 5.6 Editor window viewing the map `OpenMap`.
* **Outliner Inspection:** The World Outliner highlights key simulation actors:
  * [`BP_PizeoReciever`](../Source/RMVR/SensorScript/APizeoSensorInput.h) / Serial Input Actor.
  * `CheckPointCanulaPick`: Proximity trigger defining the instrument pickup station on the hospital trolley.
  * `CheckPointCanulaInsert`: Volumetric cylindrical checkpoint defining the patient cannulation station.
  * `laboratory_hospital_troly`: The mobile surgical instrument cart.
* **Content Browser:** Displays core project blueprints including `BP_Patient`, `BP_ThirdPersonCharacter`, `BP_ThirdPersonGameMode`, and `CanulaInjection`.
* **Details Panel:** The Details panel confirms serial configuration: `Port Name = COM3`, `Baud Rate = 115200`.
* **Serial Emulator Launch:** Overlaying the editor is the Tkinter-based Python serial test utility ([`Arduino Test Pizeo.py`](../Arduino%20Test%20Pizeo.py)):
  * Target Port: `COM2` (connected via virtual COM pair to the engine's receiver port).
  * Baud: `115200`.
  * Status: Displays connection confirmation message:
    ```text
    [12:30:42] Connected to COM2 @ 115200
    ```

---

### Phase 2: Standalone Simulation Launch & Patient Inspection (00:10 – 00:26)

* **Execution Mode:** Play In Editor (PIE) launches in a dedicated window: `RMVR Preview [NetMode: Standalone 0] (64-bit/PC D3D SM5)`.
* **Scene Staging:**
  * An outdoor emergency transit environment featuring a yellow ambulance with rear doors positioned near a roadway.
  * A mobile patient transport gurney / stretcher positioned adjacent to the ambulance.
  * The patient avatar (`BP_Patient`) is lying supine on the gurney, positioned using the clinical resting pose asset [`Female_Laying_Pose.uasset`](../Content/Animations/Female_Laying_Pose.uasset).
* **Player Character:** The surgeon character model ([`ARMVRCharacterBase`](../Source/RMVR/Character/RMVRCharacterBase.h#L10-L33) / `BP_ThirdPersonCharacter`) is dressed in sterile surgical scrubs, headcap, and medical face mask, standing adjacent to the vehicle.

---

### Phase 3: Cannula Pickup & Approach to Patient (00:26 – 00:40)

* **Navigation:** The operator controls the surgeon avatar, moving toward the stainless-steel instrument cart (`laboratory_hospital_troly`).
* **Instrument Acquisition:** The surgeon retrieves the peripheral IV cannula / syringe assembly (`CanulaInjection`). The red-hubbed cannula model attaches to the character's hand rig.
* **Visual Guidance System:** A vertical volumetric light beacon (glowing green cylindrical beam) projects from the floor to guide the operator to the bedside procedure station (`CheckPointCanulaInsert`).

---

### Phase 4: Station Docking & Hand HUD Initialization (00:40 – 00:55)

* **Spatial Docking:** The surgeon avatar steps inside the glowing circular floor boundary of `CheckPointCanulaInsert`. Upon entry, the beam shifts from navigational green to an active purple volumetric column, confirming station lock.
* **UI Banner Activation:** The top HUD activates with tracking banners:
  ```text
  C H E C K I N G   T H E   S I G N A L . . .
  W A I T I N G   F O R   S I G N A L . . .
  ```
* **Dynamic Hand Graphic HUD:** A stylized 2D right-hand silhouette appears on the bottom-right of the viewport. It displays eight discrete black circular nodes corresponding to the tactile sensor mapping $S(t) \in \{1 \dots 8\}$.
* **Target Insertion Indicator:** A translucent glowing white sphere appears directly over the patient's right forearm cannulation site, establishing the required spatial interaction zone.

---

### Phase 5: Tactile Injection, Dynamic Highlighting & Kinematic Lockout (00:55 – 01:10)

This is the pivotal demonstration of the **logic-gated constraint system**. The user shifts focus to the `Piezo Sensor Emulator` window and injects non-matching tactile inputs:

```
Trainee Contact -> Microcontroller/Emulator -> UART '4' -> Win32 ReadFile -> GameThread Dispatch
```

1. **First Tactile Injection (Sensor 4 @ 12:31:31):**
   * Emulator log: `[12:31:31] Sent -> 4`.
   * Viewport Debug Stream:
     ```text
     4
     4
     PARSED Pizeo hit: 4
     Pizeo hit: 4
     ```
   * **Hand HUD Response:** The central palm sensor point on the hand silhouette immediately illuminates in **vibrant RED**, driven by [`ARMVRCharacterBase::RHighlightHandPoint`](../Source/RMVR/Character/RMVRCharacterBase.h#L30-L32).
   * **Kinematic Lockout Triggered:** A large, prominent **Red "X" badge** appears hovering over the patient's arm. Because the operator contacted the palm compaction zone instead of establishing vein anchorage, the logic gate sets $P(t) = 0$. Cannula penetration is blocked.

2. **Second Tactile Injection (Sensor 5 @ 12:31:34):**
   * Emulator log: `[12:31:34] Sent -> 5`.
   * Debug text confirms receipt: `5`, `Pizeo hit: 5`.
   * Hand HUD updates: The hypothenar sensor point highlights in RED.
   * Red "X" remains active; penetration continues to be prohibited.

3. **Subsequent Injections (Sensor 7 @ 12:31:38 & Sensor 3 @ 12:31:41):**
   * Emulator transmits `7` and `3`.
   * Debug output confirms: `PARSED Pizeo hit: 3`, `Pizeo hit: 3`.
   * Hand HUD dynamically shifts highlighting to dot 3 in RED.
   * Lockout state persists: insertion remains physically clamped.

---

### Phase 6: Correct Signature Match, Penetration & Discomfort Reaction (01:10 – 01:19)

1. **Target Signature Injection (Sensor 1 @ 12:31:46):**
   * After injecting sensor 8 (`12:31:44`), the user injects sensor 1 (`12:31:46`), corresponding to correct distal vein stabilization and traction.
   * Serial parser outputs:
     ```text
     Signal Recieved
     1
     PARSED Pizeo hit: 1
     Pizeo hit: 1
     ```
2. **Logic Gate Unlocking:**
   * The multi-condition validator verifies that the correct tactile signature condition is met.
   * Top banner instantly transitions to:
     ```text
     M A T C H I N G   S I G N A T U R E   F O U N D !
     ```
   * The Red "X" lockout barrier instantly vanishes.
   * A large **Green Circle with a White Checkmark ("✓")** appears in mid-air over the puncture site.
3. **Cannula Penetration Executed:**
   * With permission $P(t) = 1$, the kinematic rail unlocks. The cannula advances into the patient's vein lumen.
   * The red cannula hub is clearly rendered seated firmly on the patient's forearm.
4. **Bio-Digital Feedback (Patient Recoil):**
   * The patient animation blueprint ([`ABPPatient.uasset`](../Content/Animations/ABPPatient.uasset)) triggers the reaction state ([`RaiseHand1.uasset`](../Content/Animations/RaiseHand1.uasset)).
   * The patient elevates her right hand in response to the needle puncture, completing the realistic physiological and tactile feedback loop.

---

## 3. Visual & Technical Indicators Summary

| Visual Indicator | Screen Location | State / Meaning | Underlying Implementation |
| :--- | :--- | :--- | :--- |
| **`Waiting For Signal`** | Top-Left Viewport (Cyan) | Serial receiver is active; awaiting incoming tactile bytes | `APizeoSensorInput::SerialWorker` loop |
| **`PARSED Pizeo hit: N`** | Top-Left Viewport (Green) | Raw byte parsed by `FChar::IsDigit` and dispatched to GameThread | [`AsyncTask(ENamedThreads::GameThread)`](../Source/RMVR/SensorScript/APizeoSensorInput.cpp#L154-L170) |
| **`CHECKING THE SIGNAL...`** | Top Screen Banner (White) | Operator is inside procedure zone; evaluating preconditions | Checkpoint trigger overlap logic |
| **Red Hand Point Dot** | Bottom-Right HUD Graphic | Physical touch detected on sensor node index $N$ | [`ARMVRCharacterBase::RHighlightHandPoint`](../Source/RMVR/Character/RMVRCharacterBase.h#L30-L32) |
| **Red "X" Barrier Icon** | 3D World Space over Stretcher | **Kinematic Lockout ($P(t) = 0$):** Incorrect technique; insertion blocked | Logic-Gated Insertion State Machine |
| **`MATCHING SIGNATURE FOUND!`** | Top Screen Banner (White) | Target tactile sequence validated ($P(t) = 1$) | Finite State Machine permission gate |
| **Green "✓" Icon** | 3D World Space over Stretcher | **Insertion Permitted:** Rail unlocked; penetration allowed | State Machine release signal |
| **Cannula Seated on Arm** | Patient Forearm Mesh | Catheter successfully positioned in vascular lumen | Constraint rail depth translation |
| **Patient Arm Elevation** | Patient Skeletal Mesh | Physiological discomfort reaction | [`ABPPatient.uasset`](../Content/Animations/ABPPatient.uasset) / [`RaiseHand.uasset`](../Content/Animations/RaiseHand.uasset) |

---

## 4. Local Inspection & Playback Instructions

To inspect and verify the demonstration video locally on your workstation, follow any of the methods outlined below.

### Method A: Playback via Native Video Players (Windows GUI)

Double-click the video file directly, or launch it from PowerShell using your preferred desktop media player:

```powershell
# Using default registered Windows media player (Movies & TV / Windows Media Player)
Start-Process "Documentation\Recording 2026-03-17 123219.mp4"

# Using VLC Media Player (if installed)
& "C:\Program Files\VideoLAN\VLC\vlc.exe" "Documentation\Recording 2026-03-17 123219.mp4"
```

### Method B: High-Precision Playback via `ffplay` (Command-Line)

If you have FFmpeg installed, use `ffplay` to inspect the video with exact frame timing and on-screen audio/video synchronization:

```powershell
# Standard playback
ffplay -autoexit "Documentation\Recording 2026-03-17 123219.mp4"

# Playback starting at the tactile injection phase (00:50)
ffplay -ss 00:00:50 -autoexit "Documentation\Recording 2026-03-17 123219.mp4"
```

### Method C: Keyframe Extraction for Visual Verification

To extract high-resolution PNG keyframes for documentation, inspection, or print evaluation:

```powershell
# Create an output directory for extracted keyframes
New-Item -ItemType Directory -Force -Path "Documentation\Extracted_Frames"

# Extract 1 frame every 5 seconds across the full duration
ffmpeg -i "Documentation\Recording 2026-03-17 123219.mp4" -vf fps=1/5 "Documentation\Extracted_Frames\frame_%02d.png"

# Extract exact keyframe of error lockout (Red "X") at 01:00
ffmpeg -ss 00:01:00 -i "Documentation\Recording 2026-03-17 123219.mp4" -frames:v 1 -q:v 2 "Documentation\Extracted_Frames\lockout_red_x.png"

# Extract exact keyframe of signature unlock (Green "✓") at 01:14
ffmpeg -ss 00:01:14 -i "Documentation\Recording 2026-03-17 123219.mp4" -frames:v 1 -q:v 2 "Documentation\Extracted_Frames\signature_matched_green_check.png"
```

### Method D: Cryptographic Integrity Verification (SHA-256)

To confirm that your local copy of the demonstration recording is intact and matches the published artifact:

```powershell
Get-FileHash -Algorithm SHA256 "Documentation\Recording 2026-03-17 123219.mp4"
```

**Expected Hash Output:**
```text
Algorithm       Hash                                                                Path
---------       ----                                                                ----
SHA256          ABFC9B6CAA0D8C4663E0A8D7A3A0507DF42ABEADD43D7FEA095943CD414A6A45    ...Recording 2026-03-17 123219.mp4
```

---

## 5. Summary

The demonstration video [`Recording 2026-03-17 123219.mp4`](Recording%202026-03-17%20123219.mp4) provides direct empirical evidence of the system's core scientific contribution: **procedural tactile constraints acting as hard simulation gates**. Rather than allowing visual penetration through collision alone, the digital twin enforces physical palpation and anchorage techniques, proving that wrong touch produces physical impossibility within the simulation.
