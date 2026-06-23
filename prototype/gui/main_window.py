"""Main window: Connect -> Mode/Settings -> Session, as a QStackedWidget."""

from __future__ import annotations

from pathlib import Path
from statistics import median

import serial
from PySide6.QtCore import QSettings, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from pyqtgraph import PlotWidget

from participants import (
    DEFAULT_GROUP,
    GROUPS,
    Participant,
    next_session_number,
    read_participants,
    record_session,
    session_file_name,
)
from protocol import SETTING_NAMES, Settings, build_set_command, parse_dataframe, parse_get_response
from serial_link import SerialLink, find_teensy_port, list_all_ports

AUTO_DETECT_RETRY_MS = 500
AUTO_DETECT_ATTEMPTS_BEFORE_FALLBACK = 6  # ~3 s


class ConnectPage(QWidget):
    """Auto-detects and connects to the Teensy; falls back to manual selection."""

    connected = Signal(SerialLink, Settings)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._attempts = 0

        self._status_label = QLabel("Searching for Teensy...")
        self._port_combo = QComboBox()
        self._connect_button = QPushButton("Connect")
        self._connect_button.clicked.connect(self._connect_to_selected_port)
        self._port_combo.setVisible(False)
        self._connect_button.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self._status_label)
        manual_row = QHBoxLayout()
        manual_row.addWidget(self._port_combo)
        manual_row.addWidget(self._connect_button)
        layout.addLayout(manual_row)
        layout.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._try_auto_detect)
        self._timer.start(AUTO_DETECT_RETRY_MS)

    def _try_auto_detect(self) -> None:
        self._attempts += 1
        port = find_teensy_port()
        if port is not None:
            self._timer.stop()
            self._open(port)
            return
        if self._attempts >= AUTO_DETECT_ATTEMPTS_BEFORE_FALLBACK:
            self._show_manual_fallback()

    def _show_manual_fallback(self) -> None:
        self._status_label.setText("Couldn't find a Teensy automatically. Select a port:")
        self._port_combo.clear()
        self._port_combo.addItems(list_all_ports())
        self._port_combo.setVisible(True)
        self._connect_button.setVisible(True)

    def _connect_to_selected_port(self) -> None:
        port = self._port_combo.currentText()
        if port:
            self._timer.stop()
            self._open(port)

    def _open(self, port: str) -> None:
        self._status_label.setText(f"Connecting to {port}...")
        try:
            self._link = SerialLink(port)
        except serial.SerialException as exc:
            self._status_label.setText(f"Couldn't open {port}: {exc}")
            self._show_manual_fallback()
            return
        self._link.line_received.connect(self._on_line)
        self._link.connection_lost.connect(self._on_connection_lost)
        self._link.start()
        self._link.send("GET")

    def _on_line(self, line: str) -> None:
        settings = parse_get_response(line)
        if settings is not None and self._link is not None:
            self._link.line_received.disconnect(self._on_line)
            self.connected.emit(self._link, settings)

    def _on_connection_lost(self, message: str) -> None:
        self._status_label.setText(f"Connection lost: {message}")
        self._link = None
        self._attempts = 0
        self._timer.start(AUTO_DETECT_RETRY_MS)


class ModePage(QWidget):
    """Default vs Advanced mode selection, with the Advanced settings form."""

    mode_confirmed = Signal(Settings)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._defaults: Settings | None = None

        self._default_radio = QRadioButton("Default")
        self._advanced_radio = QRadioButton("Advanced")
        self._default_radio.setChecked(True)
        self._default_radio.toggled.connect(self._update_form_enabled)

        self._fields: dict[str, QSpinBox] = {}
        form_layout = QFormLayout()
        for name in SETTING_NAMES:
            spin_box = QSpinBox()
            spin_box.setRange(0, 65535)
            form_layout.addRow(name, spin_box)
            self._fields[name] = spin_box
        self._form_group = QGroupBox("Advanced settings")
        self._form_group.setLayout(form_layout)
        self._form_group.setEnabled(False)

        continue_button = QPushButton("Continue")
        continue_button.clicked.connect(self._confirm)

        layout = QVBoxLayout(self)
        layout.addWidget(self._default_radio)
        layout.addWidget(self._advanced_radio)
        layout.addWidget(self._form_group)
        layout.addWidget(continue_button)

    def set_link_and_defaults(self, link: SerialLink, defaults: Settings) -> None:
        self._link = link
        self._defaults = defaults
        self._fields["flickerFrequencyHz"].setValue(defaults.flicker_frequency_hz)
        self._fields["amberValue"].setValue(defaults.amber_value)
        self._fields["maxRed"].setValue(defaults.max_red)
        self._fields["maxGreen"].setValue(defaults.max_green)
        self._fields["minRed"].setValue(defaults.min_red)
        self._fields["minGreen"].setValue(defaults.min_green)

    def _update_form_enabled(self) -> None:
        self._form_group.setEnabled(self._advanced_radio.isChecked())

    def _confirm(self) -> None:
        if self._link is None or self._defaults is None:
            return
        if self._default_radio.isChecked():
            self._link.send("MODE DEFAULT")
            self.mode_confirmed.emit(self._defaults)
            return

        values = {name: field.value() for name, field in self._fields.items()}
        self._link.send("MODE ADVANCED")
        self._link.send(build_set_command(values))
        resolved = Settings(
            mode="ADVANCED",
            flicker_frequency_hz=values["flickerFrequencyHz"],
            amber_value=values["amberValue"],
            max_red=values["maxRed"],
            max_green=values["maxGreen"],
            min_red=values["minRed"],
            min_green=values["minGreen"],
        )
        self.mode_confirmed.emit(resolved)


