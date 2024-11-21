from flask import Flask, render_template_string, jsonify, request, make_response
import ping3
import threading
import time
from datetime import datetime
import hashlib
import json
import os

app = Flask(__name__)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
PASSWORD_HASH = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

IP_FILE = "monitored_ips.json"
ip_status = {}

def load_ip_addresses():
    """Load IP addresses and names from file"""
    try:
        if os.path.exists(IP_FILE):
            with open(IP_FILE, 'r') as f:
                data = json.load(f)
                # Check if the loaded data is a list (old format)
                if isinstance(data, list):
                    # Convert list to dictionary with default names
                    return {ip: f"Server {i+1}" for i, ip in enumerate(data)}
                return data
    except Exception as e:
        print(f"Error loading IP addresses: {e}")
    # Default IPs with names
    return {
        "8.8.8.8": "Google DNS",
        "1.1.1.1": "Cloudflare DNS"
    }

def save_ip_addresses(ips):
    """Save IP addresses and names to file"""
    try:
        with open(IP_FILE, 'w') as f:
            json.dump(ips, f)
    except Exception as e:
        print(f"Error saving IP addresses: {e}")

# Load initial IP addresses
ip_addresses = load_ip_addresses()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>IP Monitoring Dashboard</title>
    <meta charset="UTF-8">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.14.0/Sortable.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        :root {
            --sidebar-width: 300px;
            --header-height: 60px;
            --primary-color: #2563eb;
            --danger-color: #dc2626;
            --success-color: #16a34a;
            --warning-color: #f59e0b;
            --sidebar-bg: #1e293b;
            --main-bg: #f1f5f9;
        }

        body {
            display: flex;
            min-height: 100vh;
            background: var(--main-bg);
        }

        /* Sidebar Styles */
        .sidebar {
            width: var(--sidebar-width);
            background: var(--sidebar-bg);
            color: white;
            padding: 1rem;
            position: fixed;
            height: 100vh;
            overflow-y: auto;
            transition: transform 0.3s ease;
            z-index: 1000;
        }

        /* New sidebar collapsed state */
        .sidebar.collapsed {
            transform: translateX(-100%);
        }

        /* Toggle button styles */
        .sidebar-toggle {
            position: fixed;
            left: var(--sidebar-width);
            top: 1rem;
            background: var(--sidebar-bg);
            color: white;
            border: none;
            padding: 0.5rem;
            cursor: pointer;
            border-radius: 0 0.375rem 0.375rem 0;
            transition: left 0.3s ease;
            z-index: 1000;
        }

        .sidebar-toggle.collapsed {
            left: 0;
        }

        .sidebar-toggle:hover {
            background: #2d3748;
        }

        .sidebar-header {
            padding: 1rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .sidebar-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #e2e8f0;
        }

        /* Main Content Styles */
        .main-content {
            flex: 1;
            margin-left: var(--sidebar-width);
            padding: 2rem;
            transition: margin-left 0.3s ease;
        }

        .main-content.expanded {
            margin-left: 0;
        }

        /* Form Styles */
        .form-group {
            margin-bottom: 1rem;
        }

        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            color: #e2e8f0;
            font-size: 0.875rem;
        }

        .form-control {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #475569;
            border-radius: 0.375rem;
            background: #334155;
            color: white;
            margin-bottom: 0.5rem;
        }

        .form-control:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
        }

        /* Button Styles */
        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 0.375rem;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn-primary {
            background: var(--primary-color);
            color: white;
        }

        .btn-danger {
            background: var(--danger-color);
            color: white;
        }

        .btn:hover {
            opacity: 0.9;
        }

        /* IP List Styles */
        .ip-list {
            margin-top: 1.5rem;
        }

        .ip-item {
            background: #334155;
            padding: 0.75rem;
            border-radius: 0.375rem;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        /* Previous styles remain the same until status-container */
        
        .status-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1rem;
            min-height: 100px;
        }

        .status-card {
            background: white;
            border-radius: 0.5rem;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            cursor: move;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .status-card.online {
            border-left: 4px solid var(--success-color);
            background: #f0fdf4;  /* Light green background */
        }

        .status-card.offline {
            border-left: 4px solid var(--danger-color);
            background: #fef2f2;  /* Light red background */
        }

        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 500;
        }

        .status-badge.online {
            background: var(--success-color);
            color: white;
        }

        .status-badge.offline {
            background: var(--danger-color);
            color: white;
        }

        .status-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .status-card.sortable-ghost {
            opacity: 0.4;
        }

        .status-card.sortable-chosen {
            background: #f8fafc;
        }

        /* Add styles for the name input */
        .ip-name {
            font-size: 0.875rem;
            color: #64748b;
            margin-top: 0.25rem;
        }

        .form-row {
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .form-row .form-control {
            flex: 1;
        }
    </style>
</head>
<body>
    <!-- Sidebar -->
    <button class="sidebar-toggle" onclick="toggleSidebar()">
        <i class="fas fa-bars"></i>
    </button>
    <div class="sidebar">
        <div class="sidebar-header">
            <h2 class="sidebar-title">IP Management</h2>
        </div>

        <div class="form-group">
            <label for="password">Admin Password</label>
            <input type="password" id="password" class="form-control" placeholder="Enter password">
        </div>

        <div class="form-group">
            <div class="form-row">
                <input type="text" id="newIp" class="form-control" placeholder="IP Address (e.g., 8.8.8.8)">
                <input type="text" id="newName" class="form-control" placeholder="Name (e.g., Google DNS)">
            </div>
            <button class="btn btn-primary" onclick="addIp()">
                <i class="fas fa-plus"></i>
                Add IP
            </button>
        </div>

        <div id="error-message" class="message message-error"></div>
        <div id="success-message" class="message message-success"></div>

        <div class="ip-list" id="ip-list">
            <h3 class="sidebar-title">Monitored IPs</h3>
            <!-- IP list will be populated here -->
        </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
        <div id="notification-banner" class="notification-banner">
            <h3 style="margin-top: 0; color: var(--warning-color);">
                <i class="fas fa-exclamation-triangle"></i>
                Offline IPs Detected
            </h3>
            <div id="offline-ips"></div>
        </div>

        <h1 style="margin-bottom: 2rem;">IP Monitoring Dashboard</h1>
        <div id="status-container" class="status-container"></div>
    </div>

    <script>

        // Add this new function for sidebar toggle
        function toggleSidebar() {
            const sidebar = document.querySelector('.sidebar');
            const mainContent = document.querySelector('.main-content');
            const toggleButton = document.querySelector('.sidebar-toggle');
            
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('expanded');
            toggleButton.classList.toggle('collapsed');
            
            // Trigger window resize to adjust Sortable layout
            window.dispatchEvent(new Event('resize'));
        }

        // Initialize Sortable
        let sortable;
        
        function initSortable() {
            const container = document.getElementById('status-container');
            sortable = Sortable.create(container, {
                animation: 150,
                ghostClass: 'sortable-ghost',
                chosenClass: 'sortable-chosen'
            });
        }

        function showMessage(type, message) {
            const messageDiv = document.getElementById(`${type}-message`);
            messageDiv.textContent = message;
            messageDiv.style.display = 'block';
            setTimeout(() => { messageDiv.style.display = 'none'; }, 3000);
        }

        function updateNotificationBanner(data) {
            const banner = document.getElementById('notification-banner');
            const offlineIpsDiv = document.getElementById('offline-ips');
            const offlineIps = [];
            
            for (const [ip, status] of Object.entries(data.status)) {
                if (!status.online) {
                    offlineIps.push(`
                        <div style="margin-top: 0.5rem; padding: 0.5rem 0; border-top: 1px solid rgba(0,0,0,0.1);">
                            <strong>${ip}</strong> - ${data.names[ip]}
                            <div style="color: #64748b; font-size: 0.875rem;">
                                Last online: ${status.last_online || 'Unknown'}
                                <br>
                                Last check: ${status.last_check}
                            </div>
                        </div>
                    `);
                }
            }
            
            if (offlineIps.length > 0) {
                offlineIpsDiv.innerHTML = offlineIps.join('');
                banner.classList.add('show');
            } else {
                banner.classList.remove('show');
            }
        }

        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    updateNotificationBanner(data);
                    
                    const container = document.getElementById('status-container');
                    const existingCards = Array.from(container.children);
                    const newHtml = [];
                    
                    for (const [ip, status] of Object.entries(data.status)) {
                        newHtml.push(`
                            <div class="status-card ${status.online ? 'online' : 'offline'}" data-ip="${ip}">
                                <div class="status-header">
                                    <div>
                                        <span class="status-title">${ip}</span>
                                        <div class="ip-name">${data.names[ip]}</div>
                                    </div>
                                    <span class="status-badge ${status.online ? 'online' : 'offline'}">
                                        ${status.online ? 'Online' : 'Offline'}
                                    </span>
                                </div>
                                <div style="color: #64748b;">
                                    <p><i class="fas fa-clock"></i> Last Check: ${status.last_check}</p>
                                    <p><i class="fas fa-tachometer-alt"></i> Response Time: ${status.response_time}ms</p>
                                    ${status.last_online ? `<p><i class="fas fa-history"></i> Last Online: ${status.last_online}</p>` : ''}
                                </div>
                            </div>
                        `);
                    }

                    // Only update if content has changed
                    const newContent = newHtml.join('');
                    if (container.innerHTML !== newContent) {
                        container.innerHTML = newContent;
                        initSortable();
                    }
                });
        }

        function updateIpList() {
            fetch('/list-ips')
                .then(response => response.json())
                .then(data => {
                    const ipList = document.getElementById('ip-list');
                    ipList.innerHTML = '<h3 class="sidebar-title">Monitored IPs</h3>';
                    
                    for (const [ip, name] of Object.entries(data)) {
                        const ipItem = document.createElement('div');
                        ipItem.className = 'ip-item';
                        ipItem.innerHTML = `
                            <div>
                                <div>${ip}</div>
                                <div class="ip-name">${name}</div>
                            </div>
                            <button class="btn btn-danger" onclick="removeIp('${ip}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        `;
                        ipList.appendChild(ipItem);
                    }
                });
        }

        function addIp() {
            const password = document.getElementById('password').value;
            const newIp = document.getElementById('newIp').value;
            const newName = document.getElementById('newName').value;
            
            fetch('/add-ip', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    password: password,
                    ip: newIp,
                    name: newName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showMessage('success', 'IP successfully added');
                    document.getElementById('newIp').value = '';
                    document.getElementById('newName').value = '';
                    updateIpList();
                } else {
                    showMessage('error', data.message);
                }
            });
        }

        function removeIp(ip) {
            const password = document.getElementById('password').value;
            
            fetch('/remove-ip', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    password: password,
                    ip: ip
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showMessage('success', 'IP successfully removed');
                    updateIpList();
                } else {
                    showMessage('error', data.message);
                }
            });
        }

        // Update status every 5 seconds
        setInterval(updateStatus, 5000);
        updateStatus();
        updateIpList();
        initSortable();
    </script>
