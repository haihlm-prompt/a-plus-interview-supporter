import sys
import ctypes
import pyautogui
import numpy as np
import keyboard 
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QSizeGrip, QInputDialog
from PyQt6.QtGui import QIcon

from openai import OpenAI 

ROUTER_API_KEY = "sk-nry-gc2N_aerOiP1dW_sH7AxB2ynHWRAPATU7qFttTotkH8" 
ROUTER_BASE_URL = "https://router.bynara.id/v1"  
ROUTER_MODEL_NAME = "mistral-medium-3-5" 

# 1. THÊM LUỒNG NẠP MÔ HÌNH NHẬN DIỆN CHỮ NGẦM
class OCRInitWorker(QThread):
    init_finished = pyqtSignal(object)
    
    def run(self):
        import easyocr
        # Nạp model OCR vào bộ nhớ
        reader = easyocr.Reader(['vi', 'en'], gpu=False)
        # Gửi model đã nạp xong ra ngoài
        self.init_finished.emit(reader)

class AIInterviewWorker(QThread):
    ai_response_ready = pyqtSignal(str)

    def __init__(self, system_role):
        super().__init__()
        self.system_role = system_role # Nhận vai trò được cấu hình
        self.reader = None # Sẽ được cấp phát khi OCRInitWorker chạy xong
        
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
                    
                    # Ghép vai trò với nội dung màn hình
                    prompt = f"""
                    {self.system_role}

                    Nội dung màn hình:
                    {full_text}
                    """
                    
                    response_stream = self.client.chat.completions.create(
                        model=ROUTER_MODEL_NAME,  
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
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
            print(f"Lỗi hệ thống: {e}")
            self.ai_response_ready.emit(f"Lỗi xử lý: {e}")

class CreditScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(400, 150)

        layout = QVBoxLayout(self)
        
        self.label = QLabel("Dev by mizhai", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            color: #39FF14;
            font-size: 32px;
            font-weight: bold;
            font-family: Arial;
            background-color: rgba(0, 0, 0, 120);
            border: 2px solid #39FF14;
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

    def __init__(self, system_role):
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

        # 2. HIỂN THỊ THÔNG BÁO ĐANG NẠP KHI VỪA MỞ APP
        self.label = QLabel("Đang nạp mô hình AI nhận diện chữ (Khoảng 2-5 giây)...\nVui lòng chờ trong giây lát.", self)
        self.label.setStyleSheet("""
            color: #39FF14;
            font-size: 15px;
            font-weight: bold;
            background-color: rgba(0, 0, 0, 120);
            border: 2px solid #39FF14;
            border-radius: 8px;
            padding: 15px;
        """)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.label)

        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setFixedSize(10, 10) 
        self.sizegrip.setStyleSheet("background-color: #39FF14; border-radius: 1px;") 

        self.enable_anti_screenshot()

        # 3. BIẾN CỜ KIỂM SOÁT PHÍM TẮT
        self.is_ocr_ready = False

        # Khởi tạo Worker xử lý chính và truyền vai trò vào
        self.worker = AIInterviewWorker(system_role)
        self.worker.ai_response_ready.connect(self.update_text)
        
        # Khởi chạy luồng nạp OCR ngầm
        self.init_worker = OCRInitWorker()
        self.init_worker.init_finished.connect(self.on_ocr_loaded)
        self.init_worker.start()
        
        self.hotkey_triggered.connect(self.start_processing)
        keyboard.add_hotkey('ctrl+alt+space', self.hotkey_triggered.emit)

    def on_ocr_loaded(self, reader_instance):
        # 4. KHI NẠP XONG, TRUYỀN MODEL VÀO WORKER VÀ MỞ KHÓA
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
            except Exception as e:
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
        # 5. NẾU BẤM PHÍM TẮT LÚC CHƯA NẠP XONG THÌ CHẶN LẠI
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
    # --- HIỂN THỊ ĐÚNG ICON DƯỚI TASKBAR WINDOWS ---
    try:
        myappid = 'mizhai.interviewassistant.v1' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    
    # --- SET ICON CHO TOÀN BỘ APP ---
    app.setWindowIcon(QIcon("app_logo.ico"))
    
    # --- TÍNH NĂNG HỎI VAI TRÒ TRƯỚC KHI VÀO GIAO DIỆN CHÍNH ---
    default_role = """Bạn là trợ lý phỏng vấn thông minh. Phát hiện câu hỏi phỏng vấn trong đoạn văn bản 
quét từ màn hình dưới đây và đưa ra gợi ý trả lời cực kỳ ngắn gọn, súc tích, đi thẳng vào vấn đề.
Không nói linh tinh giải thích để tránh sao nhãn cho người phỏng vấn. Ưu tiên nói tiếng anh trước."""

    role_input, ok = QInputDialog.getText(
        None, 
        "Thiết lập trợ lý AI", 
        "Bạn muốn tôi hỗ trợ bạn trong vai trò nào?\n(Nhấn Enter/OK để dùng mặc định. Nhấn Cancel để thoát.)"
    )

    # --- SỬA LOGIC Ở ĐÂY: NẾU NHẤN CANCEL THÌ THOÁT NGAY ---
    if not ok:
        sys.exit(0)  # Thoát chương trình nếu người dùng chọn Cancel hoặc đóng hộp thoại

    # Nếu người dùng bấm OK/Enter nhưng bỏ trống thì dùng role mặc định
    if not role_input.strip():
        system_role = default_role
    else:
        system_role = role_input.strip()
    
    # --- KHỞI ĐỘNG CÁC GIAO DIỆN ---
    credit_screen = CreditScreen()
    credit_screen.show()
    
    overlay = InterviewOverlay(system_role)
    
    def start_main_app():
        credit_screen.close() 
        overlay.show()       
        
    QTimer.singleShot(800, start_main_app)
    
    sys.exit(app.exec())