class ParticipantPage(QWidget):
    """Pick a save folder, then add a session to an existing participant in
    that folder or create a new one (subject ID + group). The folder's
    participants.csv is the source of truth for who already exists."""

    participant_confirmed = Signal(str, str, str)  # sub_id, group, folder

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._settings = QSettings("behExperiment1", "KnobsGui")

        self._folder_edit = QLineEdit(self._settings.value("save_folder", ""))
        self._folder_edit.setReadOnly(True)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._choose_folder)
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Save folder:"))
        folder_row.addWidget(self._folder_edit, 1)
        folder_row.addWidget(browse_button)

        self._existing_radio = QRadioButton("Existing participant")
        self._new_radio = QRadioButton("New participant")
        self._new_radio.setChecked(True)
        self._existing_radio.toggled.connect(self._update_enabled)
        self._existing_combo = QComboBox()

        self._sub_id_edit = QLineEdit()
        self._group_combo = QComboBox()
        self._group_combo.addItems(GROUPS)
        self._group_combo.setCurrentText(DEFAULT_GROUP)
        new_form = QFormLayout()
        new_form.addRow("Subject ID", self._sub_id_edit)
        new_form.addRow("Group", self._group_combo)
        self._new_group = QGroupBox("New participant")
        self._new_group.setLayout(new_form)

        self._error_label = QLabel("")
        continue_button = QPushButton("Continue")
        continue_button.clicked.connect(self._confirm)

        layout = QVBoxLayout(self)
        layout.addLayout(folder_row)
        layout.addWidget(self._existing_radio)
        layout.addWidget(self._existing_combo)
        layout.addWidget(self._new_radio)
        layout.addWidget(self._new_group)
        layout.addWidget(self._error_label)
        layout.addWidget(continue_button)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._reload_participants()

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select save folder", self._folder_edit.text())
        if folder:
            self._folder_edit.setText(folder)
            self._settings.setValue("save_folder", folder)
            self._reload_participants()

    def _reload_participants(self) -> None:
        self._existing_combo.clear()
        folder = self._folder_edit.text()
        participants = read_participants(Path(folder)) if folder else []
        for participant in participants:
            self._existing_combo.addItem(f"{participant.sub_id} ({participant.group})", participant)
        self._existing_radio.setEnabled(bool(participants))
        if not participants:
            self._new_radio.setChecked(True)
        self._update_enabled()

    def _update_enabled(self) -> None:
        existing = self._existing_radio.isChecked()
        self._existing_combo.setEnabled(existing)
        self._new_group.setEnabled(not existing)

    def _confirm(self) -> None:
        folder = self._folder_edit.text()
        if not folder:
            self._error_label.setText("Choose a save folder first.")
            return
        if self._existing_radio.isChecked():
            participant = self._existing_combo.currentData()
            if participant is None:
                self._error_label.setText("Select a participant.")
                return
            sub_id, group = participant.sub_id, participant.group
        else:
            sub_id = self._sub_id_edit.text().strip()
            if not sub_id:
                self._error_label.setText("Enter a subject ID.")
                return
            existing_ids = {self._existing_combo.itemData(i).sub_id for i in range(self._existing_combo.count())}
            if sub_id in existing_ids:
                self._error_label.setText(f"{sub_id} already exists; pick it under Existing participant.")
                return
            group = self._group_combo.currentText()
        self._error_label.setText("")
        self.participant_confirmed.emit(sub_id, group, folder)


