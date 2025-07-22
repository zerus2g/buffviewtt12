from flask import Flask, request, jsonify
import os
import threading
import time
from view import auto_loop_multi, load_links_from_file, load_proxies_from_file

app = Flask(__name__)

# Biến toàn cục để kiểm soát trạng thái của tiến trình buff view
buff_thread = None
is_running = False

@app.route('/')
def home():
    return "TikTok Buff View Service is running. Access /start to start the buffing process."

@app.route('/start', methods=['GET'])
def start_buff_process():
    global buff_thread, is_running

    if is_running:
        return jsonify({"status": "error", "message": "Buff process is already running."}), 409

    delay_sec = int(request.args.get('delay', 60))
    max_workers = int(request.args.get('workers', 50))
    requests_per_link = int(request.args.get('requests_per_link', 100))

    links_file_path = os.getenv("LINKS_FILE", "links.txt")
    proxies_file_path = os.getenv("PROXIES_FILE", "proxies.txt")

    # Lấy link mặc định từ biến môi trường
    default_tiktok_link = os.getenv("DEFAULT_TIKTOK_LINK", "")

    links = load_links_from_file(links_file_path)
    # Nếu file links.txt rỗng hoặc không tồn tại, sử dụng link mặc định từ biến môi trường
    if not links and default_tiktok_link:
        links = [default_tiktok_link]

    proxies = load_proxies_from_file(proxies_file_path)

    if not links:
        return jsonify({"status": "error", "message": "No valid links found. Please check LINKS_FILE or DEFAULT_TIKTOK_LINK environment variable."}), 400

    def run_buff():
        global is_running
        is_running = True
        try:
            auto_loop_multi(links, delay_sec, max_workers, proxies if proxies else None, requests_per_link)
        except Exception as e:
            print(f"Error in buff process: {e}")
        finally:
            is_running = False

    buff_thread = threading.Thread(target=run_buff)
    buff_thread.daemon = True
    buff_thread.start()

    return jsonify({"status": "success", "message": "Buff process started in background."}), 200

@app.route('/status', methods=['GET'])
def get_status():
    global is_running
    return jsonify({"status": "running" if is_running else "idle"})

if __name__ == '__main__':
    # Vẫn giữ việc tạo file trống nếu chúng không tồn tại, để tránh lỗi khi đọc file rỗng.
    # Logic để ghi link mặc định sẽ được xử lý trong hàm start_buff_process khi 'links' rỗng.
    if not os.path.exists("links.txt"):
        with open("links.txt", "w") as f:
            f.write("") # Tạo file rỗng

    if not os.path.exists("proxies.txt"):
        with open("proxies.txt", "w") as f:
            f.write("") # Tạo file rỗng

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)