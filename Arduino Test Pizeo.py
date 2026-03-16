import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import threading
import queue
import time
import random


class PiezoSerialEmulator:

    def __init__(self):

        self.root = tk.Tk()
        self.root.title("Piezo Sensor Emulator")

        self.serial_conn = None
        self.send_queue = queue.Queue()
        self.running = False

        # PORT
        tk.Label(self.root, text="COM Port").grid(row=0, column=0)
        self.port_var = tk.StringVar()

        self.port_menu = ttk.Combobox(
            self.root,
            textvariable=self.port_var,
            values=self.get_ports(),
            width=10
        )
        self.port_menu.grid(row=0, column=1)

        # BAUD
        tk.Label(self.root, text="Baud").grid(row=0, column=2)

        self.baud_var = tk.StringVar(value="115200")
        tk.Entry(self.root, textvariable=self.baud_var, width=10).grid(row=0, column=3)

        tk.Button(self.root, text="Connect", command=self.connect).grid(row=0, column=4)

        # SENSOR INPUT
        tk.Label(self.root, text="Sensor Index").grid(row=1, column=0)

        self.sensor_var = tk.StringVar()

        tk.Entry(self.root, textvariable=self.sensor_var, width=10).grid(row=1, column=1)

        tk.Button(self.root, text="SEND HIT", command=self.send_hit).grid(row=1, column=2)

        tk.Button(self.root, text="Random Hit", command=self.random_hit).grid(row=1, column=3)

        # LOG
        self.log = tk.Text(self.root, height=15, width=50)
        self.log.grid(row=2, column=0, columnspan=5)

        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

        self.root.mainloop()

    def get_ports(self):

        return [p.device for p in serial.tools.list_ports.comports()]

    def connect(self):

        try:

            port = self.port_var.get()
            baud = int(self.baud_var.get())

            self.serial_conn = serial.Serial(port, baud, timeout=0)

            self.running = True

            threading.Thread(target=self.serial_worker, daemon=True).start()

            self.print_log(f"Connected to {port} @ {baud}")

        except Exception as e:

            self.print_log(f"Connection failed: {e}")

    def serial_worker(self):

        while self.running:

            try:

                msg = self.send_queue.get(timeout=0.1)

                if self.serial_conn:
                    self.serial_conn.write(msg.encode())

            except queue.Empty:
                pass

    def send_hit(self):

        sensor = self.sensor_var.get()

        if not sensor.isdigit():
            self.print_log("Invalid index")
            return

        msg = f"{sensor}\n"

        self.send_queue.put(msg)

        self.print_log(f"Sent → {sensor}")

    def random_hit(self):

        sensor = random.randint(0, 8)

        self.sensor_var.set(str(sensor))

        self.send_hit()

    def print_log(self, msg):

        t = time.strftime("%H:%M:%S")

        self.log.insert(tk.END, f"[{t}] {msg}\n")

        self.log.see(tk.END)

    def shutdown(self):

        self.running = False

        if self.serial_conn:
            self.serial_conn.close()

        self.root.destroy()


PiezoSerialEmulator()