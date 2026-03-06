# -*- coding: utf-8 -*-
"""
串口调试工具 v1.3
功能：串口连接/断开、可配置波特率、时间戳显示、数据收发、日志保存、
      防死机机制、缓冲区设置、配置区域显示/隐藏、图标支持、
      字体大小选择、日志查找和高亮功能
"""

import sys
import os
import time
from datetime import datetime

import serial
import serial.tools.list_ports

from PyQt5.QtCore import (
    Qt,
    QTimer,
    pyqtSignal,
    QThread,
    QMutex,
    QMutexLocker,
    QSize,
    QPoint,
)
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QGroupBox,
    QMessageBox,
    QFileDialog,
    QTextEdit,
    QCheckBox,
    QSpinBox,
    QAction,
    QTextBrowser,
    QSplitter,
    QToolBar,
    QFrame,
    QDialog,
    QDialogButtonBox,
)
from PyQt5.QtGui import (
    QFont,
    QPalette,
    QColor,
    QTextCursor,
    QIcon,
    QFontMetrics,
    QTextCharFormat,
    QSyntaxHighlighter,
    QPainter,
)
from PyQt5.Qt import QTextDocument


# ==================== 常量 ====================

VERSION, APP_NAME = "1.3", "串口工具"
DEFAULT_BAUDRATE, DEFAULT_DATABITS, DEFAULT_STOPBITS, DEFAULT_PARITY = (
    115200,
    8,
    1,
    "无",
)
DEFAULT_RECEIVE_BUFFER = DEFAULT_SEND_BUFFER = 1024 * 1024  # 1MB
DEFAULT_RECEIVE_TIMEOUT = DEFAULT_SEND_TIMEOUT = 1.0

BAUDRATE_OPTIONS = [
    "300",
    "600",
    "1200",
    "2400",
    "4800",
    "9600",
    "14400",
    "19200",
    "28800",
    "38400",
    "57600",
    "115200",
    "230400",
    "460800",
    "921600",
]
DATABITS_OPTIONS = ["5", "6", "7", "8"]
STOPBITS_OPTIONS = ["1", "1.5", "2"]
PARITY_OPTIONS = ["无", "奇校验", "偶校验"]
FONT_OPTIONS = ["Consolas", "Monaco", "Courier New", "Roboto Mono", "Fira Code"]
FONT_SIZES = [8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 24]


# ==================== 主题样式 ====================

DARK_THEME = """
QMainWindow { background-color: #282828; }
QGroupBox { color: #cccccc; border: 1px solid #404040; border-radius: 4px; margin-top: 10px; padding-top: 10px; font-weight: 600; background-color: #303030; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 8px; color: #aaaaaa; }
QLabel { color: #bbbbbb; padding: 2px; }
QLineEdit, QComboBox, QSpinBox, QTextEdit, QTextBrowser { background-color: #252525; color: #dddddd; border: 1px solid #404040; border-radius: 3px; padding: 5px; selection-background-color: #505050; }
QPushButton { background-color: #505050; color: #dddddd; border: 1px solid #606060; border-radius: 3px; padding: 6px 12px; font-weight: 500; }
QPushButton:hover { background-color: #606060; border: 1px solid #707070; }
QPushButton:pressed { background-color: #404040; }
QPushButton:disabled { background-color: #303030; color: #888888; border: 1px solid #404040; }
QCheckBox { color: #bbbbbb; spacing: 5px; }
QToolBar { background-color: #303030; border: none; border-bottom: 1px solid #404040; }
QMenuBar { background-color: #303030; color: #bbbbbb; border-bottom: 1px solid #404040; }
QMenu { background-color: #303030; color: #bbbbbb; border: 404040; }
1px solid #QScrollBar:vertical { background-color: #252525; width: 12px; border-radius: 6px; }
QScrollBar::handle:vertical { background-color: #606060; border-radius: 6px; min-height: 20px; }
QScrollBar:horizontal { background-color: #252525; height: 12px; border-radius: 6px; }
QScrollBar::handle:horizontal { background-color: #606060; border-radius: 6px; min-width: 20px; }
"""

LIGHT_THEME = """
QMainWindow { background-color: #f0f0f0; }
QGroupBox { color: #333333; border: 1px solid #cccccc; border-radius: 4px; margin-top: 10px; padding-top: 10px; font-weight: 600; background-color: #f8f8f8; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 8px; color: #666666; }
QLabel { color: #555555; padding: 2px; }
QLineEdit, QComboBox, QSpinBox, QTextEdit, QTextBrowser { background-color: #f5f5f5; color: #333333; border: 1px solid #cccccc; border-radius: 3px; padding: 5px; selection-background-color: #c0c0c0; }
QPushButton { background-color: #e0e0e0; color: #333333; border: 1px solid #cccccc; border-radius: 3px; padding: 6px 12px; font-weight: 500; }
QPushButton:hover { background-color: #d0d0d0; border: 1px solid #999999; }
QPushButton:pressed { background-color: #c0c0c0; }
QPushButton:disabled { background-color: #f0f0f0; color: #999999; border: 1px solid #dddddd; }
QCheckBox { color: #555555; spacing: 5px; }
QToolBar { background-color: #f8f8f8; border: none; border-bottom: 1px solid #cccccc; }
QMenuBar { background-color: #f8f8f8; color: #555555; border-bottom: 1px solid #cccccc; }
QMenu { background-color: #f8f8f8; color: #555555; border: 1px solid #cccccc; }
QScrollBar:vertical { background-color: #f0f0f0; width: 12px; border-radius: 6px; }
QScrollBar::handle:vertical { background-color: #c0c0c0; border-radius: 6px; min-height: 20px; }
QScrollBar:horizontal { background-color: #f0f0f0; height: 12px; border-radius: 6px; }
QScrollBar::handle:horizontal { background-color: #c0c0c0; border-radius: 6px; min-width: 20px; }
"""

TERMINAL_STYLES = {
    "dark": "QTextBrowser { background-color: #1a1a1a; color: #c0c0c0; border: 1px solid #404040; border-radius: 4px; font-family: 'Consolas', 'Monaco', monospace; selection-background-color: #505050; padding: 5px; }",
    "light": "QTextBrowser { background-color: #f5f5f5; color: #333333; border: 1px solid #cccccc; border-radius: 4px; font-family: 'Consolas', 'Monaco', monospace; selection-background-color: #c0c0c0; padding: 5px; }",
}


# ==================== 辅助函数 ====================


