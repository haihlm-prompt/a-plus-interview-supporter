import sys
import ctypes
import pyautogui
import numpy as np
import keyboard 
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QTimer
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QLabel, QSizeGrip, QScrollArea, QDialog, QTextEdit, 
                             QSlider, QPushButton, QHBoxLayout)
from PyQt6.QtGui import QIcon, QColor

from openai import OpenAI 

ROUTER_API_KEY = "sk-nry-gc2N_aerOiP1dW_sH7AxB2ynHWRAPATU7qFttTotkH8" 
ROUTER_BASE_URL = "https://router.bynara.id/v1"  
ROUTER_MODEL_NAME = "mistral-medium-3-5" 

class OCRInitWorker(QThread):
    init_finished = pyqtSignal(object)
    
    def run(self):
        import easyocr
        reader = easyocr.Reader(['vi', 'en'], gpu=False)
        self.init_finished.emit(reader)

class AIInterviewWorker(QThread):
    ai_response_ready = pyqtSignal(str)

    def __init__(self, system_role):
        super().__init__()
        self.system_role = system_role 
        self.reader = None 
        
        self.client = OpenAI(
            api_key=ROUTER_API_KEY,
            base_url=ROUTER_BASE_URL
        )
        self.last_text = ""

    def run(self):
        try:
            if self.reader is None:
                self.ai_response_ready.emit("Lỗi: Hệ thống nhận diện chữ chưa sẵn sàng.")
                return
                
            screenshot = pyautogui.screenshot()
            img_np = np.array(screenshot)
            results = self.reader.readtext(img_np, detail=0)
            
            if results:
                full_text = " ".join(results).strip()
                
                if full_text != self.last_text and len(full_text) > 10:
                    self.last_text = full_text
                    
                    prompt = f"""
                    {self.system_role}

                    Nội dung màn hình:
                    {full_text}
                    """
                    
                    response_stream = self.client.chat.completions.create(
                        model=ROUTER_MODEL_NAME,  
                        messages=[{"role": "user", "content": prompt}],
                        stream=True
                    )
                    
                    accumulated_response = ""
                    for chunk in response_stream:
                        if chunk.choices and len(chunk.choices) > 0:
                            delta = chunk.choices[0].delta
                            if hasattr(delta, 'content') and delta.content is not None:
                                accumulated_response += delta.content
                                self.ai_response_ready.emit(accumulated_response)
                            
                else:
                    self.ai_response_ready.emit("Không tìm thấy câu hỏi mới hoặc nội dung quá ngắn.")
                        
        except Exception as e:
            self.ai_response_ready.emit(f"Lỗi xử lý: {e}")

class SetupDialog(QDialog):
    def __init__(self, default_role):
        super().__init__()
        self.setWindowTitle("Thiết lập hệ thống")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Vai trò AI:"))
        self.role_input = QTextEdit(default_role)
        layout.addWidget(self.role_input)
        
        layout.addWidget(QLabel("Kéo thanh trượt để chọn màu giao diện:"))
        self.color_slider = QSlider(Qt.Orientation.Horizontal)
        self.color_slider.setRange(0, 359)
        self.color_slider.setValue(120) 
        self.color_slider.valueChanged.connect(self.update_color)
        layout.addWidget(self.color_slider)
        
        self.preview = QLabel("Màu hiển thị")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview)
        
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
        self.update_color(120)
        
    def update_color(self, hue):
        self.color_hex = QColor.fromHsv(hue, 255, 255).name()
        self.preview.setStyleSheet(f"background: rgba(0,0,0,120); color: {self.color_hex}; border: 2px solid {self.color_hex}; border-radius: 5px; padding: 5px; font-weight: bold;")