class SessionPage(QWidget):
    """Start/Stop controls, the live red/green scatter plot, and a log of
    button-press results. "Back" is only enabled while no session is
    running (i.e. before Start, or after Stop)."""

    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._session_active = False
        self._press_reds: list[int] = []
        self._press_greens: list[int] = []

        self._folder: Path | None = None
        self._sub_id = ""
        self._group = ""
        self._session_number = 0
        self._run_file: Path | None = None
        self._settings: Settings | None = None

        self._status_label = QLabel("Not started")
        self._start_button = QPushButton("Start")
        self._stop_button = QPushButton("Stop")
        self._back_button = QPushButton("Back to experiment selection")
        self._save_button = QPushButton("Save Results...")
        self._start_button.clicked.connect(self._start)
        self._stop_button.clicked.connect(self._stop)
        self._back_button.clicked.connect(self.back_requested)
        self._save_button.clicked.connect(self._save_results)

        self._plot = PlotWidget()
        self._plot.setBackground("k")
        self._plot.setLabel("bottom", "Red LED intensity (A/D)")
        self._plot.setLabel("left", "Green LED intensity (A/D)")
        # Live position: solid yellow round marker.
        self._current_marker = self._plot.plot(
            [], [], pen=None, symbol="o", symbolBrush="y", symbolPen=None, symbolSize=16
        )
        # One gray X per button press, accumulated for the whole session.
        self._press_marks = self._plot.plot(
            [], [], pen=None, symbol="x", symbolBrush=None, symbolPen="gray", symbolSize=14
        )
        # Median of all button-press locations so far; only shown once
        # there's at least one press.
        self._median_marker = self._plot.plot(
            [], [], pen=None, symbol="star", symbolBrush="r", symbolPen=None, symbolSize=20
        )

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Trial", "Red", "Green"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._median_label = QLabel("Median: -")

        button_row = QHBoxLayout()
        button_row.addWidget(self._start_button)
        button_row.addWidget(self._stop_button)
        button_row.addWidget(self._back_button)
        button_row.addWidget(self._save_button)

        table_column = QVBoxLayout()
        table_column.addWidget(self._table)
        table_column.addWidget(self._median_label)

        plot_and_table = QHBoxLayout()
        plot_and_table.addWidget(self._plot, stretch=3)
        plot_and_table.addLayout(table_column, stretch=1)

        layout = QVBoxLayout(self)
        layout.addLayout(button_row)
        layout.addWidget(self._status_label)
        layout.addLayout(plot_and_table)

        self._update_button_states()

    def set_participant(self, folder: Path, sub_id: str, group: str) -> None:
        self._folder = folder
        self._sub_id = sub_id
        self._group = group

    def start_session(self, link: SerialLink, settings: Settings) -> None:
        if self._link is None:
            self._link = link
            self._link.line_received.connect(self._on_line)
        else:
            self._link = link

        self._press_reds.clear()
        self._press_greens.clear()
        self._press_marks.setData([], [])
        self._median_marker.setData([], [])
        self._current_marker.setData([], [])
        self._table.setRowCount(0)
        self._median_label.setText("Median: -")
        self._session_active = False
        self._run_file = None
        self._settings = settings
        self._status_label.setText("Not started")
        self._update_button_states()

        self._plot.setXRange(settings.min_red, settings.max_red, padding=0)
        self._plot.setYRange(settings.min_green, settings.max_green, padding=0)

    def _start(self) -> None:
        if self._run_file is None:
            self._open_run_file()
        self._send("START")
        self._session_active = True
        self._update_button_states()

    def _open_run_file(self) -> None:
        # One file per session, named SubID_R{next}.txt, created with its
        # header when the session starts; autosaved on every press after.
        participant = Participant(self._sub_id, self._group)
        self._session_number = next_session_number(self._folder, self._sub_id)
        file_name = session_file_name(self._sub_id, self._session_number)
        self._run_file = self._folder / file_name
        self._write_table_to(self._run_file)
        record_session(self._folder, participant, self._session_number, file_name, self._settings)

    def _stop(self) -> None:
        self._send("STOP")
        self._session_active = False
        self._update_button_states()

    def _update_button_states(self) -> None:
        self._start_button.setEnabled(not self._session_active)
        self._stop_button.setEnabled(self._session_active)
        self._back_button.setEnabled(not self._session_active)

    def _send(self, command: str) -> None:
        if self._link is not None:
            self._link.send(command)

    def _on_line(self, line: str) -> None:
        frame = parse_dataframe(line)
        if frame is None:
            return
        self._current_marker.setData([frame.red], [frame.green])
        self._status_label.setText(
            f"{self._sub_id} ({self._group}) session R{self._session_number}  |  "
            f"Search {frame.trial_number}, last Press={frame.press}"
        )

        if frame.press == 1:
            self._press_reds.append(frame.red)
            self._press_greens.append(frame.green)
            self._press_marks.setData(self._press_reds, self._press_greens)
            red_median = median(self._press_reds)
            green_median = median(self._press_greens)
            self._median_marker.setData([red_median], [green_median])
            self._median_label.setText(f"Median  Red: {red_median:g}  Green: {green_median:g}")
            self._append_table_row(frame.trial_number, frame.red, frame.green)
            if self._run_file is not None:
                self._write_table_to(self._run_file)

    def _append_table_row(self, trial_number: int, red: int, green: int) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        for column, value in enumerate((trial_number, red, green)):
            self._table.setItem(row, column, QTableWidgetItem(str(value)))
        self._table.scrollToBottom()

    def _save_results(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Results", "results.txt", "Text files (*.txt)")
        if path:
            self._write_table_to(Path(path))

    def _write_table_to(self, path: Path) -> None:
        with open(path, "w") as results_file:
            results_file.write("Trial Red Green\n")
            for row in range(self._table.rowCount()):
                values = (self._table.item(row, column).text() for column in range(3))
                results_file.write(" ".join(values) + "\n")


def _format_settings(settings: Settings) -> str:
    return (
        f"Mode: {settings.mode} | Flicker: {settings.flicker_frequency_hz} Hz | "
        f"Amber: {settings.amber_value} | "
        f"Red: [{settings.min_red}, {settings.max_red}] | "
        f"Green: [{settings.min_green}, {settings.max_green}]"
    )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Knobs Experiment")

        self._connect_page = ConnectPage()
        self._participant_page = ParticipantPage()
        self._mode_page = ModePage()
        self._session_page = SessionPage()

        self._stack = QStackedWidget()
        self._stack.addWidget(self._connect_page)
        self._stack.addWidget(self._participant_page)
        self._stack.addWidget(self._mode_page)
        self._stack.addWidget(self._session_page)
        self.setCentralWidget(self._stack)

        self._folder: Path | None = None
        self._sub_id = ""
        self._group = ""

        # Always-visible footer with the active configuration, regardless of
        # which page is showing.
        self._settings_label = QLabel("Not connected")
        self.statusBar().addPermanentWidget(self._settings_label, 1)

        self._connect_page.connected.connect(self._on_connected)
        self._participant_page.participant_confirmed.connect(self._on_participant_confirmed)
        self._mode_page.mode_confirmed.connect(self._on_mode_confirmed)
        self._session_page.back_requested.connect(self._on_back_requested)

    def _on_connected(self, link: SerialLink, settings: Settings) -> None:
        self._link = link
        self._settings_label.setText(_format_settings(settings))
        self._stack.setCurrentWidget(self._participant_page)

    def _on_participant_confirmed(self, sub_id: str, group: str, folder: str) -> None:
        self._sub_id = sub_id
        self._group = group
        self._folder = Path(folder)
        # Re-query GET before showing the mode form, so it reflects whatever
        # is currently active on the firmware (settings persist across modes).
        self._link.line_received.connect(self._on_settings_for_mode)
        self._link.send("GET")

    def _on_settings_for_mode(self, line: str) -> None:
        settings = parse_get_response(line)
        if settings is None:
            return
        self._link.line_received.disconnect(self._on_settings_for_mode)
        self._mode_page.set_link_and_defaults(self._link, settings)
        self._settings_label.setText(_format_settings(settings))
        self._stack.setCurrentWidget(self._mode_page)

    def _on_mode_confirmed(self, settings: Settings) -> None:
        self._session_page.set_participant(self._folder, self._sub_id, self._group)
        self._session_page.start_session(self._link, settings)
        self._settings_label.setText(_format_settings(settings))
        self._stack.setCurrentWidget(self._session_page)

    def _on_back_requested(self) -> None:
        self._stack.setCurrentWidget(self._participant_page)
