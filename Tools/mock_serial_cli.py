"""
Haptic Needle Twin - Headless Mock Serial CLI Tool
==================================================
Command-line test harness and CI verification utility for the Unreal Engine 5
Haptic Needle Twin serial piezo sensor interface (APizeoSensorInput).

Capabilities:
  * Emulates 3x3 tactile matrix piezo sensor packet stream over serial hardware.
  * Supports fixed sequence simulation (e.g. clinical 0,1,2,3) or randomized hit stress tests.
  * Supports headless `--dry-run` for CI/CD runners without COM hardware or virtual serial drivers.
  * Supports `--loopback` testing to verify bidirectional transmission fidelity.
  * Emits deterministic exit codes (0 = Success, 1 = Config/Arg Error, 2 = Hardware/Verification Error).

Usage Examples:
  # CI Dry Run (verifies packet synthesis & validation pipeline without serial ports):
  py Tools/mock_serial_cli.py --dry-run --sequence 0,1,2,3 --interval 0.2

  # CI Dry Run with In-Memory Loopback Verification:
  py Tools/mock_serial_cli.py --dry-run --loopback --sequence 0,1,2,3

  # Random Hit Stress Test in Dry-Run Mode:
  py Tools/mock_serial_cli.py --dry-run --random --count 20 --interval 0.05

  # Real COM Port Hardware Transmission:
  py Tools/mock_serial_cli.py --port COM3 --baud 115200 --sequence 0,1,2,3

  # Paired COM Loopback Test (e.g., com0com virtual null-modem COM1 <-> COM2):
  py Tools/mock_serial_cli.py --port COM1 --rx-port COM2 --loopback --sequence 0,1,2,3

Author: L2_Python_Tooling_Developer
Target Hardware: Arduino / ESP32 / UE5 APizeoSensorInput
"""

import sys
import time
import queue
import random
import argparse
from typing import List, Optional, Tuple

# Try to import pyserial gracefully
try:
    import serial
    import serial.tools.list_ports
    PYSERIAL_AVAILABLE = True
except ImportError:
    PYSERIAL_AVAILABLE = False


def format_timestamp() -> str:
    """Return ISO-like high precision timestamp."""
    t = time.time()
    milli = int((t % 1) * 1000)
    return time.strftime("%H:%M:%S", time.localtime(t)) + f".{milli:03d}"


def format_hex(data: bytes) -> str:
    """Format bytes into spaced hexadecimal string."""
    return " ".join(f"0x{b:02X}" for b in data)


def parse_sequence_arg(seq_str: str) -> List[int]:
    """Parse comma-separated sequence string into list of sensor IDs."""
    items = []
    for part in seq_str.split(","):
        cleaned = part.strip()
        if not cleaned:
            continue
        if not cleaned.isdigit():
            raise ValueError(f"Invalid sensor index '{cleaned}'. Must be an integer 0-8.")
        val = int(cleaned)
        if not (0 <= val <= 8):
            raise ValueError(f"Sensor index {val} out of range [0, 8].")
        items.append(val)
    if not items:
        raise ValueError("Sequence cannot be empty.")
    return items


def run_dry_run(
    sequence: List[int],
    interval: float,
    is_loopback: bool,
    verbose: bool
) -> int:
    """Execute sequence in dry-run mode without opening hardware serial ports."""
    print("=" * 70)
    print(" [DRY-RUN MODE] Simulating Serial Stream without Hardware")
    if is_loopback:
        print(" [LOOPBACK CHECK] In-memory verification enabled")
    print("=" * 70)

    total_packets = len(sequence)
    verified_count = 0
    start_time = time.time()

    # In-memory loopback simulated queue
    mock_channel: queue.Queue = queue.Queue()

    for idx, sensor_id in enumerate(sequence, start=1):
        # Format payload identical to Arduino & UE5 APizeoSensorInput expectation: f"{sensor_id}\n"
        payload_str = f"{sensor_id}\n"
        raw_bytes = payload_str.encode("utf-8")
        hex_str = format_hex(raw_bytes)
        ts = format_timestamp()

        print(f"[{ts}] TX #{idx:03d}/{total_packets:03d} | Sensor: {sensor_id} | Payload: {repr(payload_str):<6} | Hex: [{hex_str}]")

        if is_loopback:
            # Simulate transmission delay & reception
            mock_channel.put(raw_bytes)
            rx_bytes = mock_channel.get()
            rx_str = rx_bytes.decode("utf-8", errors="replace")
            # Verify packet syntax: must be digit followed by newline
            rx_digit = rx_str.strip()
            if rx_digit == str(sensor_id):
                verified_count += 1
                if verbose:
                    print(f"[{ts}] RX VERIFIED  | Received: {repr(rx_str):<6} | Match: TRUE")
            else:
                print(f"[{ts}] RX MISMATCH  | Expected: {sensor_id}, Got: {repr(rx_str)}", file=sys.stderr)

        if idx < total_packets and interval > 0:
            time.sleep(interval)

    duration = time.time() - start_time
    print("-" * 70)
    print(f"Summary: Sent {total_packets} packets in {duration:.3f}s")
    if is_loopback:
        success_rate = (verified_count / total_packets) * 100.0 if total_packets > 0 else 0.0
        print(f"Verification: {verified_count}/{total_packets} Verified ({success_rate:.1f}%)")
        if verified_count != total_packets:
            return 2

    return 0