</body>
</html>
"""

def check_ip(ip):
    """Fungsi untuk mengecek status IP"""
    try:
        response_time = ping3.ping(ip) * 1000
        is_online = True if response_time else False

        current_status = ip_status.get(ip, {})
        last_online = None

        if current_status.get('online', True) and not is_online:
            last_online = current_status.get(
                'last_check', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        elif is_online:
            last_online = None
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

# Update monitor_ips function
def monitor_ips():
    """Fungsi background untuk monitoring IP"""
    while True:
        for ip in list(ip_addresses.keys()):  # Convert to list to avoid runtime modification issues
            status = check_ip(ip)
            ip_status[ip] = status
        time.sleep(5)

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def status():
    return jsonify({
        'status': ip_status,
        'names': ip_addresses
    })

@app.route('/list-ips')
def list_ips():
    return jsonify(ip_addresses)

@app.route('/add-ip', methods=['POST'])
def add_ip():
    data = request.get_json()
    password = data.get('password')
    ip = data.get('ip')
    name = data.get('name')

    if not password or not ip or not name:
        return jsonify({'success': False, 'message': 'Password, IP, and name are required'})

    if hashlib.sha256(password.encode()).hexdigest() != PASSWORD_HASH:
        return jsonify({'success': False, 'message': 'Invalid password'})

    if not validate_ip(ip):
        return jsonify({'success': False, 'message': 'Invalid IP format'})

    if ip in ip_addresses:
        return jsonify({'success': False, 'message': 'IP already exists'})

    ip_addresses[ip] = name
    save_ip_addresses(ip_addresses)
    return jsonify({'success': True})

@app.route('/remove-ip', methods=['POST'])
def remove_ip():
    data = request.get_json()
    password = data.get('password')
    ip = data.get('ip')

    if not password or not ip:
        return jsonify({'success': False, 'message': 'Password and IP required'})

    if hashlib.sha256(password.encode()).hexdigest() != PASSWORD_HASH:
        return jsonify({'success': False, 'message': 'Invalid password'})

    if ip not in ip_addresses:
        return jsonify({'success': False, 'message': 'IP not found'})

    del ip_addresses[ip]
    if ip in ip_status:
        del ip_status[ip]
    save_ip_addresses(ip_addresses)
    return jsonify({'success': True})

if __name__ == '__main__':
    monitor_thread = threading.Thread(target=monitor_ips, daemon=True)
    monitor_thread.start()
    app.run(debug=True, host='0.0.0.0', port=3000)