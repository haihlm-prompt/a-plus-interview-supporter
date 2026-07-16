Để build trên máy mới cần build trên virtual-environment: 
python -m venv env
env\Scripts\activate


Cài các thư viện bằng:
pip install pyautogui numpy keyboard PyQt6 openai easyocr pyinstaller


Lệnh build file exe:
pyinstaller --noconsole --onefile --icon=app_logo.ico --add-data "app_logo.ico;." aplus_v3.py
