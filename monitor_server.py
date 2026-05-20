"""
Catprox 分布式监控系统 - 服务端
部署在你的电脑上,接收所有客户端的心跳并展示监控看板
"""

from flask import Flask, request, render_template_string, jsonify
from flask_cors import CORS
import time
import threading
from datetime import datetime
from notifier import alert_device_limit_exceeded, alert_service_started

app = Flask(__name__)
CORS(app)

# 存储在线设备数据: {设备名: {"last_seen": 时间戳, "ip": IP地址}}
active_devices = {}

# 配置
TIMEOUT = 120  # 超时时间(秒),120秒没收到心跳认为离线
THRESHOLD = 6  # 告警阈值(默认6,留2台余量)
MAX_DEVICES = 8  # 最大允许设备数

# 告警状态
alert_triggered = False
last_alert_time = 0
alert_cooldown = 300  # 告警冷却时间(秒)

# 导入通知器
notifier_available = False
try:
    from notifier import notifier
    notifier_available = True
except:
    pass

# HTML看板模板
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Catprox 设备监控看板</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 32px;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 14px;
        }
        
        .stats-card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        
        .count-display {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .count-number {
            font-size: 72px;
            font-weight: bold;
            color: #667eea;
            line-height: 1;
        }
        
        .count-label {
            font-size: 18px;
            color: #666;
            margin-top: 10px;
        }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin: 20px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            transition: width 0.5s ease, background 0.5s ease;
        }
        
        .progress-fill.warning {
            background: linear-gradient(90deg, #FF9800, #FF5722);
        }
        
        .progress-fill.danger {
            background: linear-gradient(90deg, #f44336, #e91e63);
        }
        
        .status-indicator {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }
        
        .status-normal {
            background: #e8f5e9;
            color: #4CAF50;
        }
        
        .status-warning {
            background: #fff3e0;
            color: #FF9800;
        }
        
        .status-danger {
            background: #ffebee;
            color: #f44336;
        }
        
        .device-list {
            margin-top: 30px;
        }
        
        .device-list h3 {
            color: #333;
            margin-bottom: 15px;
        }
        
        .device-item {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .device-name {
            font-weight: 600;
            color: #333;
        }
        
        .device-ip {
            color: #666;
            font-size: 12px;
        }
        
        .device-time {
            color: #999;
            font-size: 12px;
        }
        
        .device-status {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .status-online {
            background: #e8f5e9;
            color: #4CAF50;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .info-item {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 8px;
        }
        
        .info-label {
            font-size: 12px;
            color: #999;
            margin-bottom: 5px;
        }
        
        .info-value {
            font-size: 16px;
            font-weight: 600;
            color: #333;
        }
        
        .no-devices {
            text-align: center;
            color: #999;
            padding: 40px;
            font-size: 14px;
        }
        
        .refresh-info {
            text-align: center;
            color: rgba(255,255,255,0.7);
            margin-top: 20px;
            font-size: 12px;
        }
        
        .alert-banner {
            background: #ffebee;
            border-left: 4px solid #f44336;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
            display: none;
        }
        
        .alert-banner.show {
            display: block;
        }
        
        .alert-banner h4 {
            color: #f44336;
            margin-bottom: 5px;
        }
        
        .alert-banner p {
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Catprox 设备监控看板</h1>
            <p>实时监控账号设备使用情况</p>
        </div>
        
        <div class="alert-banner" id="alertBanner">
            <h4>⚠️ 设备超限告警!</h4>
            <p id="alertMessage">当前设备数已超过限制,可能影响正常使用!</p>
        </div>
        
        <div class="stats-card">
            <div class="count-display">
                <div class="count-number" id="activeCount">-</div>
                <div class="count-label">当前活跃设备数 / 8</div>
            </div>
            
            <div class="progress-bar">
                <div class="progress-fill" id="progressBar" style="width: 0%"></div>
            </div>
            
            <div style="text-align: center;">
                <span class="status-indicator" id="statusIndicator">加载中...</span>
            </div>
            
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">告警阈值</div>
                    <div class="info-value" id="thresholdInfo">6 (预留2台)</div>
                </div>
                <div class="info-item">
                    <div class="info-label">超时时间</div>
                    <div class="info-value">120秒</div>
                </div>
                <div class="info-item">
                    <div class="info-label">更新时间</div>
                    <div class="info-value" id="updateTime">-</div>
                </div>
            </div>
            
            <div class="device-list">
                <h3>📱 在线设备列表</h3>
                <div id="deviceContainer">
                    <div class="no-devices">暂无设备在线</div>
                </div>
            </div>
        </div>
        
        <div class="refresh-info">
            每 5 秒自动刷新 • 客户端每60秒发送心跳
        </div>
    </div>
    
    <script>
        function updateDashboard() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // 更新计数
                    document.getElementById('activeCount').textContent = data.active_count;
                    
                    // 更新进度条
                    const percentage = (data.active_count / data.max_allowed) * 100;
                    const progressBar = document.getElementById('progressBar');
                    progressBar.style.width = percentage + '%';
                    
                    // 根据数量更新颜色
                    progressBar.className = 'progress-fill';
                    if (data.active_count > data.max_allowed) {
                        progressBar.classList.add('danger');
                    } else if (data.active_count > data.threshold) {
                        progressBar.classList.add('warning');
                    }
                    
                    // 更新状态指示器
                    const statusIndicator = document.getElementById('statusIndicator');
                    if (data.active_count > data.max_allowed) {
                        statusIndicator.className = 'status-indicator status-danger';
                        statusIndicator.textContent = '⚠️ 超出限制!';
                    } else if (data.active_count > data.threshold) {
                        statusIndicator.className = 'status-indicator status-warning';
                        statusIndicator.textContent = '⚠️ 接近上限';
                    } else {
                        statusIndicator.className = 'status-indicator status-normal';
                        statusIndicator.textContent = '✅ 正常';
                    }
                    
                    // 更新告警横幅
                    const alertBanner = document.getElementById('alertBanner');
                    const alertMessage = document.getElementById('alertMessage');
                    if (data.alert_triggered) {
                        alertBanner.classList.add('show');
                        alertMessage.textContent = `当前${data.active_count}台设备,超过阈值${data.threshold}台!`;
                    } else {
                        alertBanner.classList.remove('show');
                    }
                    
                    // 更新时间
                    document.getElementById('updateTime').textContent = data.timestamp;
                    
                    // 更新设备列表
                    const container = document.getElementById('deviceContainer');
                    if (data.devices && Object.keys(data.devices).length > 0) {
                        let html = '';
                        Object.entries(data.devices).forEach(([name, info]) => {
                            const lastSeen = new Date(info.last_seen * 1000);
                            const timeStr = lastSeen.toLocaleTimeString('zh-CN');
                            html += `
                                <div class="device-item">
                                    <div>
                                        <div class="device-name">💻 ${name}</div>
                                        <div class="device-ip">IP: ${info.ip}</div>
                                    </div>
                                    <div style="text-align: right;">
                                        <div class="device-status status-online">● 在线</div>
                                        <div class="device-time">最后心跳: ${timeStr}</div>
                                    </div>
                                </div>
                            `;
                        });
                        container.innerHTML = html;
                    } else {
                        container.innerHTML = '<div class="no-devices">暂无设备在线</div>';
                    }
                })
                .catch(error => {
                    console.error('获取数据失败:', error);
                });
        }
        
        // 初始加载
        updateDashboard();
        
        // 每5秒刷新
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
"""


@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    """接收客户端心跳"""
    data = request.json
    hostname = data.get('hostname')
    
    if hostname:
        active_devices[hostname] = {
            "last_seen": time.time(),
            "ip": request.remote_addr
        }
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 收到心跳: {hostname} ({request.remote_addr})")
    
    return jsonify({"status": "ok"})


@app.route('/')
def dashboard():
    """主看板页面"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/status')
def api_status():
    """API: 获取监控状态"""
    global alert_triggered, last_alert_time
    
    now = time.time()
    
    # 清理超时设备
    to_delete = [name for name, info in active_devices.items() 
                 if now - info['last_seen'] > TIMEOUT]
    for name in to_delete:
        del active_devices[name]
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 设备超时下线: {name}")
    
    count = len(active_devices)
    
    return jsonify({
        "active_count": count,
        "threshold": THRESHOLD,
        "max_allowed": MAX_DEVICES,
        "alert_triggered": alert_triggered,
        "devices": active_devices,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


def check_alerts():
    """后台告警检查线程"""
    global alert_triggered, last_alert_time
    
    while True:
        time.sleep(10)  # 每10秒检查一次
        
        now = time.time()
        count = len(active_devices)
        
        # 判断是否需要告警
        if count > THRESHOLD and (now - last_alert_time > alert_cooldown):
            alert_triggered = True
            last_alert_time = now
            
            print(f"\n{'='*60}")
            print(f"🔔 告警触发! 当前设备数: {count}/{MAX_DEVICES}")
            print(f"{'='*60}\n")
            
            # 发送弹窗通知
            if notifier_available:
                alert_device_limit_exceeded(count, MAX_DEVICES, THRESHOLD)
        elif count <= THRESHOLD:
            alert_triggered = False


# 启动后台告警检查线程
alert_thread = threading.Thread(target=check_alerts, daemon=True)
alert_thread.start()


@app.route('/api/devices')
def api_devices():
    """API: 获取设备列表"""
    return jsonify(active_devices)


if __name__ == '__main__':
    print("=" * 60)
    print(" Catprox 分布式监控系统 - 服务端")
    print("=" * 60)
    print(f"看板地址: http://localhost:5000")
    print(f"局域网地址: 需要查看你的IP")
    print(f"告警阈值: {THRESHOLD} 台设备")
    print(f"超时时间: {TIMEOUT} 秒")
    print("=" * 60)
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    # 发送启动通知
    if notifier_available:
        alert_service_started()
    
    app.run(host='0.0.0.0', port=5000, debug=False)
