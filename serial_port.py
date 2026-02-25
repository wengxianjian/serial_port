# -*- coding: utf-8 -*-
"""
串口工具(精简版) v1.2
功能：
1. 串口连接/断开控制
2. 可配置的波特率
3. 时间戳显示
4. 数据收发
5. 日志保存
6. 防死机机制
7. 缓冲区大小设置
8. 配置区域显示/隐藏
9. 图标支持
10. 字体大小选择
11. 日志查找和高亮功能
"""

import sys
import os
import time
import threading
import queue
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QLabel, QLineEdit, 
                            QComboBox, QPushButton, QGroupBox, QMessageBox,
                            QFileDialog, QTextEdit, QCheckBox, QSpinBox,
                            QMenu, QAction, QTextBrowser, QSplitter, QToolBar,
                            QFrame, QSizePolicy, QDialog, QDialogButtonBox,
                            QFormLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QMutex, QMutexLocker, QSize, QRegularExpression, QPoint
from PyQt5.QtGui import (QFont, QPalette, QColor, QTextCursor, QIcon, QFontDatabase,
                        QTextCharFormat, QSyntaxHighlighter, QBrush, QTextDocument,
                        QPainter, QFontMetrics)


import serial
import serial.tools.list_ports


class LineNumberArea(QWidget):
    """行号显示区域"""
    def __init__(self, text_browser):
        super().__init__(text_browser)
        self.text_browser = text_browser
        self.setFixedWidth(50)  # 默认行号宽度
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#2d2d2d"))  # 行号背景色
        
        # 获取字体和颜色
        font = self.text_browser.font()
        painter.setFont(font)
        painter.setPen(QColor("#808080"))  # 行号文字颜色
        
        # 获取视口
        viewport = self.text_browser.viewport()
        scrollbar = self.text_browser.verticalScrollBar()
        offset = scrollbar.value()
        
        # 获取第一行的位置
        cursor = self.text_browser.cursorForPosition(QPoint(0, 0))
        block = cursor.block()
        block_number = block.blockNumber() + 1  # 行号从1开始
        
        # 计算行高
        fm = QFontMetrics(font)
        line_height = fm.height()
        
        # 获取当前块的顶部位置
        top = self.text_browser.document().documentLayout().blockBoundingRect(block).top() - offset
        bottom = top + line_height
        
        # 绘制可见区域的行号
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(0, int(top), self.width() - 5, line_height, 
                               Qt.AlignRight, str(block_number))
            
            block = block.next()
            top = bottom
            bottom = top + line_height
            block_number += 1
    
    def update_width(self):
        """更新行号区域宽度"""
        # 计算最大行号所需宽度
        lines = self.text_browser.document().blockCount()
        fm = QFontMetrics(self.text_browser.font())
        width = fm.width(str(lines)) + 20  # 加一些边距
        self.setFixedWidth(max(width, 40))  # 最小宽度40
    
    def update_area(self, rect, dy):
        """更新行号区域"""
        if dy:
            self.scroll(0, dy)
        else:
            self.update(0, rect.y(), self.width(), rect.height())
        
        if rect.contains(self.text_browser.viewport().rect()):
            self.update_width()


class CustomTextBrowser(QTextBrowser):
    """自定义文本浏览器，修复文本选择问题，支持行号显示"""
    text_selected = pyqtSignal(str)  # 自定义信号，用于传递选中的文本
    selection_cleared = pyqtSignal()  # 自定义信号，当选择被清除时触发
    line_number_area = None
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_selection = ""
        self.last_has_selection = False  # 记录上次是否有选择
        self.line_number_visible = False
        
        # 连接信号用于更新行号
        self.verticalScrollBar().valueChanged.connect(self.update_line_numbers)
        self.textChanged.connect(self.update_line_numbers)
    
    def set_line_number_visible(self, visible):
        """设置行号是否可见"""
        self.line_number_visible = visible
        if visible and not self.line_number_area:
            self.line_number_area = LineNumberArea(self)
            # 设置视口边距以显示行号
            self.setViewportMargins(self.line_number_area.width(), 0, 0, 0)
            self.line_number_area.show()
        elif not visible and self.line_number_area:
            self.line_number_area.hide()
            self.setViewportMargins(0, 0, 0, 0)
            self.line_number_area = None
        self.update_line_numbers()
    
    def resizeEvent(self, event):
        """重写resizeEvent，调整行号区域大小"""
        super().resizeEvent(event)
        if self.line_number_area:
            cr = self.contentsRect()
            self.line_number_area.setGeometry(cr.left(), cr.top(), 
                                            self.line_number_area.width(), cr.height())
    
    def update_line_numbers(self):
        """更新行号显示"""
        if self.line_number_area:
            self.line_number_area.update_width()
            self.line_number_area.update(0, 0, self.line_number_area.width(), self.height())
        
    def mouseReleaseEvent(self, event):
        """鼠标释放事件，处理文本选择"""
        if event.button() == Qt.LeftButton:
            # 先调用父类的方法
            super().mouseReleaseEvent(event)
            
            # 稍微延迟一下，确保选择已完成
            QTimer.singleShot(50, self.process_selection)
        else:
            super().mouseReleaseEvent(event)
            
    def process_selection(self):
        """处理选中的文本"""
        cursor = self.textCursor()
        has_selection = cursor.hasSelection()
        
        if has_selection:
            selected_text = cursor.selectedText()
            
            # 清理选中的文本（移除特殊字符）
            cleaned_text = self.clean_selected_text(selected_text)
            
            if cleaned_text and cleaned_text != self.last_selection:
                self.last_selection = cleaned_text
                # 发出自定义信号
                self.text_selected.emit(cleaned_text)
                
            self.last_has_selection = True
        else:
            # 如果之前有选择，现在没有选择，说明选择被清除了
            if self.last_has_selection:
                self.selection_cleared.emit()
                self.last_has_selection = False
                self.last_selection = ""
                
    def clean_selected_text(self, text):
        """清理选中的文本，移除特殊字符"""
        if not text:
            return ""
            
        # 替换常见的特殊字符
        cleaned = text
        
        # 移除Unicode段落分隔符 (U+2029) 和行分隔符 (U+2028)
        cleaned = cleaned.replace('\u2029', '').replace('\u2028', '')
        
        # 移除控制字符
        for i in range(32):  # 移除控制字符 (0-31)
            cleaned = cleaned.replace(chr(i), '')
            
        # 移除开头和结尾的空格、换行符
        cleaned = cleaned.strip()
        
        return cleaned