def create_palette(theme_type):
    palette = QPalette()
    if theme_type == "dark":
        colors = {
            QPalette.Window: (40, 40, 40),
            QPalette.WindowText: (220, 220, 220),
            QPalette.Base: (25, 25, 25),
            QPalette.Text: (220, 220, 220),
            QPalette.Button: (60, 60, 60),
            QPalette.ButtonText: (220, 220, 220),
            QPalette.Highlight: (80, 120, 180),
            QPalette.HighlightedText: (255, 255, 255),
        }
    else:
        colors = {
            QPalette.Window: (240, 240, 240),
            QPalette.WindowText: (50, 50, 50),
            QPalette.Base: (245, 245, 245),
            QPalette.Text: (50, 50, 50),
            QPalette.Button: (220, 220, 220),
            QPalette.ButtonText: (50, 50, 50),
            QPalette.Highlight: (200, 200, 200),
            QPalette.HighlightedText: (50, 50, 50),
        }
    for role, (r, g, b) in colors.items():
        palette.setColor(role, QColor(r, g, b))
    return palette


# ==================== UI组件 ====================


class LineNumberArea(QWidget):
    def __init__(self, text_browser):
        super().__init__(text_browser)
        self.text_browser = text_browser
        self.setFixedWidth(50)
        self.current_theme = "dark"

    def set_theme(self, theme):
        self.current_theme = theme
        self.setStyleSheet(
            f"background-color: {'#2d2d2d' if theme == 'dark' else '#e0e0e0'};"
        )
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QColor("#808080" if self.current_theme == "dark" else "#a0a0a0"))
        painter.setFont(self.text_browser.font())

        cursor = self.text_browser.cursorForPosition(QPoint(0, 0))
        block, block_number = cursor.block(), cursor.blockNumber() + 1
        fm = QFontMetrics(painter.font())
        line_height = fm.height()
        scrollbar = self.text_browser.verticalScrollBar()
        offset = scrollbar.value()
        top = (
            self.text_browser.document().documentLayout().blockBoundingRect(block).top()
            - offset
        )
        bottom = top + line_height

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0,
                    int(top),
                    self.width() - 5,
                    line_height,
                    Qt.AlignRight,
                    str(block_number),
                )
            block = block.next()
            top, bottom, block_number = bottom, bottom + line_height, block_number + 1

    def update_width(self):
        lines = self.text_browser.document().blockCount()
        self.setFixedWidth(
            max(QFontMetrics(self.text_browser.font()).width(str(lines)) + 20, 40)
        )


class CustomTextBrowser(QTextBrowser):
    text_selected = pyqtSignal(str)
    selection_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_selection = ""
        self.last_has_selection = False
        self.line_number_area = None
        self.line_number_visible = False
        self.verticalScrollBar().valueChanged.connect(self.update_line_numbers)
        self.textChanged.connect(self.update_line_numbers)

    def set_line_number_visible(self, visible):
        self.line_number_visible = visible
        if visible and not self.line_number_area:
            self.line_number_area = LineNumberArea(self)
            self.setViewportMargins(self.line_number_area.width(), 0, 0, 0)
            self.line_number_area.show()
        elif not visible and self.line_number_area:
            self.line_number_area.hide()
            self.setViewportMargins(0, 0, 0, 0)
            self.line_number_area = None
        self.update_line_numbers()

    def set_theme(self, theme):
        if self.line_number_area:
            self.line_number_area.set_theme(theme)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.line_number_area:
            cr = self.contentsRect()
            self.line_number_area.setGeometry(
                cr.left(), cr.top(), self.line_number_area.width(), cr.height()
            )

    def update_line_numbers(self):
        if self.line_number_area:
            self.line_number_area.update_width()
            self.line_number_area.update(
                0, 0, self.line_number_area.width(), self.height()
            )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            super().mouseReleaseEvent(event)
            QTimer.singleShot(50, self.process_selection)
        else:
            super().mouseReleaseEvent(event)

    def process_selection(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            if selected_text and selected_text != self.last_selection:
                self.last_selection = selected_text
                self.text_selected.emit(selected_text)
            self.last_has_selection = True
        elif self.last_has_selection:
            self.selection_cleared.emit()
            self.last_has_selection = False
            self.last_selection = ""


class LogHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_pattern, self.case_sensitive = "", False
        self.highlight_all = True
        self.current_match_start = self.current_match_end = -1

        self.highlight_format = QTextCharFormat()
        self.highlight_format.setBackground(QColor(200, 150, 0, 150))
        self.highlight_format.setForeground(QColor(255, 255, 200))

        self.current_match_format = QTextCharFormat()
        self.current_match_format.setBackground(QColor(135, 206, 250, 150))
        self.current_match_format.setForeground(QColor(255, 255, 255))

    def set_search_pattern(self, pattern, case_sensitive=False):
        self.search_pattern = str(pattern) if pattern else ""
        self.case_sensitive = case_sensitive
        self.rehighlight()

    def set_current_match(self, start, end):
        self.current_match_start, self.current_match_end = start, end
        self.rehighlight()

    def set_highlight_all(self, highlight_all):
        self.highlight_all = highlight_all
        self.rehighlight()

    def highlightBlock(self, text):
        if not self.search_pattern or not text:
            return
        try:
            block_start = self.currentBlock().position()
            pattern = (
                self.search_pattern.lower()
                if not self.case_sensitive
                else self.search_pattern
            )
            text_to_search = text.lower() if not self.case_sensitive else text
            pattern_len = len(pattern)
            index = 0
            while True:
                index = text_to_search.find(pattern, index)
                if index == -1:
                    break
                actual_start, actual_end = (
                    block_start + index,
                    block_start + index + pattern_len,
                )
                is_current_match = (
                    actual_start == self.current_match_start
                    and actual_end == self.current_match_end
                )
                if self.highlight_all or is_current_match:
                    self.setFormat(
                        index,
                        pattern_len,
                        self.current_match_format
                        if is_current_match
                        else self.highlight_format,
                    )
                index += pattern_len
        except:
            pass


class BufferSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("缓冲区设置")
        self.resize(350, 200)
        self.setup_ui()
        self.setStyleSheet(
            "QDialog { background-color: #303030; } QLabel { color: #cccccc; } QSpinBox { background-color: #252525; color: #dddddd; border: 1px solid #404040; border-radius: 3px; padding: 5px; } QPushButton { background-color: #505050; color: #dddddd; border: 1px solid #606060; border-radius: 3px; padding: 6px 12px; } QPushButton:hover { background-color: #606060; }"
        )

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.receive_buffer_spin = QSpinBox()
        self.receive_buffer_spin.setRange(1024, 10485760)
        self.receive_buffer_spin.setValue(1024 * 100)
        self.receive_buffer_spin.setSuffix(" 字节")
        form_layout.addRow("接收缓冲区大小:", self.receive_buffer_spin)

        self.send_buffer_spin = QSpinBox()
        self.send_buffer_spin.setRange(1024, 10485760)
        self.send_buffer_spin.setValue(1024 * 10)
        self.send_buffer_spin.setSuffix(" 字节")
        form_layout.addRow("发送缓冲区大小:", self.send_buffer_spin)

        self.receive_timeout_spin = QSpinBox()
        self.receive_timeout_spin.setRange(100, 10000)
        self.receive_timeout_spin.setValue(1000)
        self.receive_timeout_spin.setSuffix(" ms")
        form_layout.addRow("接收超时时间:", self.receive_timeout_spin)

        self.send_timeout_spin = QSpinBox()
        self.send_timeout_spin.setRange(100, 10000)
        self.send_timeout_spin.setValue(1000)
        self.send_timeout_spin.setSuffix(" ms")
        form_layout.addRow("发送超时时间:", self.send_timeout_spin)

        layout.addLayout(form_layout)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_settings(self):
        return {
            "receive_buffer": self.receive_buffer_spin.value(),
            "send_buffer": self.send_buffer_spin.value(),
            "receive_timeout": self.receive_timeout_spin.value() / 1000.0,
            "send_timeout": self.send_timeout_spin.value() / 1000.0,
        }

    def set_settings(self, settings):
        if "receive_buffer" in settings:
            self.receive_buffer_spin.setValue(settings["receive_buffer"])
        if "send_buffer" in settings:
            self.send_buffer_spin.setValue(settings["send_buffer"])
        if "receive_timeout" in settings:
            self.receive_timeout_spin.setValue(int(settings["receive_timeout"] * 1000))
        if "send_timeout" in settings:
            self.send_timeout_spin.setValue(int(settings["send_timeout"] * 1000))


# ==================== 串口通信线程 ====================


class SerialThread(QThread):
    data_received = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)

    def __init__(self, port, baudrate, bytesize, stopbits, parity, timeout=0.1):
        super().__init__()
        self.port, self.baudrate, self.bytesize = port, baudrate, bytesize
        self.stopbits, self.parity, self.timeout = stopbits, parity, timeout
        self.serial_port, self.running = None, False
        self.mutex = QMutex()

    def run(self):
        try:
            with QMutexLocker(self.mutex):
                if self.running:
                    return
                self.running = True

            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                stopbits=self.stopbits,
                parity=self.parity,
                timeout=self.timeout,
            )
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()

            while self.running:
                try:
                    if self.serial_port and self.serial_port.is_open:
                        if self.serial_port.in_waiting > 0:
                            data = self.serial_port.read(self.serial_port.in_waiting)
                            if data:
                                self.data_received.emit(data)
                        else:
                            time.sleep(0.001)
                    else:
                        break
                except Exception as e:
                    self.error_occurred.emit(f"读取数据错误: {str(e)}")
                    break
        except Exception as e:
            self.error_occurred.emit(f"打开串口错误: {str(e)}")
        finally:
            self.close_serial()

    def close_serial(self):
        with QMutexLocker(self.mutex):
            self.running = False
            if self.serial_port and self.serial_port.is_open:
                try:
                    self.serial_port.close()
                except:
                    pass
                finally:
                    self.serial_port = None

    def write_data(self, data):
        with QMutexLocker(self.mutex):
            if self.serial_port and self.serial_port.is_open:
                try:
                    self.serial_port.write(data)
                    return True
                except Exception as e:
                    self.error_occurred.emit(f"发送数据错误: {str(e)}")
                    return False
            return False

    def stop(self):
        self.running = False
        self.wait()