class CreditScreen(QWidget):
    def __init__(self, color_hex):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(400, 150)

        layout = QVBoxLayout(self)
        
        self.label = QLabel("Dev by mizhai", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(f"""
            color: {color_hex};
            font-size: 32px;
            font-weight: bold;
            font-family: Arial;
            background-color: rgba(0, 0, 0, 120);
            border: 2px solid {color_hex};
            border-radius: 15px;
        """)
        layout.addWidget(self.label)
        self.center_on_screen()

    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

class InterviewOverlay(QMainWindow):
    hotkey_triggered = pyqtSignal()

    def __init__(self, system_role, color_hex):
        super().__init__()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(QIcon("app_logo.ico"))

        self.resize(700, 450) 
        self.setMinimumSize(400, 250)

        self.drag_position = QPoint()

        control_widget = QWidget(self)
        self.setCentralWidget(control_widget)
        layout = QVBoxLayout(control_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        # Đã xóa các dòng ẩn thanh cuộn ở đây
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: rgba(0, 0, 0, 150);
                width: 10px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {color_hex};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        self.label = QLabel("Đang nạp mô hình AI nhận diện chữ (Khoảng 2-5 giây)...\nNếu lần đầu sẽ mất 3-5 phút để download model\nVui lòng chờ trong giây lát.", self)
        self.label.setStyleSheet(f"""
            color: {color_hex};
            font-size: 15px;
            font-weight: bold;
            background-color: rgba(0, 0, 0, 120);
            border: 2px solid {color_hex};
            border-radius: 8px;
            padding: 15px;
        """)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.scroll_area.setWidget(self.label)
        layout.addWidget(self.scroll_area)

        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setFixedSize(10, 10) 
        self.sizegrip.setStyleSheet(f"background-color: {color_hex}; border-radius: 1px;") 

        self.enable_anti_screenshot()

        self.is_ocr_ready = False

        self.worker = AIInterviewWorker(system_role)
        self.worker.ai_response_ready.connect(self.update_text)
        
        self.init_worker = OCRInitWorker()
        self.init_worker.init_finished.connect(self.on_ocr_loaded)
        self.init_worker.start()
        
        self.hotkey_triggered.connect(self.start_processing)
        keyboard.add_hotkey('ctrl+alt+space', self.hotkey_triggered.emit)

    def on_ocr_loaded(self, reader_instance):
        self.worker.reader = reader_instance
        self.is_ocr_ready = True
        self.label.setText("Hệ thống AI đã khởi động thành công!\nNhấn Ctrl + Alt + Space để bắt đầu quét màn hình...")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sizegrip.move(self.width() - self.sizegrip.width(), self.height() - self.sizegrip.height())

    def enable_anti_screenshot(self):
            try:
                hwnd = int(self.winId())
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 17)
            except Exception:
                pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def update_text(self, text):
        self.label.setText(text)

    def start_processing(self):
        if not self.is_ocr_ready:
            self.label.setText("Hệ thống vẫn đang khởi động mô hình AI, vui lòng đợi thêm chút nữa...")
            return

        if not self.worker.isRunning():
            self.label.setText("Đang đọc màn hình và xử lý dữ liệu...")
            self.worker.start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            sys.exit(0)

if __name__ == "__main__":
    try:
        myappid = 'mizhai.interviewassistant.v1' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("app_logo.ico"))
    
    default_role = """ Bạn đang là một trợ lý có nhiệm vụ xem và xử lí các thông tin trên màn hình
    và đưa ra giải pháp để trả lời chúng. """

    dialog = SetupDialog(default_role)
    if dialog.exec() == QDialog.DialogCode.Rejected:
        sys.exit(0)

    system_role = dialog.role_input.toPlainText().strip()
    if not system_role:
        system_role = default_role
        
    app_color = dialog.color_hex
    
    credit_screen = CreditScreen(app_color)
    credit_screen.show()
    
    overlay = InterviewOverlay(system_role, app_color)
    
    def start_main_app():
        credit_screen.close() 
        overlay.show()       
        
    QTimer.singleShot(800, start_main_app)
    
    sys.exit(app.exec())