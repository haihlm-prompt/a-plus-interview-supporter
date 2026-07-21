App đã có realease, ae có thể tải file exe về sử dụng trực tiếp.

LƯU Ý: Lần đầu cần khoảng 3-5 phút (tùy thuộc vào mạng) để tải model OCR về cache của máy.


********************************************************************************************************************
Dành cho ae build lại file để nghiên cứu
Cần build trên virtual-environment: 

python -m venv env

env\Scripts\activate


Cài các thư viện bằng:

pip install pyautogui numpy keyboard PyQt6 openai easyocr pyinstaller


Lệnh build file exe:

pyinstaller --noconsole --onefile --icon=app_logo.ico --add-data "app_logo.ico;." aplus_v3.py
