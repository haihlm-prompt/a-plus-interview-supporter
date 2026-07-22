App đã có realease, ae có thể tải file exe về sử dụng trực tiếp.
PROMPT MẪU THI TIẾNG ANH Ở FPT CÓ THỂ LÀ:

"Tôi là Hải, tôi có 4 năm làm việc trong ngành automotive ở FPT Software. Tôi đang làm bài Mock test Speaking, hãy giúp tôi soạn 1 đoạn văn bằng tiếng anh dựa vào các câu hỏi có trên màn hình để tôi nói kịp trong vòng 40 đến 60 giây."

LƯU Ý: Lần đầu cần khoảng 3-5 phút (tùy thuộc vào mạng) để tải model OCR về cache của máy.

Nhấn phím Esc để thoát app


********************************************************************************************************************
Dành cho ae build lại file để nghiên cứu
Cần build trên virtual-environment: 

python -m venv env

env\Scripts\activate


Cài các thư viện bằng:

pip install pyautogui numpy keyboard PyQt6 openai easyocr pyinstaller


Lệnh build file exe:

pyinstaller --noconsole --onefile --icon=app_logo.ico --add-data "app_logo.ico;." aplus_v3.py