def run_hardware(
    port: str,
    baud: int,
    sequence: List[int],
    interval: float,
    is_loopback: bool,
    rx_port: Optional[str],
    timeout: float,
    verbose: bool
) -> int:
    """Execute sequence over physical or virtual serial port hardware."""
    if not PYSERIAL_AVAILABLE:
        print("[ERROR] pyserial is required for hardware communication.", file=sys.stderr)
        print("Please install requirements: pip install -r requirements.txt", file=sys.stderr)
        return 1

    tx_conn: Optional[serial.Serial] = None
    rx_conn: Optional[serial.Serial] = None

    try:
        print(f"[*] Opening TX port {port} @ {baud} baud (timeout={timeout}s)...")
        tx_conn = serial.Serial(port=port, baudrate=baud, timeout=timeout, write_timeout=timeout)

        if is_loopback:
            target_rx_port = rx_port if rx_port else port
            if target_rx_port == port:
                print(f"[*] Using same port {port} for TX/RX loopback.")
                rx_conn = tx_conn
            else:
                print(f"[*] Opening paired RX port {target_rx_port} @ {baud} baud...")
                rx_conn = serial.Serial(port=target_rx_port, baudrate=baud, timeout=timeout)
    except Exception as e:
        print(f"[ERROR] Failed to open serial port: {e}", file=sys.stderr)
        return 2

    print("=" * 70)
    print(f" [HARDWARE ACTIVE] Port: {port} | Baud: {baud} | Loopback: {is_loopback}")
    print("=" * 70)

    total_packets = len(sequence)
    verified_count = 0
    start_time = time.time()

    try:
        for idx, sensor_id in enumerate(sequence, start=1):
            payload_str = f"{sensor_id}\n"
            raw_bytes = payload_str.encode("utf-8")
            hex_str = format_hex(raw_bytes)
            ts = format_timestamp()

            # Transmit
            tx_conn.write(raw_bytes)
            tx_conn.flush()
            print(f"[{ts}] TX #{idx:03d}/{total_packets:03d} | Sensor: {sensor_id} | Payload: {repr(payload_str):<6} | Hex: [{hex_str}]")

            # If loopback is requested, attempt to read back packet
            if is_loopback and rx_conn:
                rx_line = rx_conn.readline()
                rx_ts = format_timestamp()
                if not rx_line:
                    print(f"[{rx_ts}] RX TIMEOUT   | No response within {timeout}s", file=sys.stderr)
                else:
                    rx_str = rx_line.decode("utf-8", errors="replace")
                    rx_cleaned = rx_str.strip()
                    if rx_cleaned == str(sensor_id):
                        verified_count += 1
                        if verbose:
                            print(f"[{rx_ts}] RX VERIFIED  | Received: {repr(rx_str):<6} | Match: TRUE")
                    else:
                        print(f"[{rx_ts}] RX MISMATCH  | Expected: {sensor_id}, Got: {repr(rx_str)}", file=sys.stderr)

            if idx < total_packets and interval > 0:
                time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[!] Transmission interrupted by user.")
    except Exception as e:
        print(f"[ERROR] Communication error during transmission: {e}", file=sys.stderr)
        return 2
    finally:
        # Cleanly close ports
        if tx_conn:
            try:
                tx_conn.close()
            except Exception:
                pass
        if rx_conn and rx_conn is not tx_conn:
            try:
                rx_conn.close()
            except Exception:
                pass

    duration = time.time() - start_time
    print("-" * 70)
    print(f"Summary: Sent {total_packets} packets in {duration:.3f}s")
    if is_loopback:
        success_rate = (verified_count / total_packets) * 100.0 if total_packets > 0 else 0.0
        print(f"Verification: {verified_count}/{total_packets} Verified ({success_rate:.1f}%)")
        if verified_count != total_packets:
            return 2

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Headless Mock Serial CLI for UE5 Haptic Needle Twin Tactile Sensors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  py Tools/mock_serial_cli.py --dry-run --sequence 0,1,2,3
  py Tools/mock_serial_cli.py --dry-run --loopback --sequence 0,1,2,3
  py Tools/mock_serial_cli.py --dry-run --random --count 20 --interval 0.1
  py Tools/mock_serial_cli.py --port COM3 --baud 115200 --sequence 0,1,2,3
  py Tools/mock_serial_cli.py --port COM1 --rx-port COM2 --loopback --sequence 0,1,2,3
        """
    )

    parser.add_argument(
        "--port", "-p",
        type=str,
        default=None,
        help="Serial COM port (e.g. COM1, COM3, /dev/ttyUSB0). Required unless --dry-run is specified."
    )
    parser.add_argument(
        "--rx-port",
        type=str,
        default=None,
        help="Optional secondary COM port for loopback tests (e.g. COM2 when TX is COM1)."
    )
    parser.add_argument(
        "--baud", "-b",
        type=int,
        default=115200,
        help="Serial baud rate (default: 115200)."
    )
    parser.add_argument(
        "--sequence", "-s",
        type=str,
        default=None,
        help="Comma-separated sensor IDs to send (e.g. '0,1,2,3'). Sensors must be 0-8."
    )
    parser.add_argument(
        "--clinical",
        action="store_true",
        help="Shortcut for clinical cannulation sequence: 0,1,2,3."
    )
    parser.add_argument(
        "--random", "-r",
        action="store_true",
        help="Generate random sensor hits (sensor IDs 0-8)."
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=10,
        help="Number of hits when using --random (default: 10)."
    )
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=0.5,
        help="Interval delay in seconds between packets (default: 0.5s)."
    )
    parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=2.0,
        help="Read/Write timeout in seconds (default: 2.0s)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate transmission without opening physical COM ports (for CI/automated testing)."
    )
    parser.add_argument(
        "--loopback",
        action="store_true",
        help="Enable loopback verification (validates received payload matches transmitted sensor ID)."
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="List available hardware serial COM ports and exit."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output with detailed RX verification logging."
    )

    args = parser.parse_args()

    # Handle --list-ports
    if args.list_ports:
        if not PYSERIAL_AVAILABLE:
            print("[ERROR] pyserial is not installed. Run: pip install -r requirements.txt", file=sys.stderr)
            return 1
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("No serial COM ports detected on this system.")
        else:
            print(f"Available Serial Ports ({len(ports)} found):")
            for p in ports:
                desc = p.description if p.description else "No description"
                print(f"  * {p.device:<10} - {desc}")
        return 0

    # Build sequence list
    sequence: List[int] = []
    if args.clinical:
        sequence = [0, 1, 2, 3]
    elif args.sequence:
        try:
            sequence = parse_sequence_arg(args.sequence)
        except ValueError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return 1
    elif args.random:
        if args.count <= 0:
            print("[ERROR] --count must be greater than 0.", file=sys.stderr)
            return 1
        sequence = [random.randint(0, 8) for _ in range(args.count)]
    else:
        # Default fallback if neither sequence nor random is provided: default to clinical cannulation sequence
        print("[INFO] No sequence specified. Defaulting to clinical cannulation sequence (0,1,2,3).")
        sequence = [0, 1, 2, 3]

    # Validate COM port requirement when not in dry-run
    if not args.dry_run:
        if not args.port:
            print("[ERROR] --port is required when not running in --dry-run mode.", file=sys.stderr)
            print("Hint: Use --dry-run for CI or software-only testing, or provide --port COMx.", file=sys.stderr)
            return 1
        return run_hardware(
            port=args.port,
            baud=args.baud,
            sequence=sequence,
            interval=args.interval,
            is_loopback=args.loopback,
            rx_port=args.rx_port,
            timeout=args.timeout,
            verbose=args.verbose
        )
    else:
        return run_dry_run(
            sequence=sequence,
            interval=args.interval,
            is_loopback=args.loopback,
            verbose=args.verbose
        )


if __name__ == "__main__":
    sys.exit(main())
