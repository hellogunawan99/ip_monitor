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
    "192.168.1.2",  # Cloudflare DNS
    "192.168.1.1",  # Cloudflare DNS
    "192.168.1.4",  # Cloudflare DNS
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>IP Monitoring</title>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0;
            padding: 20px;
        }
        .notification-banner {
            position: sticky;
            top: 0;
            background-color: #FFE4E1;
            border: 2px solid #FF6B6B;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            display: none;
        }
        .notification-banner.show {
            display: block;
        }
        .offline-list {
            margin: 0;
            padding-left: 20px;
        }
        .status-card {
            border: 1px solid #ddd;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .online { 
            background-color: #90EE90; 
        }
        .offline { 
            background-color: #FFB6C1; 
        }
        .timestamp {
            color: #666;
            font-size: 0.9em;
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div id="notification-banner" class="notification-banner">
        <h3 style="margin-top: 0;">⚠️ IP Tidak Terhubung:</h3>
        <div id="offline-ips"></div>
    </div>
    
    <h1>IP Monitoring Dashboard</h1>
    <div id="status-container"></div>

    <script>
        function updateNotificationBanner(data) {
            const banner = document.getElementById('notification-banner');
            const offlineIpsDiv = document.getElementById('offline-ips');
            const offlineIps = [];
            
            for (const [ip, status] of Object.entries(data)) {
                if (!status.online) {
                    offlineIps.push(`
                        <li>
                            <strong>${ip}</strong> - Terakhir online: ${status.last_online || 'Tidak diketahui'}
                            <br>
                            <span class="timestamp">Pemeriksaan terakhir: ${status.last_check}</span>
                        </li>
                    `);
                }
            }
            
            if (offlineIps.length > 0) {
                offlineIpsDiv.innerHTML = `<ul class="offline-list">${offlineIps.join('')}</ul>`;
                banner.classList.add('show');
            } else {
                banner.classList.remove('show');
            }
        }

        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    // Update notification banner
                    updateNotificationBanner(data);
                    
                    // Update status cards
                    const container = document.getElementById('status-container');
                    container.innerHTML = '';
                    
                    for (const [ip, status] of Object.entries(data)) {
                        const card = document.createElement('div');
                        card.className = `status-card ${status.online ? 'online' : 'offline'}`;
                        card.innerHTML = `
                            <h3>IP: ${ip}</h3>
                            <p>Status: ${status.online ? 'Online ✅' : 'Offline ❌'}</p>
                            <p>Pemeriksaan Terakhir: ${status.last_check}</p>
                            <p>Waktu Respon: ${status.response_time}ms</p>
                            ${status.last_online ? `<p>Terakhir Online: ${status.last_online}</p>` : ''}
                        `;
                        container.appendChild(card);
                    }
                });
        }

        // Update status setiap 5 detik
        setInterval(updateStatus, 5000);
        updateStatus();
    </script>
</body>
</html>
"""


def check_ip(ip):
    """Fungsi untuk mengecek status IP"""
    try:
        response_time = ping3.ping(ip) * 1000  # Konversi ke milliseconds
        is_online = True if response_time else False

        current_status = ip_status.get(ip, {})
        last_online = None

        # Jika sebelumnya online dan sekarang offline, catat waktu terakhir online
        if current_status.get('online', True) and not is_online:
            last_online = current_status.get(
                'last_check', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        # Jika online, reset last_online
        elif is_online:
            last_online = None
        # Jika masih offline, pertahankan last_online yang ada
        else:
            last_online = current_status.get('last_online')

        return {
            'online': is_online,
            'response_time': f'{response_time:.2f}' if response_time else 'N/A',
            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_online': last_online
        }
    except Exception:
        current_status = ip_status.get(ip, {})
        return {
            'online': False,
            'response_time': 'N/A',
            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_online': current_status.get('last_online') or current_status.get('last_check')
        }


def monitor_ips():
    """Fungsi background untuk monitoring IP"""
    while True:
        for ip in ip_addresses:
            status = check_ip(ip)
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