# ==================== 主窗口 ====================


class SerialTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Log tool v{VERSION}")
        
        # 获取屏幕可用大小，拉伸到满屏但不是最大化
        screen = QApplication.desktop().availableGeometry()
        self.setGeometry(screen)
        
        # 确保窗口不是最大化状态
        self.showNormal()

        self.serial_thread, self.reconnect_timer, self.reconnect_count = (
            None,
            QTimer(),
            0,
        )
        self.reconnect_timer.timeout.connect(self.auto_reconnect)
        self.max_reconnect = 9999  # 增加最大重连次数
        self.reconnect_dialog = None  # 重连弹窗
        self.receive_count = self.send_count = 0
        self.receive_buffer = self.send_buffer = bytearray()
        self.repeat_timer = QTimer()
        self.repeat_timer.timeout.connect(self.send_data)
        self.buffer_settings = {
            "receive_buffer": DEFAULT_RECEIVE_BUFFER,
            "send_buffer": DEFAULT_SEND_BUFFER,
            "receive_timeout": DEFAULT_RECEIVE_TIMEOUT,
            "send_timeout": DEFAULT_SEND_TIMEOUT,
        }
        self.config_visible = True
        self.font_name, self.font_size = "Consolas", 12
        self.current_theme = "dark"
        self.search_text, self.search_results = "", []
        self.current_search_index, self.first_click = 0, True

        self.setup_icon()
        self.setup_ui()
        self.setup_menu()
        self.refresh_ports()
        self.port_refresh_timer = QTimer()
        self.port_refresh_timer.timeout.connect(self.refresh_ports)
        self.port_refresh_timer.start(2000)
        
        # 延迟自动连接串口
        QTimer.singleShot(500, self.auto_connect_serial)

    def setup_icon(self):
        for icon_path in [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "serial_port.ico"),
            os.path.join(sys._MEIPASS, "serial_port.ico")
            if hasattr(sys, "_MEIPASS")
            else None,
            os.path.join(os.path.dirname(sys.executable), "serial_port.ico")
            if getattr(sys, "frozen", False)
            else None,
        ]:
            if icon_path and os.path.exists(icon_path):
                try:
                    icon = QIcon(icon_path)
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                        return
                except:
                    pass

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.apply_theme(self.current_theme)
        self.setup_toolbar()
        self.receive_frame = self.create_receive_frame()
        self.main_layout.addWidget(self.receive_frame, 1)
        self.config_frame = self.create_config_frame()
        self.main_layout.addWidget(self.config_frame)

    def setup_toolbar(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)

        self.toggle_config_action = QAction(
            "显示配置",
            self,
            checkable=True,
            checked=True,
            triggered=self.toggle_config_area,
        )
        toolbar.addAction(self.toggle_config_action)
        toolbar.addSeparator()

        self.connect_action = QAction("连接", self, triggered=self.toggle_connection)
        toolbar.addAction(self.connect_action)
        toolbar.addSeparator()

        toolbar.addAction(QAction("清除接收", self, triggered=self.clear_receive))
        toolbar.addSeparator()
        toolbar.addAction(QAction("保存接收", self, triggered=self.save_receive_data))

    def apply_theme(self, theme):
        self.current_theme = theme
        QApplication.setPalette(create_palette(theme))
        self.setStyleSheet(DARK_THEME if theme == "dark" else LIGHT_THEME)
        self.update_stats_labels_color()
        self.apply_font_settings()

    def update_stats_labels_color(self):
        if not hasattr(self, "buffer_stats_label"):
            return
        color = "#a0a0c0" if self.current_theme == "dark" else "#666666"
        green = "#a0c0a0" if self.current_theme == "dark" else color
        self.buffer_stats_label.setStyleSheet(f"color: {color};")
        self.status_stats_label.setStyleSheet(f"color: {color}; font-weight: 500;")
        self.receive_stats_label.setStyleSheet(f"color: {green};")
        self.send_stats_label.setStyleSheet(f"color: {green};")
        self.search_result_label.setStyleSheet(
            f"color: {green}; min-width: 120px; font-weight: 500;"
        )
        search_label = self.findChild(QLabel, "search_label")
        if search_label:
            search_label.setStyleSheet(
                f"color: {'#aaaaaa' if self.current_theme == 'dark' else '#555555'};"
            )

    def apply_font_settings(self):
        if not hasattr(self, "receive_text"):
            return
        font = QFont(self.font_name, self.font_size)
        if not font.exactMatch() and font.family():
            font = QFont("Consolas", self.font_size)
        self.receive_text.setFont(font)
        self.receive_text.setStyleSheet(
            TERMINAL_STYLES[self.current_theme].replace(
                "font-size: 12pt;", f"font-size: {self.font_size}pt;"
            )
        )
        self.receive_text.update_line_numbers()

    def create_receive_frame(self):
        receive_frame = QFrame()
        receive_frame.setFrameStyle(QFrame.NoFrame)
        layout = QVBoxLayout(receive_frame)
        layout.setSpacing(5)
        layout.addWidget(self.create_control_frame())
        self.receive_text = CustomTextBrowser()
        self.receive_text.setFont(QFont(self.font_name, self.font_size))
        self.receive_text.setLineWrapMode(QTextEdit.WidgetWidth)
        self.highlighter = LogHighlighter(self.receive_text.document())
        layout.addWidget(self.receive_text, 1)
        return receive_frame

    def create_control_frame(self):
        control_frame = QFrame()
        bg = "#303030" if self.current_theme == "dark" else "#f0f0f0"
        border = "#404040" if self.current_theme == "dark" else "#cccccc"
        control_frame.setStyleSheet(
            f"QFrame {{ background-color: {bg}; border: 1px solid {border}; border-radius: 4px; padding: 5px; }}"
        )

        layout = QHBoxLayout(control_frame)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        options_layout = QHBoxLayout()
        options_layout.setSpacing(10)
        self.timestamp_cb = QCheckBox("时间戳")
        self.hex_display_cb = QCheckBox("十六进制")
        self.pause_display_cb = QCheckBox("暂停显示")
        self.line_numbers_cb = QCheckBox("显示行号")
        self.line_numbers_cb.stateChanged.connect(self.on_line_numbers_changed)
        self.auto_scroll_cb = QCheckBox("自动滚屏")
        self.auto_scroll_cb.setChecked(True)
        for cb in [
            self.timestamp_cb,
            self.hex_display_cb,
            self.pause_display_cb,
            self.line_numbers_cb,
            self.auto_scroll_cb,
        ]:
            options_layout.addWidget(cb)
        layout.addLayout(options_layout)

        layout.addLayout(self.create_search_layout())
        layout.addLayout(self.create_stats_layout())
        return control_frame

    def create_search_layout(self):
        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)
        search_label = QLabel("查找:")
        search_label.setObjectName("search_label")
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索内容...")
        self.search_input.setMaximumWidth(200)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.returnPressed.connect(self.find_next)
        search_layout.addWidget(self.search_input)

        self.search_result_label = QLabel("")
        self.search_result_label.setStyleSheet(
            "color: #a0c0a0; min-width: 120px; font-weight: 500;"
        )
        search_layout.addWidget(self.search_result_label)

        self.case_sensitive_cb = QCheckBox("区分大小写")
        self.case_sensitive_cb.stateChanged.connect(self.on_case_sensitive_changed)
        search_layout.addWidget(self.case_sensitive_cb)

        self.find_prev_btn = QPushButton("上")
        self.find_prev_btn.setFixedWidth(40)
        self.find_prev_btn.clicked.connect(self.find_previous)
        self.find_prev_btn.setEnabled(False)
        search_layout.addWidget(self.find_prev_btn)

        self.find_next_btn = QPushButton("下")
        self.find_next_btn.setFixedWidth(40)
        self.find_next_btn.clicked.connect(self.find_next)
        self.find_next_btn.setEnabled(False)
        search_layout.addWidget(self.find_next_btn)

        search_layout.addStretch()
        return search_layout

    def create_stats_layout(self):
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        self.receive_stats_label = QLabel("接收: 0 字节")
        self.send_stats_label = QLabel("发送: 0 字节")
        self.buffer_stats_label = QLabel("缓冲区: 0/1048576 字节")
        self.status_stats_label = QLabel("状态: 就绪")

        for label in [self.receive_stats_label, self.send_stats_label]:
            label.setStyleSheet("color: #a0c0a0;")
        for label in [self.buffer_stats_label, self.status_stats_label]:
            label.setStyleSheet("color: #a0a0c0; font-weight: 500;")

        for lbl in [
            self.receive_stats_label,
            self.send_stats_label,
            self.buffer_stats_label,
            self.status_stats_label,
        ]:
            stats_layout.addWidget(lbl)
        stats_layout.addStretch()
        return stats_layout

    def create_config_frame(self):
        config_frame = QFrame()
        config_frame.setFrameStyle(QFrame.NoFrame)
        layout = QVBoxLayout(config_frame)
        layout.setSpacing(5)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.create_config_group())
        splitter.addWidget(self.create_send_group())
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)
        return config_frame

    def create_config_group(self):
        config_group = QGroupBox("")
        layout = QGridLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 15, 10, 10)

        layout.addWidget(QLabel("端口:"), 0, 0)
        self.port_combo = QComboBox()
        layout.addWidget(self.port_combo, 0, 1, 1, 2)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        layout.addWidget(self.refresh_btn, 0, 3)

        layout.addWidget(QLabel("波特率:"), 1, 0)
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(BAUDRATE_OPTIONS)
        self.baudrate_combo.setCurrentText("115200")
        self.baudrate_combo.currentTextChanged.connect(self.on_baudrate_changed)
        layout.addWidget(self.baudrate_combo, 1, 1)

        self.custom_baudrate_edit = QLineEdit()
        self.custom_baudrate_edit.setPlaceholderText("自定义波特率")
        self.custom_baudrate_edit.setVisible(False)
        layout.addWidget(self.custom_baudrate_edit, 1, 2, 1, 2)

        param_layout = QHBoxLayout()
        param_layout.setSpacing(10)
        param_layout.addWidget(QLabel("数据位:"))
        self.databits_combo = QComboBox()
        self.databits_combo.addItems(DATABITS_OPTIONS)
        self.databits_combo.setCurrentText("8")
        param_layout.addWidget(self.databits_combo)

        param_layout.addWidget(QLabel("停止位:"))
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(STOPBITS_OPTIONS)
        self.stopbits_combo.setCurrentText("1")
        param_layout.addWidget(self.stopbits_combo)

        param_layout.addWidget(QLabel("校验:"))
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(PARITY_OPTIONS)
        self.parity_combo.setCurrentText("无")
        param_layout.addWidget(self.parity_combo)
        param_layout.addStretch()
        layout.addLayout(param_layout, 2, 0, 1, 4)

        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_btn, 3, 0, 1, 4)
        config_group.setLayout(layout)
        return config_group

    def create_send_group(self):
        send_group = QGroupBox("")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 15, 10, 10)

        self.send_text = QTextEdit()
        self.send_text.setPlaceholderText("输入要发送的数据...")
        layout.addWidget(self.send_text, 2)

        options_layout = QGridLayout()
        options_layout.setSpacing(10)

        self.send_btn = QPushButton("发送")
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self.send_data)
        options_layout.addWidget(self.send_btn, 0, 0, 1, 3)

        row1_layout = QHBoxLayout()
        self.send_newline_cb = QCheckBox("发送新行")
        self.hex_send_cb = QCheckBox("十六进制")
        row1_layout.addWidget(self.send_newline_cb)
        row1_layout.addWidget(self.hex_send_cb)
        row1_layout.addStretch()
        options_layout.addLayout(row1_layout, 1, 0, 1, 3)

        row2_layout = QHBoxLayout()
        self.repeat_send_cb = QCheckBox("重复发送")
        self.repeat_send_cb.stateChanged.connect(self.on_repeat_send_changed)
        row2_layout.addWidget(self.repeat_send_cb)
        row2_layout.addWidget(QLabel("间隔:"))
        self.repeat_interval_spin = QSpinBox()
        self.repeat_interval_spin.setRange(100, 10000)
        self.repeat_interval_spin.setValue(1000)
        self.repeat_interval_spin.setSuffix(" ms")
        self.repeat_interval_spin.setEnabled(False)
        row2_layout.addWidget(self.repeat_interval_spin)
        row2_layout.addStretch()
        options_layout.addLayout(row2_layout, 2, 0, 1, 3)

        layout.addLayout(options_layout, 1)
        send_group.setLayout(layout)
        return send_group

    def setup_menu(self):
        menubar = self.menuBar()
        self.theme_actions, self.font_name_actions, self.font_actions = [], [], []

        view_menu = menubar.addMenu("视图")
        theme_menu = view_menu.addMenu("主题")
        for theme_id, theme_name in [("dark", "暗黑主题"), ("light", "浅色主题")]:
            a = QAction(
                theme_name,
                self,
                checkable=True,
                checked=theme_id == self.current_theme,
                triggered=self.on_theme_changed,
            )
            a.setData(theme_id)
            theme_menu.addAction(a)
            self.theme_actions.append(a)

        font_menu = view_menu.addMenu("字体")
        font_name_menu = font_menu.addMenu("字体名称")
        for font in FONT_OPTIONS:
            a = QAction(
                font,
                self,
                checkable=True,
                checked=font == self.font_name,
                triggered=self.on_font_name_changed,
            )
            a.setData(font)
            font_name_menu.addAction(a)
            self.font_name_actions.append(a)

        font_size_menu = font_menu.addMenu("字体大小")
        for size in FONT_SIZES:
            a = QAction(
                f"{size} pt",
                self,
                checkable=True,
                checked=size == self.font_size,
                triggered=self.on_font_size_changed,
            )
            a.setData(size)
            font_size_menu.addAction(a)
            self.font_actions.append(a)

        edit_menu = menubar.addMenu("编辑")
        edit_menu.addAction(
            QAction(
                "查找",
                self,
                shortcut="Ctrl+F",
                triggered=lambda: (
                    self.search_input.setFocus(),
                    self.search_input.selectAll(),
                ),
            )
        )
        edit_menu.addAction(
            QAction("查找下一个", self, shortcut="F3", triggered=self.find_next)
        )
        edit_menu.addAction(
            QAction(
                "查找上一个", self, shortcut="Shift+F3", triggered=self.find_previous
            )
        )
        edit_menu.addSeparator()
        edit_menu.addAction(QAction("清除搜索", self, triggered=self.clear_search))

        menubar.addMenu("设置").addAction(
            QAction("缓冲区设置", self, triggered=self.show_buffer_settings)
        )
        menubar.addMenu("帮助").addAction(
            QAction("关于", self, triggered=self.show_about)
        )

    def toggle_config_area(self):
        self.config_visible = not self.config_visible
        if self.config_visible:
            self.config_frame.show()
            self.toggle_config_action.setText("隐藏配置")
            self.toggle_config_action.setChecked(True)
        else:
            self.config_frame.hide()
            self.toggle_config_action.setText("显示配置")
            self.toggle_config_action.setChecked(False)

    def on_theme_changed(self):
        action = self.sender()
        if action and action.isChecked():
            for act in self.theme_actions:
                act.setChecked(act == action)
            new_theme = action.data()
            self.apply_theme(new_theme)
            self.receive_text.set_theme(new_theme)
            bg = "#303030" if new_theme == "dark" else "#f0f0f0"
            border = "#404040" if new_theme == "dark" else "#cccccc"
            self.receive_frame.findChild(QFrame).setStyleSheet(
                f"QFrame {{ background-color: {bg}; border: 1px solid {border}; border-radius: 4px; padding: 5px; }}"
            )

    def on_font_name_changed(self):
        action = self.sender()
        if action and action.isChecked():
            for act in self.font_name_actions:
                act.setChecked(act == action)
            self.font_name = action.data()
            self.apply_font_settings()

    def on_font_size_changed(self):
        action = self.sender()
        if action and action.isChecked():
            for act in self.font_actions:
                act.setChecked(act == action)
            self.font_size = action.data()
            self.apply_font_settings()

    def on_line_numbers_changed(self, state):
        self.receive_text.set_line_number_visible(state == Qt.Checked)

    def on_baudrate_changed(self, text):
        self.custom_baudrate_edit.setVisible(text == "自定义")

    def on_repeat_send_changed(self, state):
        enabled = state == Qt.Checked
        self.repeat_interval_spin.setEnabled(enabled)
        if enabled:
            self.repeat_timer.start(self.repeat_interval_spin.value())
        else:
            self.repeat_timer.stop()

    def on_search_text_changed(self, text):
        try:
            scrollbar = self.receive_text.verticalScrollBar()
            scroll_position = scrollbar.value() if scrollbar else 0
            self.search_text = str(text).strip() if text else ""
            if self.search_text:
                self.find_next_btn.setEnabled(True)
                self.find_prev_btn.setEnabled(True)
                self.highlighter.set_highlight_all(True)
                self.highlighter.set_search_pattern(
                    self.search_text, self.case_sensitive_cb.isChecked()
                )
                self.current_search_index = 0
                self.first_click = True
                self.find_all_matches()
                if scrollbar:
                    scrollbar.setValue(scroll_position)
            else:
                self.find_next_btn.setEnabled(False)
                self.find_prev_btn.setEnabled(False)
                self.highlighter.set_search_pattern("")
                self.search_result_label.setText("")
        except:
            self.highlighter.set_search_pattern("")

    def on_case_sensitive_changed(self, state):
        if self.search_text:
            scrollbar = self.receive_text.verticalScrollBar()
            scroll_position = scrollbar.value() if scrollbar else 0
            self.highlighter.set_highlight_all(True)
            self.highlighter.set_search_pattern(self.search_text, state == Qt.Checked)
            self.current_search_index = 0
            self.find_all_matches()
            if scrollbar:
                scrollbar.setValue(scroll_position)

    def find_all_matches(self):
        if not self.search_text or not self.receive_text.document():
            self.search_results = []
            self.search_result_label.setText("未找到")
            return
        self.search_results = []
        document = self.receive_text.document()
        flags = (
            QTextDocument.FindCaseSensitively
            if self.case_sensitive_cb.isChecked()
            else QTextDocument.FindFlag(0)
        )
        cursor = QTextCursor(document)
        cursor.movePosition(QTextCursor.Start)
        while True:
            cursor = document.find(self.search_text, cursor, flags)
            if cursor.isNull():
                break
            self.search_results.append(
                {"start": cursor.selectionStart(), "end": cursor.selectionEnd()}
            )
        self.search_result_label.setText(
            f"找到 {len(self.search_results)} 个结果"
            if self.search_results
            else "未找到"
        )

    def find_next(self):
        if not self.search_text or not self.search_results:
            return
        cursor = self.receive_text.textCursor()
        current_pos = cursor.position()
        if self.first_click or not cursor.hasSelection():
            self.current_search_index = next(
                (
                    i
                    for i, m in enumerate(self.search_results)
                    if m["start"] > current_pos
                ),
                0,
            )
        else:
            current_selection_start = cursor.selectionStart()
            for i, m in enumerate(self.search_results):
                if m["start"] == current_selection_start:
                    self.current_search_index = i
                    break
            self.current_search_index = (self.current_search_index + 1) % len(
                self.search_results
            )
        self.first_click = False
        self.jump_to_match(self.current_search_index)

    def find_previous(self):
        if not self.search_text or not self.search_results:
            return
        cursor = self.receive_text.textCursor()
        current_pos = cursor.position()
        if self.first_click or not cursor.hasSelection():
            self.current_search_index = next(
                (
                    i
                    for i in range(len(self.search_results) - 1, -1, -1)
                    if self.search_results[i]["start"] < current_pos
                ),
                len(self.search_results) - 1,
            )
        else:
            current_selection_start = cursor.selectionStart()
            for i, m in enumerate(self.search_results):
                if m["start"] == current_selection_start:
                    self.current_search_index = i
                    break
            self.current_search_index = (
                self.current_search_index - 1 + len(self.search_results)
            ) % len(self.search_results)
        self.first_click = False
        self.jump_to_match(self.current_search_index)

    def jump_to_match(self, index):
        if not self.search_results or index < 0 or index >= len(self.search_results):
            return
        match = self.search_results[index]
        cursor = QTextCursor(self.receive_text.document())
        cursor.setPosition(match["start"])
        cursor.setPosition(match["end"], QTextCursor.KeepAnchor)
        self.receive_text.setTextCursor(cursor)
        self.receive_text.ensureCursorVisible()
        self.highlighter.set_highlight_all(True)
        self.highlighter.set_current_match(match["start"], match["end"])
        self.search_result_label.setText(f"{index + 1}/{len(self.search_results)}")

    def clear_search(self):
        self.search_input.clear()
        self.highlighter.set_search_pattern("")
        self.highlighter.set_highlight_all(True)
        self.search_result_label.setText("")
        self.search_results = []
        self.current_search_index = 0
        self.first_click = True

    def refresh_ports(self):
        current_port = self.port_combo.currentText()
        self.port_combo.clear()
        for port in serial.tools.list_ports.comports():
            desc = port.description if port.description else "未知设备"
            self.port_combo.addItem(f"{port.device} - {desc}", port.device)
        if current_port:
            index = self.port_combo.findText(current_port, Qt.MatchStartsWith)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)

    def get_baudrate(self):
        if self.baudrate_combo.currentText() == "自定义":
            try:
                return int(self.custom_baudrate_edit.text())
            except:
                return DEFAULT_BAUDRATE
        else:
            try:
                return int(self.baudrate_combo.currentText())
            except:
                return DEFAULT_BAUDRATE

    def get_serial_params(self):
        baudrate = self.get_baudrate()
        databits_map = {
            "5": serial.FIVEBITS,
            "6": serial.SIXBITS,
            "7": serial.SEVENBITS,
            "8": serial.EIGHTBITS,
        }
        stopbits_map = {
            "1": serial.STOPBITS_ONE,
            "1.5": serial.STOPBITS_ONE_POINT_FIVE,
            "2": serial.STOPBITS_TWO,
        }
        parity_map = {
            "无": serial.PARITY_NONE,
            "奇校验": serial.PARITY_ODD,
            "偶校验": serial.PARITY_EVEN,
        }
        return (
            baudrate,
            databits_map.get(self.databits_combo.currentText(), serial.EIGHTBITS),
            stopbits_map.get(self.stopbits_combo.currentText(), serial.STOPBITS_ONE),
            parity_map.get(self.parity_combo.currentText(), serial.PARITY_NONE),
        )

    def toggle_connection(self):
        self.disconnect_serial() if self.serial_thread and self.serial_thread.isRunning() else self.connect_serial()

    def connect_serial(self):
        if self.port_combo.count() == 0:
            QMessageBox.warning(self, "警告", "没有找到可用串口")
            return
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "警告", "请选择串口")
            return
        try:
            baudrate, bytesize, stopbits, parity = self.get_serial_params()
            timeout = self.buffer_settings.get("receive_timeout", 1.0)
            self.serial_thread = SerialThread(
                port, baudrate, bytesize, stopbits, parity, timeout
            )
            self.serial_thread.data_received.connect(self.on_data_received)
            self.serial_thread.error_occurred.connect(self.on_serial_error)
            self.serial_thread.start()
            self.connect_btn.setText("断开")
            self.connect_action.setText("断开")
            self.send_btn.setEnabled(True)
            self.status_stats_label.setText(f"已连接到 {port}")
            self.reconnect_count = 0
            # 连接成功，关闭重连弹窗
            if self.reconnect_dialog:
                self.reconnect_dialog.close()
                self.reconnect_dialog = None
        except Exception as e:
            QMessageBox.critical(self, "连接错误", f"无法连接到串口: {str(e)}")
            self.status_stats_label.setText("连接失败")

    def disconnect_serial(self):
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread = None
        if self.repeat_timer.isActive():
            self.repeat_timer.stop()
        self.connect_btn.setText("连接")
        self.connect_action.setText("连接")
        self.send_btn.setEnabled(False)
        self.status_stats_label.setText("已断开连接")
        # 断开连接时关闭重连弹窗
        if self.reconnect_dialog:
            self.reconnect_dialog.close()
            self.reconnect_dialog = None

    def on_data_received(self, data):
        if self.pause_display_cb.isChecked():
            return
        max_buffer_size = self.buffer_settings.get(
            "receive_buffer", DEFAULT_RECEIVE_BUFFER
        )
        if len(self.receive_buffer) + len(data) > max_buffer_size:
            discard_size = len(self.receive_buffer) + len(data) - max_buffer_size
            self.receive_buffer = (
                self.receive_buffer[discard_size:]
                if discard_size < len(self.receive_buffer)
                else bytearray()
            )

        self.receive_buffer.extend(data)
        self.receive_count += len(data)
        self.receive_stats_label.setText(f"接收: {self.receive_count} 字节")
        buffer_bytes = len(self.receive_buffer)
        self.buffer_stats_label.setText(
            f"缓冲区: {buffer_bytes}/{max_buffer_size} 字节"
        )

        display_text = (
            " ".join(f"{b:02X}" for b in data)
            if self.hex_display_cb.isChecked()
            else data.decode("utf-8", errors="replace")
            if self.hex_display_cb.isChecked() is False
            else data.hex(" ")
        )
        if self.timestamp_cb.isChecked():
            display_text = (
                datetime.now().strftime("[%H:%M:%S.%f")[:-3] + "] " + display_text
            )

        scrollbar = self.receive_text.verticalScrollBar()
        scroll_position = scrollbar.value() if scrollbar else 0
        cursor = self.receive_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(display_text)

        if self.search_text:
            try:
                self.highlighter.set_search_pattern(
                    self.search_text, self.case_sensitive_cb.isChecked()
                )
            except:
                pass
        if scrollbar:
            scrollbar.setValue(scroll_position)
        if self.auto_scroll_cb.isChecked():
            cursor = self.receive_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.receive_text.setTextCursor(cursor)

    def on_serial_error(self, error_msg):
        # 先断开连接，确保状态正确更新
        self.disconnect_serial()
        
        # 区分端口被占用和串口不存在的情况
        if not self.reconnect_dialog:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
            self.reconnect_dialog = QDialog(self)
            
            # 判断错误类型
            if "PermissionError" in error_msg or "access denied" in error_msg.lower() or "could not open port" in error_msg.lower():
                # 端口被占用
                self.reconnect_dialog.setWindowTitle("端口被占用")
                error_text = "端口被占用，无法连接\n\n请检查后点击重连"
            else:
                # 串口不存在或其他错误
                self.reconnect_dialog.setWindowTitle("无可用串口")
                error_text = "串口不存在或已拔出\n\n请检查后点击重连"
            
            self.reconnect_dialog.setWindowModality(Qt.WindowModal)
            self.reconnect_dialog.setMinimumWidth(280)
            
            layout = QVBoxLayout(self.reconnect_dialog)
            layout.setSpacing(10)
            
            error_label = QLabel(error_text)
            error_label.setWordWrap(True)
            error_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(error_label)
            
            reconnect_btn = QPushButton("重连")
            reconnect_btn.clicked.connect(self.on_manual_reconnect)
            layout.addWidget(reconnect_btn)
            
            self.reconnect_dialog.show()

    def auto_reconnect(self):
        if self.serial_thread and self.serial_thread.isRunning():
            return
        self.disconnect_serial()
        time.sleep(0.5)
        self.connect_serial()

    def on_manual_reconnect(self):
        """用户点击重连按钮"""
        if self.reconnect_dialog:
            self.reconnect_dialog.close()
            self.reconnect_dialog = None
        self.disconnect_serial()
        time.sleep(0.5)
        self.connect_serial()

    def auto_connect_serial(self):
        """应用启动时自动连接串口"""
        # 检查是否有可用串口
        if self.port_combo.count() == 0:
            QMessageBox.warning(self, "无可用串口", "未检测到可用串口设备，请检查连接后手动刷新。")
            return
        
        # 尝试连接第一个可用串口
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "连接失败", "无法获取串口信息，请手动选择串口并连接。")
            return
        
        try:
            baudrate, bytesize, stopbits, parity = self.get_serial_params()
            timeout = self.buffer_settings.get("receive_timeout", 1.0)
            self.serial_thread = SerialThread(
                port, baudrate, bytesize, stopbits, parity, timeout
            )
            self.serial_thread.data_received.connect(self.on_data_received)
            self.serial_thread.error_occurred.connect(self.on_serial_error)
            self.serial_thread.start()
            self.connect_btn.setText("断开")
            self.connect_action.setText("断开")
            self.send_btn.setEnabled(True)
            self.status_stats_label.setText(f"已连接到 {port}")
            self.reconnect_count = 0
            # 连接成功，关闭重连弹窗
            if self.reconnect_dialog:
                self.reconnect_dialog.close()
                self.reconnect_dialog = None
        except Exception as e:
            # 显示重连弹窗，等待用户手动重连
            if not self.reconnect_dialog:
                from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
                self.reconnect_dialog = QDialog(self)
                
                # 判断错误类型
                error_msg = str(e)
                if "PermissionError" in error_msg or "access denied" in error_msg.lower() or "could not open port" in error_msg.lower():
                    # 端口被占用
                    self.reconnect_dialog.setWindowTitle("端口被占用")
                    error_text = "端口被占用，无法连接\n\n请检查后点击重连"
                else:
                    # 串口不存在或其他错误
                    self.reconnect_dialog.setWindowTitle("无可用串口")
                    error_text = "串口不存在或已拔出\n\n请检查后点击重连"
                
                self.reconnect_dialog.setWindowModality(Qt.WindowModal)
                self.reconnect_dialog.setMinimumWidth(280)
                
                layout = QVBoxLayout(self.reconnect_dialog)
                layout.setSpacing(10)
                
                error_label = QLabel(error_text)
                error_label.setWordWrap(True)
                error_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(error_label)
                
                reconnect_btn = QPushButton("重连")
                reconnect_btn.clicked.connect(self.on_manual_reconnect)
                layout.addWidget(reconnect_btn)
                
                self.reconnect_dialog.show()



    def send_data(self):
        if not self.serial_thread or not self.serial_thread.isRunning():
            QMessageBox.warning(self, "警告", "串口未连接")
            return
        text = self.send_text.toPlainText()
        if not text:
            return
        max_buffer_size = self.buffer_settings.get("send_buffer", DEFAULT_SEND_BUFFER)
        if len(self.send_buffer) + len(text) > max_buffer_size:
            QMessageBox.warning(self, "警告", "发送缓冲区已满")
            return
        if self.hex_send_cb.isChecked():
            try:
                hex_str = text.replace(" ", "").replace("\n", "").replace("\r", "")
                if len(hex_str) % 2 != 0:
                    raise ValueError("十六进制数据长度错误")
                data = bytes.fromhex(hex_str)
            except Exception as e:
                QMessageBox.warning(self, "格式错误", f"无效的十六进制数据: {str(e)}")
                return
        else:
            data = text.encode("utf-8")
        self.send_buffer.extend(data)
        if self.send_newline_cb.isChecked():
            data += b"\r\n"
        if self.serial_thread.write_data(data):
            self.send_count += len(data)
            self.send_stats_label.setText(f"发送: {self.send_count} 字节")

    def clear_receive(self):
        self.receive_text.clear()
        self.receive_count = 0
        self.receive_buffer = bytearray()
        self.receive_stats_label.setText("接收: 0 字节")
        max_buffer_size = self.buffer_settings.get(
            "receive_buffer", DEFAULT_RECEIVE_BUFFER
        )
        self.buffer_stats_label.setText(f"缓冲区: 0/{max_buffer_size} 字节")
        self.receive_text.update_line_numbers()

    def save_receive_data(self):
        if not self.receive_text.toPlainText():
            QMessageBox.warning(self, "警告", "没有接收数据可保存")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存接收数据", "", "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(self.receive_text.toPlainText())
                QMessageBox.information(self, "成功", f"接收数据已保存到: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")

    def show_buffer_settings(self):
        dialog = BufferSettingsDialog(self)
        dialog.set_settings(self.buffer_settings)
        if dialog.exec_() == QDialog.Accepted:
            self.buffer_settings.update(dialog.get_settings())
            max_buffer_size = self.buffer_settings.get(
                "receive_buffer", DEFAULT_RECEIVE_BUFFER
            )
            self.buffer_stats_label.setText(
                f"缓冲区: {len(self.receive_buffer)}/{max_buffer_size} 字节"
            )
            QMessageBox.information(self, "成功", "缓冲区设置已更新")

    def show_about(self):
        about_text = f"""
        <h3 style="color: #cccccc;">{APP_NAME} v{VERSION}</h3>
        <p style="color: #aaaaaa;">轻量级串口调试助手，支持缓冲区设置和界面控制。</p>
        <p style="color: #cccccc;"><b>主要功能:</b></p>
        <ul style="color: #aaaaaa;">
            <li>自动检测串口，实时刷新</li>
            <li>多种波特率选择（支持自定义）</li>
            <li>十六进制/文本收发模式</li>
            <li>时间戳显示（默认关闭）</li>
            <li>数据保存功能</li>
            <li>防死机机制，自动重连</li>
            <li>缓冲区大小设置（默认1MB/1MB）</li>
            <li>配置区域显示/隐藏</li>
            <li>图标支持（支持.ico文件）</li>
            <li>字体大小调节（8-24pt，默认12pt）</li>
            <li>日志查找和高亮功能</li>
            <li>多种字体选择（Consolas、Monaco等）</li>
            <li>主题切换（暗黑主题/浅色主题）</li>
        </ul>
        <p style="color: #cccccc;"><b>搜索功能:</b></p>
        <ul style="color: #aaaaaa;">
            <li>在接收控制栏添加搜索框</li>
            <li>支持查找上一个/下一个（F3/Shift+F3）</li>
            <li>支持区分大小写搜索</li>
            <li>支持高亮所有匹配项</li>
            <li>选中文本自动填充到搜索框</li>
            <li>显示搜索结果数量</li>
        </ul>
        <p style="color: #cccccc;"><b>主题切换:</b></p>
        <ul style="color: #aaaaaa;">
            <li>暗黑主题（默认）</li>
            <li>浅色主题</li>
            <li>主题切换实时生效</li>
        </ul>
        <p style="color: #888888;">版本: {VERSION}</p>
        """
        msg_box = QMessageBox()
        msg_box.setWindowTitle("关于")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(about_text)
        msg_box.setStyleSheet(
            "QMessageBox { background-color: #303030; color: #cccccc; }"
        )
        msg_box.exec_()

    def closeEvent(self, event):
        if self.serial_thread and self.serial_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "确认退出",
                "串口正在连接，确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.disconnect_serial()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# ==================== 程序入口 ====================


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    icon_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "serial_port.ico"
    )
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    window = SerialTool()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
