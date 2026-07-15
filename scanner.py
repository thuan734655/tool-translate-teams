import mss
import logging
import asyncio

from winrt.windows.media.ocr import OcrEngine
from winrt.windows.globalization import Language
from winrt.windows.graphics.imaging import SoftwareBitmap, BitmapPixelFormat, BitmapAlphaMode
from winrt.windows.security.cryptography import CryptographicBuffer

class ScreenScanner:
    def __init__(self):
        self.sct = mss.mss()
        self.lang = Language("ja")
        
        if not OcrEngine.is_language_supported(self.lang):
            logging.error("Lỗi: Máy tính chưa cài đặt gói ngôn ngữ Tiếng Nhật cho Windows.")
            
        self.engine = OcrEngine.try_create_from_language(self.lang)
        
    def capture_and_recognize(self, region):
        """
        region: tuple (x, y, width, height)
        """
        monitor = {
            "top": int(region[1]), 
            "left": int(region[0]), 
            "width": int(region[2]), 
            "height": int(region[3])
        }
        
        try:
            if not self.engine:
                return ""
                
            # 1. Chụp ảnh vùng màn hình bằng mss
            sct_img = self.sct.grab(monitor)
            
            # 2. Chuyển đổi dữ liệu byte màn hình (BGRA) thành định dạng SoftwareBitmap của Windows
            buf = CryptographicBuffer.create_from_byte_array(sct_img.bgra)
            bitmap = SoftwareBitmap(BitmapPixelFormat.BGRA8, sct_img.width, sct_img.height, BitmapAlphaMode.PREMULTIPLIED)
            bitmap.copy_from_buffer(buf)
            
            # 3. Trích xuất văn bản bằng thuật toán AI cực mạnh của Windows
            async def do_ocr():
                return await self.engine.recognize_async(bitmap)
                
            result = asyncio.run(do_ocr())
            
            if result and result.text:
                # Trả về kết quả, tự động gộp dòng cực tốt nhờ Windows OCR
                # result.text tự động loại bỏ các khoảng trắng dư thừa trong tiếng Nhật
                return result.text.strip()
            return ""
        except Exception as e:
            logging.error(f"Lỗi khi quét ảnh: {e}")
            return ""
