from deep_translator import GoogleTranslator
import logging

logging.basicConfig(level=logging.INFO)

class SubtitleTranslator:
    def __init__(self, source_lang='en', target_lang='vi'):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
        self.last_text = ""

    def translate(self, text):
        text = text.strip()
        if not text:
            return ""
            
        # Dọn dẹp khoảng trắng dư thừa và ngắt dòng
        text = text.replace('\n', ' ').strip()
        
        # Bỏ qua nếu chữ giống hệt lần quét trước
        if text == self.last_text:
            return None 

        try:
            translated = self.translator.translate(text)
            self.last_text = text
            return translated
        except Exception as e:
            logging.error(f"Translation error: {e}")
            return "Lỗi dịch thuật..."
