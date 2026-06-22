"""Serial connection to the Teensy: port discovery, background line reading."""

from __future__ import annotations

import serial
from PySide6.QtCore import QThread, Signal
from serial.tools import list_ports

BAUD_RATE = 38400
READ_TIMEOUT_S = 0.1

# PJRC's USB vendor ID, used by all Teensy boards.
TEENSY_VENDOR_ID = 0x16C0


def find_teensy_port() -> str | None:
    """Returns the first serial port whose USB vendor ID matches a Teensy, or None."""
    for port in list_ports.comports():
        if port.vid == TEENSY_VENDOR_ID:
            return port.device
    return None


def list_all_ports() -> list[str]:
    """Returns every available serial port, for the manual-selection fallback."""
    return [port.device for port in list_ports.comports()]


class SerialLink(QThread):
    """Owns the serial connection and reads lines on a background thread.

    Writes (send()) are called directly from the main thread; pyserial's
    Serial object supports one reader thread plus writes from elsewhere
    without extra locking.
    """

    line_received = Signal(str)
    connection_lost = Signal(str)

    def __init__(self, port: str, parent=None) -> None:
        super().__init__(parent)
        self._serial = serial.Serial(port, BAUD_RATE, timeout=READ_TIMEOUT_S)

    def send(self, command: str) -> None:
        self._serial.write((command + "\n").encode("ascii"))

    def close(self) -> None:
        self.requestInterruption()
        self.wait()
        self._serial.close()

    def run(self) -> None:
        while not self.isInterruptionRequested():
            try:
                raw_line = self._serial.readline()
            except serial.SerialException as exc:
                self.connection_lost.emit(str(exc))
                return
            if not raw_line:
                continue
            line = raw_line.decode("ascii", errors="ignore").strip()
            if line:
                self.line_received.emit(line)
