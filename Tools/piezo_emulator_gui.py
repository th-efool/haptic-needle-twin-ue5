"""
Haptic Needle Twin - Piezo Tactile Matrix Emulator (GUI)
=========================================================
A professional Tkinter-based serial emulator for the Unreal Engine 5 Haptic Needle Twin.
Emulates the 3x3 piezo tactile sensor array with real-time serial transmission,
interactive matrix pad, clinical cannulation sequence simulation, and traffic logging.

Author: L2_Python_Tooling_Developer
Target Hardware: Arduino / ESP32 / Virtual COM / UE5 APizeoSensorInput
"""

import sys
import time
import queue
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

# Gracefully import pyserial
try:
    import serial
    import serial.tools.list_ports
    PYSERIAL_AVAILABLE = True
except ImportError:
    PYSERIAL_AVAILABLE = False


# Clinical cannulation phases for realistic tissue layer simulation
CLINICAL_SEQUENCE_PHASES = [
    (0, "Phase 1/4: Epidermal Contact", 0.60),
    (1, "Phase 2/4: Dermal Resistance & Entry", 0.75),
    (2, "Phase 3/4: Subcutaneous Tissue Advance", 0.85),
    (3, "Phase 4/4: Vessel Wall Puncture (Flashback)", 0.50),
]

BAUD_RATES = [
    "9600",
    "19200",
    "38400",
    "57600",
    "115200",
    "230400",
    "460800",
    "921600",
]


