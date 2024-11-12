from flask import Flask, render_template_string, jsonify
import ping3
import threading
import time
from datetime import datetime

app = Flask(__name__)

# Menyimpan status IP
ip_status = {}
# Daftar IP yang akan dimonitor
ip_addresses = [
    "8.8.8.8",  # Google DNS
    "1.1.1.1",  # Cloudflare DNS
    "192.168.1.2",  # test
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>IP Monitoring</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .status-card {
            border: 1px solid #ddd;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .online { background-color: #90EE90; }
        .offline { background-color: #FFB6C1; }
    </style>
</head>
<body>
    <h1>IP Monitoring Dashboard</h1>
    <div id="status-container"></div>

    <script>
        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('status-container');
                    container.innerHTML = '';
                    
                    for (const [ip, status] of Object.entries(data)) {
                        const card = document.createElement('div');
                        card.className = `status-card ${status.online ? 'online' : 'offline'}`;
                        card.innerHTML = `
                            <h3>IP: ${ip}</h3>
                            <p>Status: ${status.online ? 'Online' : 'Offline'}</p>
                            <p>Last Check: ${status.last_check}</p>
                            <p>Response Time: ${status.response_time}ms</p>
                        `;
                        container.appendChild(card);
                    }
                });
        }

        // Update status setiap 5 detik
        setInterval(updateStatus, 5000);
        updateStatus();

        // Mendaftarkan untuk notifikasi
        if ('Notification' in window) {
            Notification.requestPermission();
        }
    </script>
</body>
</html>
"""


def check_ip(ip):
    """Fungsi untuk mengecek status IP"""
    try:
        response_time = ping3.ping(ip) * 1000  # Konversi ke milliseconds
        return {
            'online': True if response_time else False,
            'response_time': f'{response_time:.2f}' if response_time else 'N/A',
            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception:
        return {
            'online': False,
            'response_time': 'N/A',
            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


def monitor_ips():
    """Fungsi background untuk monitoring IP"""
    while True:
        for ip in ip_addresses:
            status = check_ip(ip)
            previous_status = ip_status.get(ip, {}).get('online', True)

            if previous_status and not status['online']:
                print(f"⚠️ Alert: {ip} is down!")
                # Di sini Anda bisa menambahkan notifikasi tambahan (email, SMS, dll)

            ip_status[ip] = status
        time.sleep(5)


@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)


@app.route('/status')
def status():
    return jsonify(ip_status)


if __name__ == '__main__':
    # Memulai thread monitoring
    monitor_thread = threading.Thread(target=monitor_ips, daemon=True)
    monitor_thread.start()

    # Menjalankan aplikasi Flask
    app.run(debug=True, host='0.0.0.0', port=5010)
