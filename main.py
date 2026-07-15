import sys
import threading
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QSizeGrip, QTextEdit
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor

from scanner import ScreenScanner
from translator import SubtitleTranslator

class WorkerSignals(QObject):
    translation_ready = pyqtSignal(str, str)

class OCRWorker(threading.Thread):
    def __init__(self, scanner, translator, region, signals):
        super().__init__()
        self.scanner = scanner
        self.translator = translator
        self.region = region
        self.signals = signals
        self.running = True
        self.daemon = True

    def run(self):
        while self.running:
            text = self.scanner.capture_and_recognize(self.region)
            if text:
                translated = self.translator.translate(text)
                if translated:
                    # Ghi thêm vào file log trên máy
                    try:
                        with open("scanned_text.log", "a", encoding="utf-8") as f:
                            f.write(f"JP: {text}\nVI: {translated}\n---\n")
                    except Exception as e:
                        print("Lỗi ghi file:", e)
                        
                    self.signals.translation_ready.emit(text, translated)
            # Quét mỗi giây 1 lần
            time.sleep(1.0) 

    def stop(self):
        self.running = False

class TranslationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bản dịch")
        self.setGeometry(100, 350, 800, 300)
        
        # Cửa sổ luôn nổi trên cùng
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 200);")
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.layout = QVBoxLayout(self.central_widget)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("""
            QTextEdit {
                color: #FFEB3B;
                font-size: 20px;
                font-weight: bold;
                border: none;
                background-color: transparent;
            }
        """)
        self.layout.addWidget(self.log_area)

    def update_text(self, original, translated):
        # Thêm nội dung mới vào danh sách dạng log
        html = f"<div style='margin-bottom: 15px;'><span style='color: #4CAF50;'>[Tiếng Nhật]: {original}</span><br><span style='color: #FFEB3B;'>[Tiếng Việt]: {translated}</span></div>"
        self.log_area.append(html)
        
        # Tự động cuộn xuống dưới cùng
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

class OverlayWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Teams Auto Translator - Khung Quét")
        self.setGeometry(100, 100, 800, 200)
        
        # Xóa viền cửa sổ và luôn nổi trên cùng
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Viền màu xanh lá để người dùng dễ nhìn thấy khung chọn
        self.central_widget.setStyleSheet("""
            QWidget {
                border: 3px solid #00FF00;
                background-color: rgba(0, 0, 0, 40);
                border-radius: 10px;
            }
        """)

        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Thanh tiêu đề (màu đen đặc để tránh người dùng đặt đè lên chữ)
        self.top_bar = QWidget()
        self.top_bar.setStyleSheet("background-color: rgba(0, 0, 0, 255); border-top-left-radius: 10px; border-top-right-radius: 10px;")
        self.controls_layout = QHBoxLayout(self.top_bar)
        self.controls_layout.setContentsMargins(10, 10, 10, 10)
        
        self.drag_label = QLabel("Kéo khung này đè lên vùng phụ đề")
        self.drag_label.setStyleSheet("color: white; font-weight: bold; background-color: transparent; border: none;")
        
        self.start_btn = QPushButton("Bắt đầu Dịch")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; 
                color: white; 
                border: none; 
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.start_btn.clicked.connect(self.toggle_translation)
        
        self.close_btn = QPushButton("Đóng")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336; 
                color: white; 
                border: none; 
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        
        self.controls_layout.addWidget(self.drag_label)
        self.controls_layout.addStretch()
        self.controls_layout.addWidget(self.start_btn)
        self.controls_layout.addWidget(self.close_btn)
        
        self.layout.addWidget(self.top_bar)
        
        # Vùng trống ở giữa (để thấy xuyên qua)
        self.layout.addStretch()
        
        # Nút để kéo dãn kích thước cửa sổ ở góc dưới phải
        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("background-color: transparent; border: none; width: 20px; height: 20px;")
        self.layout.addWidget(self.sizegrip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        # Trạng thái
        self.is_running = False
        self.worker = None
        self.old_pos = None
        
        # Cửa sổ hiển thị bản dịch
        self.translation_window = TranslationWindow()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def toggle_translation(self):
        if not self.is_running:
            self.is_running = True
            self.start_btn.setText("Dừng Dịch")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800; 
                    color: white; border: none; 
                    padding: 8px 15px; border-radius: 5px; font-weight: bold;
                }
            """)
            
            # Hiển thị cửa sổ bản dịch
            self.translation_window.show()
            self.translation_window.log_area.clear()
            self.translation_window.update_text("Hệ thống", "Đang tải dữ liệu và chờ phụ đề...")
            
            self.drag_label.hide()
            self.central_widget.setStyleSheet("""
                QWidget {
                    border: 3px solid #FF0000;
                    background-color: rgba(0, 0, 0, 0);
                    border-radius: 10px;
                }
            """)
            # Tính toán vị trí chụp (bỏ qua phần chứa các nút bấm ở trên)
            geo = self.geometry()
            ctrl_h = self.top_bar.height()
            if ctrl_h < 10: ctrl_h = 45
            region = (geo.x() + 5, geo.y() + ctrl_h, geo.width() - 10, geo.height() - ctrl_h - 5)
            
            self.signals = WorkerSignals()
            self.signals.translation_ready.connect(self.translation_window.update_text)
            
            scanner = ScreenScanner()
            translator = SubtitleTranslator(source_lang='ja', target_lang='vi')
            
            self.worker = OCRWorker(scanner, translator, region, self.signals)
            self.worker.start()
        else:
            self.is_running = False
            self.drag_label.show()
            self.central_widget.setStyleSheet("""
                QWidget {
                    border: 3px solid #00FF00;
                    background-color: rgba(0, 0, 0, 40);
                    border-radius: 10px;
                }
            """)
            self.start_btn.setText("Bắt đầu Dịch")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3; 
                    color: white; border: none; 
                    padding: 8px 15px; border-radius: 5px; font-weight: bold;
                }
            """)
            if self.worker:
                self.worker.stop()
                self.worker = None
                self.translation_window.update_text("Hệ thống", "Đã dừng dịch.")

    def closeEvent(self, event):
        if self.worker:
            self.worker.stop()
        self.translation_window.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OverlayWindow()
    window.show()
    sys.exit(app.exec())