class LogHighlighter(QSyntaxHighlighter):
    """日志高亮器，用于高亮匹配的文本"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_pattern = ""
        self.case_sensitive = False
        self.highlight_all = True  # 是否高亮所有匹配项，还是只高亮当前选中的
        self.current_match_start = -1  # 当前选中匹配项的起始位置
        self.current_match_end = -1    # 当前选中匹配项的结束位置
        
        # 普通高亮格式（用于所有匹配项）
        self.highlight_format = QTextCharFormat()
        self.highlight_format.setBackground(QColor(200, 150, 0, 150))  # 黄色半透明背景
        self.highlight_format.setForeground(QColor(255, 255, 200))    # 浅黄色文字
        
        # 当前选中项的高亮格式（用于当前选中的文本）
        self.current_match_format = QTextCharFormat()
        self.current_match_format.setBackground(QColor(135, 206, 250, 150))  # 浅蓝色半透明背景
        self.current_match_format.setForeground(QColor(255, 255, 255))    # 白色文字
        
    def set_search_pattern(self, pattern, case_sensitive=False):
        """设置搜索模式"""
        self.search_pattern = str(pattern) if pattern else ""
        self.case_sensitive = case_sensitive
        self.rehighlight()
        
    def set_current_match(self, start, end):
        """设置当前选中的匹配项位置"""
        self.current_match_start = start
        self.current_match_end = end
        self.rehighlight()
        
    def set_highlight_all(self, highlight_all):
        """设置是否高亮所有匹配项"""
        self.highlight_all = highlight_all
        self.rehighlight()
        
    def highlightBlock(self, text):
        """高亮文本块"""
        if not self.search_pattern or not text:
            return
            
        try:
            # 获取当前块的起始位置
            block_start = self.currentBlock().position()
            
            # 修复：当case_sensitive为True时区分大小写，为False时不区分
            if not self.case_sensitive:  # 不区分大小写
                pattern = self.search_pattern.lower()
                text_lower = text.lower()
                index = 0
                pattern_len = len(pattern)
                
                while True:
                    index = text_lower.find(pattern, index)
                    if index == -1:
                        break
                    
                    # 计算实际位置
                    actual_start = block_start + index
                    actual_end = actual_start + pattern_len
                    
                    # 判断是否是当前选中的匹配项
                    is_current_match = (actual_start == self.current_match_start and 
                                       actual_end == self.current_match_end)
                    
                    # 如果只高亮当前选中的，则检查是否匹配
                    if self.highlight_all or is_current_match:
                        # 使用不同的高亮格式
                        if is_current_match:
                            self.setFormat(index, pattern_len, self.current_match_format)
                        else:
                            self.setFormat(index, pattern_len, self.highlight_format)
                    
                    index += pattern_len
            else:  # 区分大小写
                pattern = self.search_pattern
                index = 0
                pattern_len = len(pattern)
                
                while True:
                    index = text.find(pattern, index)
                    if index == -1:
                        break
                    
                    # 计算实际位置
                    actual_start = block_start + index
                    actual_end = actual_start + pattern_len
                    
                    # 判断是否是当前选中的匹配项
                    is_current_match = (actual_start == self.current_match_start and 
                                       actual_end == self.current_match_end)
                    
                    # 如果只高亮当前选中的，则检查是否匹配
                    if self.highlight_all or is_current_match:
                        # 使用不同的高亮格式
                        if is_current_match:
                            self.setFormat(index, pattern_len, self.current_match_format)
                        else:
                            self.setFormat(index, pattern_len, self.highlight_format)
                    
                    index += pattern_len
                    
        except Exception as e:
            print(f"高亮错误: {e}")
            return


class BufferSettingsDialog(QDialog):
    """缓冲区设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("缓冲区设置")
        self.resize(350, 200)
        
        self.setup_ui()
        self.apply_dark_theme()
        
    def setup_ui(self):
        """设置对话框界面"""
        layout = QVBoxLayout(self)
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 接收缓冲区大小
        self.receive_buffer_spin = QSpinBox()
        self.receive_buffer_spin.setRange(1024, 10485760)  # 1024字节 - 10MB
        self.receive_buffer_spin.setValue(1024 * 100)  # 默认102400字节
        self.receive_buffer_spin.setSuffix(" 字节")
        form_layout.addRow("接收缓冲区大小:", self.receive_buffer_spin)
        
        # 发送缓冲区大小
        self.send_buffer_spin = QSpinBox()
        self.send_buffer_spin.setRange(1024, 10485760)  # 1024字节 - 10MB
        self.send_buffer_spin.setValue(1024 * 10)  # 默认10240字节
        self.send_buffer_spin.setSuffix(" 字节")
        form_layout.addRow("发送缓冲区大小:", self.send_buffer_spin)
        
        # 接收超时时间
        self.receive_timeout_spin = QSpinBox()
        self.receive_timeout_spin.setRange(100, 10000)  # 100ms - 10s
        self.receive_timeout_spin.setValue(1000)  # 默认1s
        self.receive_timeout_spin.setSuffix(" ms")
        form_layout.addRow("接收超时时间:", self.receive_timeout_spin)
        
        # 发送超时时间
        self.send_timeout_spin = QSpinBox()
        self.send_timeout_spin.setRange(100, 10000)  # 100ms - 10s
        self.send_timeout_spin.setValue(1000)  # 默认1s
        self.send_timeout_spin.setSuffix(" ms")
        form_layout.addRow("发送超时时间:", self.send_timeout_spin)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def apply_dark_theme(self):
        """应用暗黑主题"""
        self.setStyleSheet("""
            QDialog {
                background-color: #303030;
            }
            QLabel {
                color: #cccccc;
            }
            QSpinBox {
                background-color: #252525;
                color: #dddddd;
                border: 1px solid #404040;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton {
                background-color: #505050;
                color: #dddddd;
                border: 1px solid #606060;
                border-radius: 3px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #606060;
            }
        """)
        
    def get_settings(self):
        """获取设置值"""
        return {
            'receive_buffer': self.receive_buffer_spin.value(),
            'send_buffer': self.send_buffer_spin.value(),
            'receive_timeout': self.receive_timeout_spin.value() / 1000.0,  # 转换为秒
            'send_timeout': self.send_timeout_spin.value() / 1000.0
        }
        
    def set_settings(self, settings):
        """设置初始值"""
        if 'receive_buffer' in settings:
            self.receive_buffer_spin.setValue(settings['receive_buffer'])
        if 'send_buffer' in settings:
            self.send_buffer_spin.setValue(settings['send_buffer'])
        if 'receive_timeout' in settings:
            self.receive_timeout_spin.setValue(int(settings['receive_timeout'] * 1000))
        if 'send_timeout' in settings:
            self.send_timeout_spin.setValue(int(settings['send_timeout'] * 1000))


class SerialThread(QThread):
    """串口读取线程，防止界面卡死"""
    data_received = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, port, baudrate, bytesize, stopbits, parity, timeout=0.1):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.stopbits = stopbits
        self.parity = parity
        self.timeout = timeout
        self.serial_port = None
        self.running = False
        self.mutex = QMutex()
        
    def run(self):
        """线程运行函数"""
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
                timeout=self.timeout
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
                            # 短暂休眠，避免CPU占用过高
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
        """关闭串口"""
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
        """写入数据到串口"""
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
        """停止线程"""
        self.running = False
        self.wait()


class SerialTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log tool v1.2")
        self.resize(1200, 800)
        
        # 设置图标
        self.setup_icon()
        
        # 串口相关变量
        self.serial_thread = None
        self.reconnect_timer = QTimer()
        self.reconnect_timer.timeout.connect(self.auto_reconnect)
        self.reconnect_count = 0
        self.max_reconnect = 3
        
        # 数据接收缓存
        self.receive_count = 0
        self.send_count = 0
        
        # 重复发送定时器
        self.repeat_timer = QTimer()
        self.repeat_timer.timeout.connect(self.send_data)
        
        # 缓冲区设置
        self.buffer_settings = {
            'receive_buffer': 1024 * 1024,  # 1MB
            'send_buffer': 1024 * 1024,     # 1MB
            'receive_timeout': 1.0,         # 1秒
            'send_timeout': 1.0             # 1秒
        }
        
        # 数据缓冲区
        self.receive_buffer = bytearray()
        self.send_buffer = bytearray()
        
        # 配置区域显示状态
        self.config_visible = True
        
        # 字体大小设置 - 改为默认12pt
        self.font_size = 12  # 默认字体大小改为12pt
        
        # 搜索相关变量
        self.search_text = ""
        self.case_sensitive = False
        self.current_search_index = 0
        self.search_results = []  # 存储匹配位置
        self.auto_jump = False  # 控制是否自动跳转到第一个匹配项
        self.first_click = True  # 标记是否是第一次点击上下按钮
        
        # 初始化界面
        self.setup_ui()
        self.setup_menu()
        self.refresh_ports()
        
        # 定时刷新可用串口
        self.port_refresh_timer = QTimer()
        self.port_refresh_timer.timeout.connect(self.refresh_ports)
        self.port_refresh_timer.start(2000)  # 每2秒刷新一次
        
    def setup_icon(self):
        """设置应用程序图标 - 简化图标加载逻辑"""
        # 图标文件名
        icon_filename = "serial_port.ico"
        
        # 1. 首先尝试从当前目录加载图标
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, icon_filename)
        
        if os.path.exists(icon_path):
            try:
                icon = QIcon(icon_path)
                if not icon.isNull():
                    self.setWindowIcon(icon)
                    print(f"✓ 从当前目录加载图标成功: {icon_path}")
                    return
            except Exception as e:
                print(f"✗ 从当前目录加载图标失败: {e}")
        
        # 2. 尝试从PyInstaller的临时目录加载图标
        if hasattr(sys, '_MEIPASS'):
            temp_dir = sys._MEIPASS
            temp_icon_path = os.path.join(temp_dir, icon_filename)
            if os.path.exists(temp_icon_path):
                try:
                    icon = QIcon(temp_icon_path)
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                        print(f"✓ 从PyInstaller临时目录加载图标成功: {temp_icon_path}")
                        return
                except Exception as e:
                    print(f"✗ 从PyInstaller临时目录加载图标失败: {e}")
        
        # 3. 尝试从应用程序目录加载（打包后的情况）
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
            app_icon_path = os.path.join(app_dir, icon_filename)
            if os.path.exists(app_icon_path):
                try:
                    icon = QIcon(app_icon_path)
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                        print(f"✓ 从应用程序目录加载图标成功: {app_icon_path}")
                        return
                except Exception as e:
                    print(f"✗ 从应用程序目录加载图标失败: {e}")
        
        # 4. 都没有找到，使用默认图标
        print("⚠ 未找到图标文件，将使用默认图标")
        
    def setup_ui(self):
        """设置主界面 - 上方日志，下方配置"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 应用简洁暗黑主题
        self.apply_simple_dark_theme()
        
        # 创建工具栏
        self.setup_toolbar()
        
        # 创建接收区域（上方）
        self.receive_frame = self.create_receive_frame()
        self.main_layout.addWidget(self.receive_frame, 1)  # 占据主要空间
        
        # 创建配置区域（下方）
        self.config_frame = self.create_config_frame()
        self.main_layout.addWidget(self.config_frame)
        
    def apply_simple_dark_theme(self):
        """应用简洁暗黑主题"""
        # 深灰色调色板
        dark_palette = QPalette()
        
        # 基础颜色 - 深灰色系
        dark_palette.setColor(QPalette.Window, QColor(40, 40, 40))
        dark_palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.Text, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.Button, QColor(60, 60, 60))
        dark_palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Link, QColor(100, 150, 220))
        dark_palette.setColor(QPalette.Highlight, QColor(80, 120, 180))
        dark_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        # 应用调色板
        QApplication.setPalette(dark_palette)
        
        # 设置样式表 - 简洁暗黑风格
        self.setStyleSheet("""
            /* 主窗口 */
            QMainWindow {
                background-color: #282828;
            }
            
            /* 分组框 */
            QGroupBox {
                color: #cccccc;
                border: 1px solid #404040;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: 600;
                background-color: #303030;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #aaaaaa;
            }
            
            /* 标签 */
            QLabel {
                color: #bbbbbb;
                padding: 2px;
            }
            
            /* 输入框 */
            QLineEdit, QComboBox, QSpinBox, QTextEdit, QTextBrowser {
                background-color: #252525;
                color: #dddddd;
                border: 1px solid #404040;
                border-radius: 3px;
                padding: 5px;
                selection-background-color: #505050;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #606060;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #353535;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 1px solid #404040;
                padding: 5px;
            }
            
            /* 按钮 */
            QPushButton {
                background-color: #505050;
                color: #dddddd;
                border: 1px solid #606060;
                border-radius: 3px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #606060;
                border: 1px solid #707070;
            }
            QPushButton:pressed {
                background-color: #404040;
                padding: 7px 11px 5px 13px;
            }
            QPushButton:disabled {
                background-color: #303030;
                color: #888888;
                border: 1px solid #404040;
            }
            
            /* 复选框 */
            QCheckBox {
                color: #bbbbbb;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #606060;
                border-radius: 2px;
                background-color: #252525;
            }
            QCheckBox::indicator:checked {
                background-color: #606060;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #808080;
            }
            
            /* 状态栏 */
            QStatusBar {
                color: #aaaaaa;
                background-color: #282828;
                border-top: 1px solid #404040;
            }
            
            /* 工具栏 */
            QToolBar {
                background-color: #303030;
                border: none;
                border-bottom: 1px solid #404040;
                spacing: 3px;
                padding: 3px;
            }
            QToolBar QToolButton {
                padding: 5px 8px;
                border-radius: 3px;
            }
            QToolBar QToolButton:hover {
                background-color: #404040;
            }
            
            /* 菜单栏 */
            QMenuBar {
                background-color: #303030;
                color: #bbbbbb;
                border-bottom: 1px solid #404040;
            }
            QMenuBar::item {
                padding: 5px 10px;
                background-color: transparent;
            }
            QMenuBar::item:selected {
                background-color: #404040;
                border-radius: 2px;
            }
            
            /* 菜单 */
            QMenu {
                background-color: #303030;
                color: #bbbbbb;
                border: 1px solid #404040;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px 5px 20px;
            }
            QMenu::item:selected {
                background-color: #404040;
            }
            QMenu::separator {
                height: 1px;
                background-color: #404040;
                margin: 5px 10px;
            }
            
            /* 滚动条 */
            QScrollBar:vertical {
                background-color: #252525;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #606060;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #707070;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            QScrollBar:horizontal {
                background-color: #252525;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #606060;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #707070;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
    def setup_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # 显示/隐藏配置区域按钮
        self.toggle_config_action = QAction("显示配置", self)
        self.toggle_config_action.setCheckable(True)
        self.toggle_config_action.setChecked(True)
        self.toggle_config_action.triggered.connect(self.toggle_config_area)
        toolbar.addAction(self.toggle_config_action)
        
        toolbar.addSeparator()
        
        # 连接/断开按钮
        self.connect_action = QAction("连接", self)
        self.connect_action.triggered.connect(self.toggle_connection)
        toolbar.addAction(self.connect_action)
        
        toolbar.addSeparator()
        
        # 清除接收
        clear_rx_action = QAction("清除接收", self)
        clear_rx_action.triggered.connect(self.clear_receive)
        toolbar.addAction(clear_rx_action)
        
        toolbar.addSeparator()
        
        # 保存接收数据
        save_rx_action = QAction("保存接收", self)
        save_rx_action.triggered.connect(self.save_receive_data)
        toolbar.addAction(save_rx_action)
        
    def toggle_config_area(self):
        """切换配置区域显示/隐藏"""
        self.config_visible = not self.config_visible
        
        if self.config_visible:
            self.config_frame.show()
            self.toggle_config_action.setText("隐藏配置")
            self.toggle_config_action.setChecked(True)
        else:
            self.config_frame.hide()
            self.toggle_config_action.setText("显示配置")
            self.toggle_config_action.setChecked(False)
            
    def create_receive_frame(self):
        """创建接收区域 - 上方"""
        receive_frame = QFrame()
        receive_frame.setFrameStyle(QFrame.NoFrame)
        
        layout = QVBoxLayout(receive_frame)
        layout.setSpacing(5)
        
        # 接收控制栏
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #303030;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(10, 5, 10, 5)
        
        # 控制选项
        self.timestamp_cb = QCheckBox("时间戳")
        self.timestamp_cb.setChecked(False)
        control_layout.addWidget(self.timestamp_cb)
        
        self.hex_display_cb = QCheckBox("十六进制")
        control_layout.addWidget(self.hex_display_cb)
        
        self.pause_display_cb = QCheckBox("暂停显示")
        control_layout.addWidget(self.pause_display_cb)
        
        self.line_numbers_cb = QCheckBox("显示行号")
        self.line_numbers_cb.setChecked(False)
        self.line_numbers_cb.stateChanged.connect(self.on_line_numbers_changed)
        control_layout.addWidget(self.line_numbers_cb)
        
        self.auto_scroll_cb = QCheckBox("自动滚屏")
        self.auto_scroll_cb.setChecked(True)
        control_layout.addWidget(self.auto_scroll_cb)
        
        # 搜索栏
        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)
        
        # 搜索标签
        search_label = QLabel("查找:")
        search_label.setStyleSheet("color: #aaaaaa;")
        search_layout.addWidget(search_label)
        
        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索内容...")
        self.search_input.setMaximumWidth(200)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.returnPressed.connect(self.find_next)
        search_layout.addWidget(self.search_input)
        
        # 搜索结果标签
        self.search_result_label = QLabel("")
        self.search_result_label.setStyleSheet("color: #a0c0a0; min-width: 120px; font-weight: 500;")
        search_layout.addWidget(self.search_result_label)
        
        # 大小写敏感复选框
        self.case_sensitive_cb = QCheckBox("区分大小写")
        self.case_sensitive_cb.setChecked(False)
        self.case_sensitive_cb.stateChanged.connect(self.on_case_sensitive_changed)
        search_layout.addWidget(self.case_sensitive_cb)
        
        # 查找上一个按钮
        self.find_prev_btn = QPushButton("上")
        self.find_prev_btn.setFixedWidth(40)  # 缩小按钮宽度
        self.find_prev_btn.clicked.connect(self.find_previous)
        self.find_prev_btn.setEnabled(False)
        search_layout.addWidget(self.find_prev_btn)
        
        # 查找下一个按钮
        self.find_next_btn = QPushButton("下")
        self.find_next_btn.setFixedWidth(40)  # 缩小按钮宽度
        self.find_next_btn.clicked.connect(self.find_next)
        self.find_next_btn.setEnabled(False)
        search_layout.addWidget(self.find_next_btn)
        
        search_layout.addStretch()
        control_layout.addLayout(search_layout)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        self.receive_stats_label = QLabel("接收: 0 字节")
        self.receive_stats_label.setStyleSheet("color: #a0c0a0;")
        stats_layout.addWidget(self.receive_stats_label)
        
        self.send_stats_label = QLabel("发送: 0 字节")
        self.send_stats_label.setStyleSheet("color: #a0c0a0;")
        stats_layout.addWidget(self.send_stats_label)
        
        # 缓冲区信息
        self.buffer_stats_label = QLabel("缓冲区: 0/1048576 字节")
        self.buffer_stats_label.setStyleSheet("color: #a0a0c0;")
        stats_layout.addWidget(self.buffer_stats_label)
        
        self.status_stats_label = QLabel("状态: 就绪")
        self.status_stats_label.setStyleSheet("color: #a0a0c0; font-weight: 500;")
        stats_layout.addWidget(self.status_stats_label)
        
        stats_layout.addStretch()
        control_layout.addLayout(stats_layout)
        
        # 接收文本框 - 使用自定义的文本浏览器
        self.receive_text = CustomTextBrowser()
        self.receive_text.setFont(QFont("Consolas", self.font_size))
        # 默认启用自动换行（自动换行功能已从界面移除）
        self.receive_text.setLineWrapMode(QTextEdit.WidgetWidth)
        
        # 连接文本选中信号 - 已注释，禁用鼠标选中自动高亮功能
        # self.receive_text.text_selected.connect(self.on_text_selected)
        # 连接选择清除信号 - 已注释，禁用鼠标选中自动高亮功能
        # self.receive_text.selection_cleared.connect(self.on_selection_cleared)
        
        # 设置语法高亮
        self.highlighter = LogHighlighter(self.receive_text.document())
        
        # 设置专业终端样式
        self.receive_text.setStyleSheet(f"""
            QTextBrowser {{
                background-color: #1a1a1a;
                color: #c0c0c0;
                border: 1px solid #404040;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: {self.font_size}pt;
                selection-background-color: #505050;
                padding: 5px;
            }}
        """)
        
        layout.addWidget(control_frame)
        layout.addWidget(self.receive_text, 1)
        
        return receive_frame
        
    def on_text_selected(self, text):
        """文本选中事件处理"""
        if text and len(text.strip()) > 0:
            # 保存当前光标位置和选区
            cursor = self.receive_text.textCursor()
            saved_start = cursor.selectionStart()
            saved_end = cursor.selectionEnd()
            
            # 清除之前的高亮和搜索结果
            self.highlighter.set_search_pattern("")
            self.highlighter.set_highlight_all(True)  # 重置为高亮所有模式
            self.search_results = []
            self.search_result_label.setText("")
            self.current_search_index = 0
            self.first_click = True
            
            # 将选中的文本设置到搜索框
            self.search_input.setText(text)
            
            # 查找所有匹配项
            self.find_all_matches()
            
            # 恢复光标位置并设置高亮
            new_cursor = QTextCursor(self.receive_text.document())
            new_cursor.setPosition(saved_start)
            new_cursor.setPosition(saved_end, QTextCursor.KeepAnchor)
            self.receive_text.setTextCursor(new_cursor)
            
            # 设置高亮
            if new_cursor.hasSelection():
                start = new_cursor.selectionStart()
                end = new_cursor.selectionEnd()
                self.highlighter.set_highlight_all(True)
                self.highlighter.set_current_match(start, end)
            
    def on_selection_cleared(self):
        """选择清除事件处理 - 自动取消高亮"""
        # 清除搜索框
        self.search_input.clear()
        # 清除高亮
        self.highlighter.set_search_pattern("")
        # 重置为高亮所有模式
        self.highlighter.set_highlight_all(True)
        # 清除搜索结果
        self.search_results = []
        self.search_result_label.setText("")
        # 重置搜索索引
        self.current_search_index = 0
        self.first_click = True
            
    def on_search_text_changed(self, text):
        """搜索文本改变"""
        try:
            # 保存当前滚动位置
            scrollbar = self.receive_text.verticalScrollBar()
            scroll_position = scrollbar.value() if scrollbar else 0
            
            self.search_text = str(text).strip() if text else ""
            if self.search_text:
                self.find_next_btn.setEnabled(True)
                self.find_prev_btn.setEnabled(True)
                
                # 更新高亮 - 手动输入时高亮所有匹配项
                self.highlighter.set_highlight_all(True)
                self.highlighter.set_search_pattern(self.search_text, self.case_sensitive_cb.isChecked())
                    
                # 重置搜索索引
                self.current_search_index = 0
                self.first_click = True
                
                # 查找所有匹配项
                self.find_all_matches()
                
                # 恢复滚动位置
                if scrollbar:
                    scrollbar.setValue(scroll_position)
            else:
                self.find_next_btn.setEnabled(False)
                self.find_prev_btn.setEnabled(False)
                self.highlighter.set_search_pattern("")
                self.search_result_label.setText("")
        except Exception as e:
            print(f"搜索文本改变处理错误: {e}")
            self.highlighter.set_search_pattern("")
            
    def on_case_sensitive_changed(self, state):
        """大小写敏感选项改变"""
        try:
            # 保存当前滚动位置
            scrollbar = self.receive_text.verticalScrollBar()
            scroll_position = scrollbar.value() if scrollbar else 0
            
            if self.search_text:
                # 更新高亮 - 手动改变选项时高亮所有匹配项
                self.highlighter.set_highlight_all(True)
                self.highlighter.set_search_pattern(self.search_text, (state == Qt.Checked))
                # 重置搜索
                self.current_search_index = 0
                self.auto_jump = False
                self.find_all_matches()
                
                # 恢复滚动位置
                if scrollbar:
                    scrollbar.setValue(scroll_position)
        except Exception as e:
            print(f"大小写敏感选项改变错误: {e}")
            
    def find_all_matches(self):
        """查找所有匹配项"""
        try:
            if not self.search_text or not self.receive_text.document():
                self.search_results = []
                self.search_result_label.setText("未找到")
                return
                
            # 清空之前的搜索结果
            self.search_results = []
            
            # 获取文档
            document = self.receive_text.document()
            
            # 修复：正确设置查找标志
            # QTextDocument.FindFlag(0) - 默认查找，不区分大小写
            # QTextDocument.FindCaseSensitively - 区分大小写
            if self.case_sensitive_cb.isChecked():  # 如果选中"区分大小写"
                flags = QTextDocument.FindCaseSensitively  # 区分大小写
            else:  # 如果未选中"区分大小写"
                flags = QTextDocument.FindFlag(0)  # 不区分大小写
                
            # 从文档开始查找
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.Start)
            
            # 查找所有匹配项
            while True:
                cursor = document.find(self.search_text, cursor, flags)
                if cursor.isNull():
                    break
                    
                # 记录匹配位置
                self.search_results.append({
                    'start': cursor.selectionStart(),
                    'end': cursor.selectionEnd()
                })
            
            # 更新搜索结果标签
            if self.search_results:
                self.search_result_label.setText(f"找到 {len(self.search_results)} 个结果")
                # 只有在明确调用查找时才跳转
                if self.auto_jump and self.current_search_index < len(self.search_results):
                    self.jump_to_match(self.current_search_index)
            else:
                self.search_result_label.setText("未找到")
                
        except Exception as e:
            print(f"查找所有匹配项错误: {e}")
            self.search_results = []
            self.search_result_label.setText("搜索错误")
            
    def find_next(self):
        """查找下一个"""
        try:
            if not self.search_text or not self.search_results:
                return
                
            # 获取当前光标位置
            cursor = self.receive_text.textCursor()
            current_pos = cursor.position()
            
            # 如果是第一次点击查找按钮，或者没有选中任何文本
            if self.first_click or not cursor.hasSelection():
                # 找到第一个在当前光标位置之后的匹配项
                self.current_search_index = -1
                for i, match in enumerate(self.search_results):
                    if match['start'] > current_pos:
                        self.current_search_index = i
                        break
                
                # 如果没有找到在当前位置之后的，则循环到第一个
                if self.current_search_index == -1 and self.search_results:
                    self.current_search_index = 0
            else:
                # 从当前选中的位置开始查找下一个
                current_selection_start = cursor.selectionStart()
                current_selection_end = cursor.selectionEnd()
                
                # 找到当前选中的匹配项在搜索结果中的索引
                found_current = False
                for i, match in enumerate(self.search_results):
                    if match['start'] == current_selection_start and match['end'] == current_selection_end:
                        self.current_search_index = i
                        found_current = True
                        break
                
                # 如果找到了当前选中的匹配项，则移动到下一个
                if found_current:
                    self.current_search_index += 1
                    if self.current_search_index >= len(self.search_results):
                        self.current_search_index = 0  # 循环到第一个
                else:
                    # 如果没有找到当前选中的，则从当前位置开始查找
                    self.current_search_index = -1
                    for i, match in enumerate(self.search_results):
                        if match['start'] > current_pos:
                            self.current_search_index = i
                            break
                    if self.current_search_index == -1 and self.search_results:
                        self.current_search_index = 0
                
            self.first_click = False
            self.auto_jump = True
                
            # 跳转到匹配项
            self.jump_to_match(self.current_search_index)
            
        except Exception as e:
            print(f"查找下一个错误: {e}")
            
    def find_previous(self):
        """查找上一个"""
        try:
            if not self.search_text or not self.search_results:
                return
                
            # 获取当前光标位置
            cursor = self.receive_text.textCursor()
            current_pos = cursor.position()
            
            # 如果是第一次点击查找按钮，或者没有选中任何文本
            if self.first_click or not cursor.hasSelection():
                # 找到最后一个在当前光标位置之前的匹配项
                self.current_search_index = -1
                for i in range(len(self.search_results) - 1, -1, -1):
                    if self.search_results[i]['start'] < current_pos:
                        self.current_search_index = i
                        break
                
                # 如果没有找到在当前位置之前的，则循环到最后一个
                if self.current_search_index == -1 and self.search_results:
                    self.current_search_index = len(self.search_results) - 1
            else:
                # 从当前选中的位置开始查找上一个
                current_selection_start = cursor.selectionStart()
                current_selection_end = cursor.selectionEnd()
                
                # 找到当前选中的匹配项在搜索结果中的索引
                found_current = False
                for i, match in enumerate(self.search_results):
                    if match['start'] == current_selection_start and match['end'] == current_selection_end:
                        self.current_search_index = i
                        found_current = True
                        break
                
                # 如果找到了当前选中的匹配项，则移动到上一个
                if found_current:
                    self.current_search_index -= 1
                    if self.current_search_index < 0:
                        self.current_search_index = len(self.search_results) - 1  # 循环到最后一个
                else:
                    # 如果没有找到当前选中的，则从当前位置开始查找
                    self.current_search_index = -1
                    for i in range(len(self.search_results) - 1, -1, -1):
                        if self.search_results[i]['start'] < current_pos:
                            self.current_search_index = i
                            break
                    if self.current_search_index == -1 and self.search_results:
                        self.current_search_index = len(self.search_results) - 1
                
            self.first_click = False
            self.auto_jump = True
                
            # 跳转到匹配项
            self.jump_to_match(self.current_search_index)
            
        except Exception as e:
            print(f"查找上一个错误: {e}")
            
    def jump_to_match(self, index):
        """跳转到指定的匹配项"""
        try:
            if not self.search_results or index < 0 or index >= len(self.search_results):
                return
                
            # 获取匹配位置
            match = self.search_results[index]
            
            # 创建光标
            cursor = QTextCursor(self.receive_text.document())
            
            # 设置光标位置
            cursor.setPosition(match['start'])
            cursor.setPosition(match['end'], QTextCursor.KeepAnchor)
            
            # 设置光标并确保可见
            self.receive_text.setTextCursor(cursor)
            self.receive_text.ensureCursorVisible()
            
            # 修复：上下搜索时保持所有相同字符的高亮，并用不同颜色标记当前选中的
            self.highlighter.set_highlight_all(True)
            self.highlighter.set_current_match(match['start'], match['end'])
            
            # 更新搜索结果标签
            self.search_result_label.setText(f"{index + 1}/{len(self.search_results)}")
            
        except Exception as e:
            print(f"跳转到匹配项错误: {e}")
            
    def create_config_frame(self):
        """创建配置区域 - 下方"""
        config_frame = QFrame()
        config_frame.setFrameStyle(QFrame.NoFrame)
        
        layout = QVBoxLayout(config_frame)
        layout.setSpacing(5)
        
        # 使用分割器将串口配置和发送配置放在一行
        splitter = QSplitter(Qt.Horizontal)
        
        # 串口配置
        config_group = self.create_config_group()
        splitter.addWidget(config_group)
        
        # 发送配置
        send_group = self.create_send_group()
        splitter.addWidget(send_group)
        
        # 设置分割器比例
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
        
        return config_frame
        
    def create_config_group(self):
        """创建串口配置区域"""
        config_group = QGroupBox("串口配置")
        layout = QGridLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 15, 10, 10)
        
        # 第一行：端口选择
        layout.addWidget(QLabel("端口:"), 0, 0)
        self.port_combo = QComboBox()
        layout.addWidget(self.port_combo, 0, 1, 1, 2)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        layout.addWidget(self.refresh_btn, 0, 3)
        
        # 第二行：波特率
        layout.addWidget(QLabel("波特率:"), 1, 0)
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems([
            "自定义", "300", "600", "1200", "2400", "4800", 
            "9600", "14400", "19200", "28800", "38400", 
            "57600", "115200", "230400", "460800", "921600"
        ])
        self.baudrate_combo.setCurrentText("115200")
        self.baudrate_combo.currentTextChanged.connect(self.on_baudrate_changed)
        layout.addWidget(self.baudrate_combo, 1, 1)
        
        # 自定义波特率输入
        self.custom_baudrate_edit = QLineEdit()
        self.custom_baudrate_edit.setPlaceholderText("自定义波特率")
        self.custom_baudrate_edit.setVisible(False)
        layout.addWidget(self.custom_baudrate_edit, 1, 2, 1, 2)
        
        # 第三行：其他参数
        param_layout = QHBoxLayout()
        param_layout.setSpacing(10)
        
        # 数据位
        param_layout.addWidget(QLabel("数据位:"))
        self.databits_combo = QComboBox()
        self.databits_combo.addItems(["5", "6", "7", "8"])
        self.databits_combo.setCurrentText("8")
        param_layout.addWidget(self.databits_combo)
        
        # 停止位
        param_layout.addWidget(QLabel("停止位:"))
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "1.5", "2"])
        self.stopbits_combo.setCurrentText("1")
        param_layout.addWidget(self.stopbits_combo)
        
        # 校验位
        param_layout.addWidget(QLabel("校验:"))
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["无", "奇校验", "偶校验"])
        self.parity_combo.setCurrentText("无")
        param_layout.addWidget(self.parity_combo)
        
        param_layout.addStretch()
        layout.addLayout(param_layout, 2, 0, 1, 4)
        
        # 第四行：连接按钮
        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_btn, 3, 0, 1, 4)
        
        config_group.setLayout(layout)
        return config_group
        
    def create_send_group(self):
        """创建发送区域"""
        send_group = QGroupBox("发送数据")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 15, 10, 10)
        
        # 发送文本框
        self.send_text = QTextEdit()
        self.send_text.setPlaceholderText("输入要发送的数据...")
        layout.addWidget(self.send_text, 2)
        
        # 发送选项
        options_layout = QGridLayout()
        options_layout.setSpacing(10)
        
        # 发送按钮
        self.send_btn = QPushButton("发送")
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self.send_data)
        options_layout.addWidget(self.send_btn, 0, 0, 1, 3)
        
        # 第一行选项
        row1_layout = QHBoxLayout()
        self.send_newline_cb = QCheckBox("发送新行")
        row1_layout.addWidget(self.send_newline_cb)
        self.hex_send_cb = QCheckBox("十六进制")
        row1_layout.addWidget(self.hex_send_cb)
        row1_layout.addStretch()
        options_layout.addLayout(row1_layout, 1, 0, 1, 3)
        
        # 第二行选项
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
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 保存接收数据
        save_rx_action = QAction("保存接收数据", self)
        save_rx_action.triggered.connect(self.save_receive_data)
        file_menu.addAction(save_rx_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        # 显示/隐藏配置区域
        toggle_config_menu_action = QAction("显示配置区域", self)
        toggle_config_menu_action.setCheckable(True)
        toggle_config_menu_action.setChecked(True)
        toggle_config_menu_action.triggered.connect(self.toggle_config_area)
        view_menu.addAction(toggle_config_menu_action)
        
        # 字体大小菜单
        font_menu = view_menu.addMenu("字体大小")
        
        # 存储字体动作列表，以便后续管理
        self.font_actions = []
        
        # 字体大小选项
        font_sizes = [8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 24]
        for size in font_sizes:
            font_action = QAction(f"{size} pt", self)
            font_action.setData(size)
            font_action.setCheckable(True)  # 所有选项都可选中
            
            # 设置当前默认字体选中状态
            if size == self.font_size:
                font_action.setChecked(True)
            
            # 连接信号
            font_action.triggered.connect(self.on_font_size_changed)
            
            # 添加到菜单和列表
            font_menu.addAction(font_action)
            self.font_actions.append(font_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        # 查找
        find_action = QAction("查找", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.focus_search_input)
        edit_menu.addAction(find_action)
        
        # 查找下一个
        find_next_action = QAction("查找下一个", self)
        find_next_action.setShortcut("F3")
        find_next_action.triggered.connect(self.find_next)
        edit_menu.addAction(find_next_action)
        
        # 查找上一个
        find_prev_action = QAction("查找上一个", self)
        find_prev_action.setShortcut("Shift+F3")
        find_prev_action.triggered.connect(self.find_previous)
        edit_menu.addAction(find_prev_action)
        
        edit_menu.addSeparator()
        
        # 清除搜索
        clear_search_action = QAction("清除搜索", self)
        clear_search_action.triggered.connect(self.clear_search)
        edit_menu.addAction(clear_search_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置")
        
        # 串口设置
        serial_settings_action = QAction("串口设置", self)
        serial_settings_action.triggered.connect(self.show_serial_settings)
        settings_menu.addAction(serial_settings_action)
        
        # 缓冲区设置
        buffer_settings_action = QAction("缓冲区设置", self)
        buffer_settings_action.triggered.connect(self.show_buffer_settings)
        settings_menu.addAction(buffer_settings_action)
        
        # 显示设置
        display_settings_action = QAction("显示设置", self)
        display_settings_action.triggered.connect(self.show_display_settings)
        settings_menu.addAction(display_settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        # 关于
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def focus_search_input(self):
        """聚焦到搜索输入框"""
        self.search_input.setFocus()
        self.search_input.selectAll()
        
    def clear_search(self):
        """清除搜索"""
        self.search_input.clear()
        self.highlighter.set_search_pattern("")
        self.highlighter.set_highlight_all(True)  # 重置为高亮所有模式
        self.search_result_label.setText("")
        self.search_results = []
        self.current_search_index = 0
        self.first_click = True
        
    def on_font_size_changed(self):
        """字体大小改变"""
        action = self.sender()
        if action and action.isChecked():
            new_size = action.data()
            if new_size != self.font_size:
                # 清除所有字体选项的选中状态
                for act in self.font_actions:
                    act.setChecked(False)
                
                # 设置当前选项为选中状态
                action.setChecked(True)
                
                # 更新字体大小
                self.font_size = new_size
                self.apply_font_size()
    
    def apply_font_size(self):
        """应用新的字体大小"""
        # 更新接收文本框字体
        self.receive_text.setFont(QFont("Consolas", self.font_size))
        
        # 更新样式表
        self.receive_text.setStyleSheet(f"""
            QTextBrowser {{
                background-color: #1a1a1a;
                color: #c0c0c0;
                border: 1px solid #404040;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: {self.font_size}pt;
                selection-background-color: #505050;
                padding: 5px;
            }}
        """)
        
        # 更新行号显示
        self.receive_text.update_line_numbers()
        
    def refresh_ports(self):
        """刷新可用串口"""
        current_port = self.port_combo.currentText()
        ports = serial.tools.list_ports.comports()
        
        self.port_combo.clear()
        for port in ports:
            description = port.description if port.description else "未知设备"
            self.port_combo.addItem(f"{port.device} - {description}", port.device)
            
        # 恢复之前的选择
        if current_port:
            index = self.port_combo.findText(current_port, Qt.MatchStartsWith)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)
                
    def on_baudrate_changed(self, text):
        """波特率选择改变"""
        if text == "自定义":
            self.custom_baudrate_edit.setVisible(True)
        else:
            self.custom_baudrate_edit.setVisible(False)
            
    def on_repeat_send_changed(self, state):
        """重复发送状态改变"""
        enabled = state == Qt.Checked
        self.repeat_interval_spin.setEnabled(enabled)
        
        if enabled:
            interval = self.repeat_interval_spin.value()
            self.repeat_timer.start(interval)
        else:
            self.repeat_timer.stop()
            
    # 自动换行功能已移除
    
    def on_line_numbers_changed(self, state):
        """行号显示状态改变"""
        self.receive_text.set_line_number_visible(state == Qt.Checked)
    
    def get_baudrate(self):
        """获取波特率"""
        if self.baudrate_combo.currentText() == "自定义":
            try:
                return int(self.custom_baudrate_edit.text())
            except ValueError:
                return 115200
        else:
            try:
                return int(self.baudrate_combo.currentText())
            except ValueError:
                return 115200
                
    def get_serial_params(self):
        """获取串口参数"""
        baudrate = self.get_baudrate()
        
        # 数据位
        databits_map = {"5": serial.FIVEBITS, "6": serial.SIXBITS, 
                       "7": serial.SEVENBITS, "8": serial.EIGHTBITS}
        bytesize = databits_map.get(self.databits_combo.currentText(), serial.EIGHTBITS)
        
        # 停止位
        stopbits_map = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE,
                       "2": serial.STOPBITS_TWO}
        stopbits = stopbits_map.get(self.stopbits_combo.currentText(), serial.STOPBITS_ONE)
        
        # 校验位
        parity_map = {"无": serial.PARITY_NONE, "奇校验": serial.PARITY_ODD,
                     "偶校验": serial.PARITY_EVEN}
        parity = parity_map.get(self.parity_combo.currentText(), serial.PARITY_NONE)
        
        return baudrate, bytesize, stopbits, parity
        
    def toggle_connection(self):
        """切换连接状态"""
        if self.serial_thread and self.serial_thread.isRunning():
            self.disconnect_serial()
        else:
            self.connect_serial()
            
    def connect_serial(self):
        """连接串口"""
        if self.port_combo.count() == 0:
            QMessageBox.warning(self, "警告", "没有找到可用串口")
            return
            
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "警告", "请选择串口")
            return
            
        try:
            baudrate, bytesize, stopbits, parity = self.get_serial_params()
            
            # 设置接收超时
            timeout = self.buffer_settings.get('receive_timeout', 1.0)
            
            # 创建串口线程
            self.serial_thread = SerialThread(port, baudrate, bytesize, stopbits, parity, timeout)
            self.serial_thread.data_received.connect(self.on_data_received)
            self.serial_thread.error_occurred.connect(self.on_serial_error)
            self.serial_thread.start()
            
            # 更新UI状态
            self.connect_btn.setText("断开")
            self.connect_action.setText("断开")
            self.send_btn.setEnabled(True)
            self.status_stats_label.setText(f"已连接到 {port}")
            
            # 重置重连计数器
            self.reconnect_count = 0
            
        except Exception as e:
            QMessageBox.critical(self, "连接错误", f"无法连接到串口: {str(e)}")
            self.status_stats_label.setText("连接失败")
            
    def disconnect_serial(self):
        """断开串口连接"""
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread = None
            
        # 停止重复发送
        if self.repeat_timer.isActive():
            self.repeat_timer.stop()
            
        # 更新UI状态
        self.connect_btn.setText("连接")
        self.connect_action.setText("连接")
        self.send_btn.setEnabled(False)
        self.status_stats_label.setText("已断开连接")
        
    def on_data_received(self, data):
        """接收数据回调"""
        if self.pause_display_cb.isChecked():
            return
            
        # 检查缓冲区大小
        max_buffer_size = self.buffer_settings.get('receive_buffer', 1024 * 1024)  # 1MB
        if len(self.receive_buffer) + len(data) > max_buffer_size:
            # 缓冲区溢出，丢弃最旧的数据
            discard_size = len(self.receive_buffer) + len(data) - max_buffer_size
            if discard_size < len(self.receive_buffer):
                self.receive_buffer = self.receive_buffer[discard_size:]
            else:
                self.receive_buffer = bytearray()
        
        # 添加到缓冲区
        self.receive_buffer.extend(data)
        
        # 更新接收计数
        self.receive_count += len(data)
        self.receive_stats_label.setText(f"接收: {self.receive_count} 字节")
        
        # 更新缓冲区信息
        buffer_bytes = len(self.receive_buffer)
        max_buffer_bytes = max_buffer_size
        self.buffer_stats_label.setText(f"缓冲区: {buffer_bytes}/{max_buffer_bytes} 字节")
        
        # 格式化数据
        if self.hex_display_cb.isChecked():
            # 十六进制显示
            hex_str = ' '.join(f'{b:02X}' for b in data)
            display_text = hex_str
        else:
            # 文本显示
            try:
                display_text = data.decode('utf-8', errors='replace')
            except:
                display_text = data.hex(' ')
                
        # 添加时间戳
        if self.timestamp_cb.isChecked():
            timestamp = datetime.now().strftime("[%H:%M:%S.%f")[:-3] + "] "
            display_text = timestamp + display_text
            
        # 保存当前滚动位置
        scrollbar = self.receive_text.verticalScrollBar()
        scroll_position = scrollbar.value() if scrollbar else 0
        
        # 添加到显示区域 - 使用insertPlainText避免自动添加换行符，只保留数据本身的换行
        cursor = self.receive_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(display_text)
        
        # 如果有搜索文本，重新应用高亮
        if self.search_text:
            try:
                self.highlighter.set_search_pattern(self.search_text, self.case_sensitive_cb.isChecked())
            except Exception as e:
                print(f"重新应用高亮错误: {e}")
            
        # 恢复滚动位置
        if scrollbar:
            scrollbar.setValue(scroll_position)
            
        # 自动滚屏
        if self.auto_scroll_cb.isChecked():
            cursor = self.receive_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.receive_text.setTextCursor(cursor)
            
    def on_serial_error(self, error_msg):
        """串口错误回调"""
        self.status_stats_label.setText(f"错误: {error_msg[:20]}...")
        
        # 尝试重连
        if self.reconnect_count < self.max_reconnect:
            self.reconnect_count += 1
            self.status_stats_label.setText(f"重连({self.reconnect_count}/{self.max_reconnect})...")
            self.reconnect_timer.singleShot(1000, self.auto_reconnect)
        else:
            self.disconnect_serial()
            QMessageBox.warning(self, "连接错误", f"串口连接失败: {error_msg}")
            
    def auto_reconnect(self):
        """自动重连"""
        if self.serial_thread and self.serial_thread.isRunning():
            return
            
        self.disconnect_serial()
        time.sleep(0.5)
        self.connect_serial()
        
    def send_data(self):
        """发送数据"""
        if not self.serial_thread or not self.serial_thread.isRunning():
            QMessageBox.warning(self, "警告", "串口未连接")
            return
            
        text = self.send_text.toPlainText()
        if not text:
            return
            
        # 检查发送缓冲区
        max_buffer_size = self.buffer_settings.get('send_buffer', 1024 * 1024)  # 1MB
        if len(self.send_buffer) + len(text) > max_buffer_size:
            QMessageBox.warning(self, "警告", "发送缓冲区已满")
            return
            
        # 十六进制发送
        if self.hex_send_cb.isChecked():
            try:
                # 移除空格，处理十六进制字符串
                hex_str = text.replace(' ', '').replace('\n', '').replace('\r', '')
                if len(hex_str) % 2 != 0:
                    raise ValueError("十六进制数据长度错误")
                data = bytes.fromhex(hex_str)
            except Exception as e:
                QMessageBox.warning(self, "格式错误", f"无效的十六进制数据: {str(e)}")
                return
        else:
            data = text.encode('utf-8')
            
        # 添加到发送缓冲区
        self.send_buffer.extend(data)
            
        # 添加新行
        if self.send_newline_cb.isChecked():
            data += b'\r\n'
            
        # 发送数据
        if self.serial_thread.write_data(data):
            # 更新发送计数
            self.send_count += len(data)
            self.send_stats_label.setText(f"发送: {self.send_count} 字节")
            
    def clear_receive(self):
        """清除接收数据"""
        self.receive_text.clear()
        self.receive_count = 0
        self.receive_buffer = bytearray()
        self.receive_stats_label.setText("接收: 0 字节")
        
        # 更新缓冲区信息
        max_buffer_size = self.buffer_settings.get('receive_buffer', 1024 * 1024)  # 1MB
        self.buffer_stats_label.setText(f"缓冲区: 0/{max_buffer_size} 字节")
        
        # 更新行号显示
        self.receive_text.update_line_numbers()
        
    def save_receive_data(self):
        """保存接收数据"""
        if not self.receive_text.toPlainText():
            QMessageBox.warning(self, "警告", "没有接收数据可保存")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存接收数据", "", "文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.receive_text.toPlainText())
                QMessageBox.information(self, "成功", f"接收数据已保存到: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")
                
    def show_serial_settings(self):
        """显示串口设置对话框"""
        baudrate, bytesize, stopbits, parity = self.get_serial_params()
        
        # 将枚举值转换为可读文本
        bytesize_text = {5: "5", 6: "6", 7: "7", 8: "8"}.get(bytesize, "8")
        stopbits_text = {1: "1", 1.5: "1.5", 2: "2"}.get(stopbits, "1")
        parity_text = {serial.PARITY_NONE: "无", serial.PARITY_ODD: "奇校验", 
                      serial.PARITY_EVEN: "偶校验"}.get(parity, "无")
        
        params_text = f"""
        当前串口参数:
        
        端口: {self.port_combo.currentData() or '未选择'}
        波特率: {baudrate}
        数据位: {bytesize_text}
        停止位: {stopbits_text}
        校验位: {parity_text}
        接收超时: {self.buffer_settings.get('receive_timeout', 1.0):.2f} 秒
        发送超时: {self.buffer_settings.get('send_timeout', 1.0):.2f} 秒
        配置区域: {'显示' if self.config_visible else '隐藏'}
        时间戳显示: {'开启' if self.timestamp_cb.isChecked() else '关闭'}
        字体大小: {self.font_size} pt
        
        缓冲区设置:
        接收缓冲区: {self.buffer_settings.get('receive_buffer', 1024 * 1024):.0f} 字节
        发送缓冲区: {self.buffer_settings.get('send_buffer', 1024 * 1024):.0f} 字节
        """
        
        QMessageBox.information(self, "串口设置", params_text)
        
    def show_buffer_settings(self):
        """显示缓冲区设置对话框"""
        dialog = BufferSettingsDialog(self)
        dialog.set_settings(self.buffer_settings)
        
        if dialog.exec_() == QDialog.Accepted:
            new_settings = dialog.get_settings()
            self.buffer_settings.update(new_settings)
            
            # 更新缓冲区显示
            max_buffer_size = self.buffer_settings.get('receive_buffer', 1024 * 1024)  # 1MB
            buffer_bytes = len(self.receive_buffer)
            self.buffer_stats_label.setText(f"缓冲区: {buffer_bytes}/{max_buffer_size} 字节")
            
            QMessageBox.information(self, "成功", "缓冲区设置已更新")
            
    def show_display_settings(self):
        """显示显示设置对话框"""
        settings_text = f"""
        显示设置:
        
        时间戳: {'开启' if self.timestamp_cb.isChecked() else '关闭'}
        十六进制显示: {'开启' if self.hex_display_cb.isChecked() else '关闭'}
        自动滚屏: {'开启' if self.auto_scroll_cb.isChecked() else '关闭'}
        配置区域: {'显示' if self.config_visible else '隐藏'}
        字体大小: {self.font_size} pt
        
        搜索功能:
        查找: {'启用' if self.search_input.text() else '禁用'}
        大小写敏感: {'开启' if self.case_sensitive_cb.isChecked() else '关闭'}
        
        终端背景: 深灰 (#1a1a1a)
        终端文字: 浅灰 (#c0c0c0)
        
        缓冲区设置:
        接收缓冲区: {self.buffer_settings.get('receive_buffer', 1024 * 1024):.0f} 字节
        发送缓冲区: {self.buffer_settings.get('send_buffer', 1024 * 1024):.0f} 字节
        接收超时: {self.buffer_settings.get('receive_timeout', 1.0):.2f} 秒
        发送超时: {self.buffer_settings.get('send_timeout', 1.0):.2f} 秒
        """
        
        QMessageBox.information(self, "显示设置", settings_text)
        
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h3 style="color: #cccccc;">串口工具(精简版) v1.2</h3>
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
            <li><b>日志查找和高亮功能</b></li>
            <li>简洁暗黑主题，护眼设计</li>
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
        <p style="color: #cccccc;"><b>图标使用:</b></p>
        <ul style="color: #aaaaaa;">
            <li>图标文件: serial_port.ico</li>
            <li>图标文件应放置在程序目录下</li>
            <li>显示在窗口左上角和任务栏</li>
        </ul>
        <p style="color: #cccccc;"><b>界面布局:</b></p>
        <ul style="color: #aaaaaa;">
            <li>上方：最大化日志显示区域（含搜索功能）</li>
            <li>下方：串口配置和发送配置（可隐藏）</li>
            <li>工具栏：快速控制配置区域显示/隐藏</li>
            <li>实时统计和缓冲区信息（字节单位）</li>
        </ul>
        <p style="color: #888888;">开发者: 串口工具(精简版)</p>
        <p style="color: #888888;">版本: 1.2.0</p>
        """
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle("关于")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(about_text)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #303030;
                color: #cccccc;
            }
            QLabel {
                color: #cccccc;
            }
        """)
        msg_box.exec_()
        
    def closeEvent(self, event):
        """关闭窗口事件"""
        if self.serial_thread and self.serial_thread.isRunning():
            reply = QMessageBox.question(
                self, '确认退出',
                '串口正在连接，确定要退出吗？',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.disconnect_serial()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 设置应用程序信息
    app.setApplicationName("串口工具(精简版)")
    
    # 设置应用程序图标
    try:
        # 图标文件名
        icon_filename = "serial_port.ico"
        
        # 尝试从当前目录加载图标
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, icon_filename)
        
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            print(f"应用程序图标已设置: {icon_path}")
        else:
            print(f"未找到图标文件: {icon_path}")
    except Exception as e:
        print(f"设置应用程序图标失败: {e}")
    
    # 创建并显示主窗口
    window = SerialTool()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    # 安装依赖: pip install pyserial
    main()