class PiezoEmulatorGUI:
    """Tkinter-based GUI emulator for 3x3 Piezo Tactile Sensor Matrix."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Haptic Needle Twin — Piezo Sensor Emulator")
        self.root.geometry("860x720")
        self.root.minsize(780, 640)

        # Communication and Threading State
        self.serial_conn: Optional[serial.Serial] = None
        self.tx_queue: queue.Queue = queue.Queue()
        self.gui_queue: queue.Queue = queue.Queue()
        self.running: bool = True
        self.is_connected: bool = False

        # Simulation thread handles
        self.sequence_thread: Optional[threading.Thread] = None
        self.sequence_stop_event = threading.Event()
        self.random_thread: Optional[threading.Thread] = None
        self.random_stop_event = threading.Event()

        # UI state variables
        self.port_var = tk.StringVar()
        self.baud_var = tk.StringVar(value="115200")
        self.status_var = tk.StringVar(value="Disconnected (Virtual Mode)")
        self.random_rate_var = tk.DoubleVar(value=0.5)
        self.manual_sensor_var = tk.StringVar(value="0")
        self.auto_scroll_var = tk.BooleanVar(value=True)

        # Button widget mapping for visual feedback: sensor_id -> tk.Button
        self.sensor_buttons = {}

        # Set up modern TTK styling
        self._setup_styles()

        # Build UI layout
        self._build_ui()

        # Bind keyboard shortcuts (Keys 0-8 and Numpad 0-8)
        self._bind_shortcuts()

        # Launch background serial worker thread
        self.worker_thread = threading.Thread(target=self._serial_worker, daemon=True, name="SerialWorker")
        self.worker_thread.start()

        # Start GUI event loop listener for thread safety
        self.root.after(40, self._process_gui_queue)

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Auto-scan ports on startup
        self.refresh_ports()

        # Initial log
        self._log_status("Piezo Sensor Emulator initialized.")
        if not PYSERIAL_AVAILABLE:
            self._log_warn("pyserial is not installed. Running in Virtual/Offline mode.")
            self._log_status("To enable physical COM ports, run: pip install -r requirements.txt")

    def _setup_styles(self):
        """Configure ttk theme and custom styles."""
        self.style = ttk.Style(self.root)
        available_themes = self.style.theme_names()
        if "clam" in available_themes:
            self.style.theme_use("clam")

        # Palette definition
        self.c_bg = "#f4f6f9"
        self.c_card = "#ffffff"
        self.c_primary = "#0d6efd"
        self.c_success = "#198754"
        self.c_danger = "#dc3545"
        self.c_warning = "#ffc107"
        self.c_text = "#212529"
        self.c_matrix_idle = "#e9ecef"
        self.c_matrix_active = "#38bdf8"
        self.c_matrix_active_txt = "#0f172a"

        self.root.configure(bg=self.c_bg)

        self.style.configure("TFrame", background=self.c_bg)
        self.style.configure("Card.TFrame", background=self.c_card, relief="ridge")
        self.style.configure("TLabelframe", background=self.c_bg)
        self.style.configure("TLabelframe.Label", background=self.c_bg, font=("Segoe UI", 9, "bold"), foreground="#495057")
        self.style.configure("TLabel", background=self.c_bg, font=("Segoe UI", 9), foreground=self.c_text)
        self.style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"), foreground="#1e293b")
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 8), foreground="#64748b")
        self.style.configure("Status.TLabel", font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        """Construct the main GUI widgets."""
        main_container = ttk.Frame(self.root, padding=12)
        main_container.pack(fill=tk.BOTH, expand=True)

        # ---------------------------------------------------------------------
        # 1. Header & Connection Bar
        # ---------------------------------------------------------------------
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_box = ttk.Frame(header_frame)
        title_box.pack(side=tk.LEFT)
        ttk.Label(title_box, text="⚡ Haptic Needle Twin — Tactile Matrix Emulator", style="Header.TLabel").pack(anchor=tk.W)
        ttk.Label(title_box, text="Simulates 3x3 Piezo Array for UE5 APizeoSensorInput | Keys [0-8]", style="SubHeader.TLabel").pack(anchor=tk.W)

        # Connection Control Box
        conn_box = ttk.LabelFrame(main_container, text="Serial Connection & Port Configuration", padding=10)
        conn_box.pack(fill=tk.X, pady=(0, 10))

        # Grid inside conn_box
        ttk.Label(conn_box, text="COM Port:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5), pady=2)
        self.port_menu = ttk.Combobox(conn_box, textvariable=self.port_var, width=16, state="readonly")
        self.port_menu.grid(row=0, column=1, sticky=tk.W, padx=(0, 6), pady=2)

        self.btn_refresh = ttk.Button(conn_box, text="↻ Refresh", command=self.refresh_ports, width=9)
        self.btn_refresh.grid(row=0, column=2, sticky=tk.W, padx=(0, 16), pady=2)

        ttk.Label(conn_box, text="Baud Rate:").grid(row=0, column=3, sticky=tk.W, padx=(0, 5), pady=2)
        self.baud_menu = ttk.Combobox(conn_box, textvariable=self.baud_var, values=BAUD_RATES, width=10, state="readonly")
        self.baud_menu.grid(row=0, column=4, sticky=tk.W, padx=(0, 16), pady=2)

        self.btn_connect = tk.Button(
            conn_box,
            text="Connect",
            command=self.toggle_connection,
            bg=self.c_primary,
            fg="white",
            activebackground="#0b5ed7",
            activeforeground="white",
            relief="raised",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=2,
            cursor="hand2"
        )
        self.btn_connect.grid(row=0, column=5, sticky=tk.W, padx=(0, 16), pady=2)

        # Connection status badge
        self.status_label = tk.Label(
            conn_box,
            textvariable=self.status_var,
            font=("Segoe UI", 9, "bold"),
            fg="#6c757d",
            bg=self.c_bg,
            padx=8,
            pady=2
        )
        self.status_label.grid(row=0, column=6, sticky=tk.W, pady=2)

        # ---------------------------------------------------------------------
        # 2. Middle Area: Tactile Matrix (Left) & Simulation Controls (Right)
        # ---------------------------------------------------------------------
        mid_container = ttk.Frame(main_container)
        mid_container.pack(fill=tk.BOTH, expand=False, pady=(0, 10))

        # LEFT: 3x3 Tactile Matrix Pad
        matrix_frame = ttk.LabelFrame(mid_container, text="3x3 Tactile Matrix Pad (Click or Press Keys 0-8)", padding=12)
        matrix_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        grid_container = tk.Frame(matrix_frame, bg=self.c_bg)
        grid_container.pack(expand=True)

        for row in range(3):
            for col in range(3):
                sensor_id = row * 3 + col
                btn = tk.Button(
                    grid_container,
                    text=f"Sensor {sensor_id}\n[Key {sensor_id}]",
                    font=("Segoe UI", 10, "bold"),
                    bg=self.c_matrix_idle,
                    fg="#1e293b",
                    activebackground=self.c_matrix_active,
                    activeforeground=self.c_matrix_active_txt,
                    relief="raised",
                    bd=3,
                    width=11,
                    height=3,
                    cursor="hand2",
                    command=lambda sid=sensor_id: self.trigger_sensor(sid)
                )
                btn.grid(row=row, column=col, padx=5, pady=5)
                self.sensor_buttons[sensor_id] = btn

        # RIGHT: Sequence & Automated Simulation Controls
        sim_frame = ttk.LabelFrame(mid_container, text="Sequence Simulation & Automation", padding=12)
        sim_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        # Section A: Clinical Cannulation Sequence
        clinical_box = tk.LabelFrame(sim_frame, text="Clinical Cannulation Simulation (0 → 1 → 2 → 3)", bg=self.c_bg, font=("Segoe UI", 9, "bold"), fg="#334155", padx=8, pady=8)
        clinical_box.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            clinical_box,
            text="Simulates physiological tissue layer puncture:\nContact (0) → Dermis (1) → SubQ (2) → Vessel Wall (3)",
            font=("Segoe UI", 8),
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 6))

        clin_btn_box = ttk.Frame(clinical_box)
        clin_btn_box.pack(fill=tk.X)

        self.btn_clinical = tk.Button(
            clin_btn_box,
            text="▶ Simulate Cannulation Sequence",
            command=self.start_clinical_sequence,
            bg="#0d6efd",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            padx=8,
            pady=4,
            cursor="hand2"
        )
        self.btn_clinical.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_stop_seq = tk.Button(
            clin_btn_box,
            text="⏹ Stop",
            command=self.stop_clinical_sequence,
            bg="#6c757d",
            fg="white",
            font=("Segoe UI", 9),
            relief="raised",
            state=tk.DISABLED,
            padx=8,
            pady=4
        )
        self.btn_stop_seq.pack(side=tk.LEFT)

        self.seq_status_lbl = ttk.Label(clinical_box, text="Sequence Idle", font=("Segoe UI", 8, "italic"), foreground="#64748b")
        self.seq_status_lbl.pack(anchor=tk.W, pady=(4, 0))

        # Section B: Random Hit Mode
        random_box = tk.LabelFrame(sim_frame, text="Random Hit Mode", bg=self.c_bg, font=("Segoe UI", 9, "bold"), fg="#334155", padx=8, pady=8)
        random_box.pack(fill=tk.X, pady=(0, 10))

        rate_box = ttk.Frame(random_box)
        rate_box.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(rate_box, text="Interval:").pack(side=tk.LEFT, padx=(0, 4))
        self.rate_scale = ttk.Scale(
            rate_box,
            from_=0.1,
            to=2.0,
            variable=self.random_rate_var,
            orient=tk.HORIZONTAL,
            command=self._update_rate_label
        )
        self.rate_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.rate_val_lbl = ttk.Label(rate_box, text="0.50 s", width=6)
        self.rate_val_lbl.pack(side=tk.LEFT, padx=(4, 0))

        self.btn_random = tk.Button(
            random_box,
            text="▶ Start Random Hits",
            command=self.toggle_random_hits,
            bg="#198754",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            padx=8,
            pady=4,
            cursor="hand2"
        )
        self.btn_random.pack(anchor=tk.W)

        # Section C: Manual Custom Sensor Input
        manual_box = ttk.Frame(sim_frame)
        manual_box.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(manual_box, text="Custom Sensor Index:").pack(side=tk.LEFT, padx=(0, 6))
        self.entry_manual = ttk.Entry(manual_box, textvariable=self.manual_sensor_var, width=6)
        self.entry_manual.pack(side=tk.LEFT, padx=(0, 6))
        self.btn_manual_send = ttk.Button(manual_box, text="Send Hit", command=self._send_manual_sensor)
        self.btn_manual_send.pack(side=tk.LEFT)

        # ---------------------------------------------------------------------
        # 3. Serial Traffic Log
        # ---------------------------------------------------------------------
        log_frame = ttk.LabelFrame(main_container, text="Serial Traffic & Event Log", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Log toolbar
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill=tk.X, pady=(0, 4))

        btn_clear = ttk.Button(log_toolbar, text="Clear Log", command=self.clear_log, width=10)
        btn_clear.pack(side=tk.LEFT, padx=(0, 6))

        btn_copy = ttk.Button(log_toolbar, text="Copy to Clipboard", command=self.copy_log, width=16)
        btn_copy.pack(side=tk.LEFT, padx=(0, 10))

        chk_scroll = ttk.Checkbutton(log_toolbar, text="Auto-scroll", variable=self.auto_scroll_var)
        chk_scroll.pack(side=tk.LEFT)

        self.tx_counter_lbl = ttk.Label(log_toolbar, text="Packets Sent: 0", font=("Segoe UI", 8), foreground="#64748b")
        self.tx_counter_lbl.pack(side=tk.RIGHT)
        self.total_tx_count = 0

        # Text area with scrollbar
        text_container = ttk.Frame(log_frame)
        text_container.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            text_container,
            wrap=tk.NONE,
            font=("Consolas", 9),
            bg="#1e293b",
            fg="#f8fafc",
            insertbackground="#ffffff",
            selectbackground="#334155",
            height=10
        )
        scrollbar_y = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar_x = ttk.Scrollbar(text_container, orient=tk.HORIZONTAL, command=self.log_text.xview)
        self.log_text.configure(xscrollcommand=scrollbar_x.set, yscrollcommand=scrollbar_y.set)

        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Text color tags for console formatting
        self.log_text.tag_configure("time", foreground="#94a3b8")
        self.log_text.tag_configure("tx", foreground="#38bdf8", font=("Consolas", 9, "bold"))
        self.log_text.tag_configure("status", foreground="#4ade80")
        self.log_text.tag_configure("warn", foreground="#facc15")
        self.log_text.tag_configure("error", foreground="#f87171", font=("Consolas", 9, "bold"))

    def _bind_shortcuts(self):
        """Bind keyboard keys 0-8 and keypad 0-8 to trigger corresponding sensors."""
        for i in range(9):
            # Standard keyboard number keys
            self.root.bind(str(i), lambda e, sid=i: self._on_key_press(sid))
            # Numpad keys
            self.root.bind(f"<KP_{i}>", lambda e, sid=i: self._on_key_press(sid))

    def _on_key_press(self, sensor_id: int):
        """Handle keyboard shortcut event."""
        # Check if the focused widget is an Entry; if so, do not intercept typing
        focused = self.root.focus_get()
        if isinstance(focused, (tk.Entry, ttk.Entry)):
            return
        self.trigger_sensor(sensor_id)

    def _update_rate_label(self, val=None):
        """Update rate label dynamically when slider is moved."""
        rate = self.random_rate_var.get()
        self.rate_val_lbl.config(text=f"{rate:.2f} s")

    # -------------------------------------------------------------------------
    # Port Scanning and Connection Management
    # -------------------------------------------------------------------------
    def refresh_ports(self):
        """Auto-scan available serial ports and populate combobox."""
        if not PYSERIAL_AVAILABLE:
            self.port_menu["values"] = ["<pyserial missing>"]
            self.port_var.set("<pyserial missing>")
            return

        try:
            ports = [p.device for p in serial.tools.list_ports.comports()]
            if ports:
                self.port_menu["values"] = ports
                if self.port_var.get() not in ports:
                    self.port_var.set(ports[0])
                self._log_status(f"Found {len(ports)} serial port(s): {', '.join(ports)}")
            else:
                self.port_menu["values"] = ["<No Ports Detected>"]
                self.port_var.set("<No Ports Detected>")
                self._log_warn("No hardware serial ports detected. Emulator can run in Virtual Mode.")
        except Exception as e:
            self._log_error(f"Error scanning ports: {e}")

    def toggle_connection(self):
        """Connect or disconnect serial port."""
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        """Open serial port connection."""
        if not PYSERIAL_AVAILABLE:
            messagebox.showwarning(
                "pyserial Required",
                "pyserial is not installed in the current Python environment.\n\n"
                "Please run: pip install -r requirements.txt\n\n"
                "You can still use the emulator in Virtual Mode without hardware."
            )
            return

        port = self.port_var.get()
        if not port or port.startswith("<"):
            messagebox.showerror("Invalid Port", "Please select a valid COM port from the dropdown.")
            return

        try:
            baud = int(self.baud_var.get())
        except ValueError:
            messagebox.showerror("Invalid Baud", "Please select a valid baud rate.")
            return

        try:
            self._log_status(f"Connecting to {port} @ {baud} baud...")
            self.serial_conn = serial.Serial(port=port, baudrate=baud, timeout=0.1, write_timeout=1.0)
            self.is_connected = True

            # Update UI
            self.btn_connect.config(text="Disconnect", bg=self.c_danger, activebackground="#bb2d3b")
            self.status_var.set(f"● Connected: {port} @ {baud}")
            self.status_label.config(fg="#198754")
            self.port_menu.config(state="disabled")
            self.baud_menu.config(state="disabled")
            self.btn_refresh.config(state="disabled")

            self._log_status(f"Serial port {port} opened successfully.")
        except Exception as e:
            self.is_connected = False
            self.serial_conn = None
            self._log_error(f"Failed to connect to {port}: {e}")
            messagebox.showerror("Connection Error", f"Could not open {port}:\n\n{e}")

    def disconnect(self):
        """Close active serial port."""
        # Stop any active sequences first
        self.stop_clinical_sequence()
        self.stop_random_hits()

        self.is_connected = False
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except Exception as e:
                self._log_warn(f"Error closing port: {e}")
            finally:
                self.serial_conn = None

        self.btn_connect.config(text="Connect", bg=self.c_primary, activebackground="#0b5ed7")
        self.status_var.set("Disconnected (Virtual Mode)")
        self.status_label.config(fg="#6c757d")
        self.port_menu.config(state="readonly")
        self.baud_menu.config(state="readonly")
        self.btn_refresh.config(state="normal")
        self._log_status("Disconnected from serial port.")

    # -------------------------------------------------------------------------
    # Sensor Triggering & Visual Feedback
    # -------------------------------------------------------------------------
    def trigger_sensor(self, sensor_id: int):
        """Trigger sensor hit, transmit serial packet, and flash visual button."""
        if not (0 <= sensor_id <= 8):
            self._log_warn(f"Sensor index {sensor_id} out of 3x3 matrix range (0-8).")

        # Visual tactile feedback: flash button
        self._flash_button(sensor_id)

        # Prepare packet: UE5 APizeoSensorInput parses digits followed by newline
        payload = f"{sensor_id}\n"
        self.tx_queue.put((sensor_id, payload))

    def _flash_button(self, sensor_id: int):
        """Temporarily highlight the tactile pad button for visual feedback."""
        btn = self.sensor_buttons.get(sensor_id)
        if not btn:
            return

        btn.config(bg=self.c_matrix_active, fg=self.c_matrix_active_txt, relief="sunken")
        # Reset button appearance after 160ms
        self.root.after(160, lambda: self._reset_button(sensor_id))

    def _reset_button(self, sensor_id: int):
        """Reset button styling back to normal idle state."""
        btn = self.sensor_buttons.get(sensor_id)
        if btn:
            btn.config(bg=self.c_matrix_idle, fg="#1e293b", relief="raised")

    def _send_manual_sensor(self):
        """Send sensor value entered manually into Entry."""
        val = self.manual_sensor_var.get().strip()
        if not val.isdigit():
            messagebox.showerror("Invalid Input", "Please enter an integer sensor index (e.g. 0 to 8).")
            return
        sensor_id = int(val)
        self.trigger_sensor(sensor_id)

    # -------------------------------------------------------------------------
    # Background Serial Worker (Thread-Safe Transmission)
    # -------------------------------------------------------------------------
    def _serial_worker(self):
        """Dedicated thread consuming from tx_queue and transmitting over serial."""
        while self.running:
            try:
                item = self.tx_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            sensor_id, payload = item
            raw_bytes = payload.encode("utf-8")
            hex_repr = " ".join(f"0x{b:02X}" for b in raw_bytes)

            transmitted = False
            if self.is_connected and self.serial_conn:
                try:
                    self.serial_conn.write(raw_bytes)
                    self.serial_conn.flush()
                    transmitted = True
                except Exception as e:
                    self.gui_queue.put(("error", f"Transmission error on {self.port_var.get()}: {e}"))
                    self.gui_queue.put(("disconnect_req", None))

            mode_tag = "[HARDWARE TX]" if transmitted else "[VIRTUAL TX]"
            log_msg = f"{mode_tag} Sensor {sensor_id} → Payload: {repr(payload)} (Hex: {hex_repr})"
            self.gui_queue.put(("tx", log_msg))
            self.gui_queue.put(("increment_tx", None))

    # -------------------------------------------------------------------------
    # Clinical Sequence Simulation
    # -------------------------------------------------------------------------
    def start_clinical_sequence(self):
        """Simulate realistic cannulation sequence: 0 -> 1 -> 2 -> 3 with physiological delays."""
        if self.sequence_thread and self.sequence_thread.is_alive():
            return

        self.sequence_stop_event.clear()
        self.btn_clinical.config(state=tk.DISABLED)
        self.btn_stop_seq.config(state=tk.NORMAL, bg=self.c_danger)

        self._log_status("Starting Clinical Cannulation Sequence (0 → 1 → 2 → 3)...")

        self.sequence_thread = threading.Thread(
            target=self._clinical_sequence_worker,
            daemon=True,
            name="ClinicalSequenceWorker"
        )
        self.sequence_thread.start()

    def stop_clinical_sequence(self):
        """Abort running clinical sequence."""
        self.sequence_stop_event.set()
        self.btn_clinical.config(state=tk.NORMAL)
        self.btn_stop_seq.config(state=tk.DISABLED, bg="#6c757d")
        self.seq_status_lbl.config(text="Sequence Idle")

    def _clinical_sequence_worker(self):
        """Background runner for sequential needle layer penetration."""
        try:
            for sensor_id, phase_name, delay_sec in CLINICAL_SEQUENCE_PHASES:
                if self.sequence_stop_event.is_set():
                    break

                self.gui_queue.put(("seq_status", f"Simulating {phase_name}..."))
                self.gui_queue.put(("trigger_sensor", sensor_id))

                # Sleep in small slices to respond promptly to cancellation
                elapsed = 0.0
                step = 0.05
                while elapsed < delay_sec:
                    if self.sequence_stop_event.is_set():
                        break
                    time.sleep(step)
                    elapsed += step

            if not self.sequence_stop_event.is_set():
                self.gui_queue.put(("status", "Clinical Cannulation Sequence completed successfully."))
                self.gui_queue.put(("seq_status", "Completed (Vessel Lumen Reached)"))
            else:
                self.gui_queue.put(("warn", "Clinical Cannulation Sequence aborted by user."))
                self.gui_queue.put(("seq_status", "Aborted"))
        finally:
            self.gui_queue.put(("seq_finished", None))

    # -------------------------------------------------------------------------
    # Random Hit Mode
    # -------------------------------------------------------------------------
    def toggle_random_hits(self):
        """Toggle automated random hit generation."""
        if self.random_thread and self.random_thread.is_alive():
            self.stop_random_hits()
        else:
            self.start_random_hits()

    def start_random_hits(self):
        """Start random sensor hit generator thread."""
        self.random_stop_event.clear()
        self.btn_random.config(text="⏹ Stop Random Hits", bg=self.c_danger)
        self._log_status(f"Random Hit Mode started (Interval: {self.random_rate_var.get():.2f}s)")

        self.random_thread = threading.Thread(
            target=self._random_hit_worker,
            daemon=True,
            name="RandomHitWorker"
        )
        self.random_thread.start()

    def stop_random_hits(self):
        """Stop random sensor hit generator thread."""
        self.random_stop_event.set()
        self.btn_random.config(text="▶ Start Random Hits", bg=self.c_success)
        self._log_status("Random Hit Mode stopped.")

    def _random_hit_worker(self):
        """Background worker generating random tactile hits."""
        while not self.random_stop_event.is_set():
            sensor_id = random.randint(0, 8)
            self.gui_queue.put(("trigger_sensor", sensor_id))

            interval = max(0.05, self.random_rate_var.get())
            elapsed = 0.0
            step = 0.05
            while elapsed < interval:
                if self.random_stop_event.is_set():
                    break
                time.sleep(step)
                elapsed += step

    # -------------------------------------------------------------------------
    # Thread-Safe GUI Event Processing
    # -------------------------------------------------------------------------
    def _process_gui_queue(self):
        """Drain background events on the Tkinter main thread."""
        while True:
            try:
                event_type, data = self.gui_queue.get_nowait()
            except queue.Empty:
                break

            if event_type == "tx":
                self._log_tx(data)
            elif event_type == "status":
                self._log_status(data)
            elif event_type == "warn":
                self._log_warn(data)
            elif event_type == "error":
                self._log_error(data)
            elif event_type == "increment_tx":
                self.total_tx_count += 1
                self.tx_counter_lbl.config(text=f"Packets Sent: {self.total_tx_count}")
            elif event_type == "trigger_sensor":
                self.trigger_sensor(data)
            elif event_type == "seq_status":
                self.seq_status_lbl.config(text=data)
            elif event_type == "seq_finished":
                self.btn_clinical.config(state=tk.NORMAL)
                self.btn_stop_seq.config(state=tk.DISABLED, bg="#6c757d")
            elif event_type == "disconnect_req":
                self.disconnect()

        if self.running:
            self.root.after(30, self._process_gui_queue)

    # -------------------------------------------------------------------------
    # Logging Utilities
    # -------------------------------------------------------------------------
    def _timestamp(self) -> str:
        """Return formatted local timestamp with milliseconds."""
        t = time.time()
        milli = int((t % 1) * 1000)
        return time.strftime("%H:%M:%S", time.localtime(t)) + f".{milli:03d}"

    def _append_log(self, tag: str, message: str):
        """Append line to log widget with timestamp."""
        ts = self._timestamp()
        self.log_text.insert(tk.END, f"[{ts}] ", "time")
        self.log_text.insert(tk.END, f"{message}\n", tag)

        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)

    def _log_tx(self, msg: str):
        self._append_log("tx", msg)

    def _log_status(self, msg: str):
        self._append_log("status", f"[INFO] {msg}")

    def _log_warn(self, msg: str):
        self._append_log("warn", f"[WARN] {msg}")

    def _log_error(self, msg: str):
        self._append_log("error", f"[ERROR] {msg}")

    def clear_log(self):
        """Clear traffic log contents."""
        self.log_text.delete("1.0", tk.END)
        self._log_status("Traffic log cleared.")

    def copy_log(self):
        """Copy all log text to system clipboard."""
        content = self.log_text.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self._log_status("Log copied to system clipboard.")

    # -------------------------------------------------------------------------
    # Clean Shutdown
    # -------------------------------------------------------------------------
    def on_closing(self):
        """Clean shutdown handler."""
        self.running = False
        self.sequence_stop_event.set()
        self.random_stop_event.set()

        if self.serial_conn:
            try:
                self.serial_conn.close()
            except Exception:
                pass
            self.serial_conn = None

        self.root.destroy()


def main():
    """Application entry point."""
    root = tk.Tk()
    app = PiezoEmulatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
