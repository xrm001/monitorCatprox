"""
Catprox 监控看板服务器
提供Web界面和API接口
"""

from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import threading
import time
from monitor_core import CatproxMonitor

app = Flask(__name__)
CORS(app)  # 允许跨域访问

# 初始化监控器
monitor = CatproxMonitor(threshold=6)

# 告警回调函数
alert_callback = None


def set_alert_callback(callback):
    """设置告警回调函数"""
    global alert_callback
    alert_callback = callback


def background_monitor():
    """后台监控线程"""
    while True:
        if monitor.should_alert():
            status = monitor.get_status()
            if alert_callback:
                alert_callback(status)
        time.sleep(10)  # 每10秒检查一次


# 启动后台监控线程
monitor_thread = threading.Thread(target=background_monitor, daemon=True)
monitor_thread.start()


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
        
        .connections-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        .connections-table th {
            background: #f5f5f5;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #e0e0e0;
        }
        
        .connections-table td {
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
            color: #666;
        }
        
        .connections-table tr:hover {
            background: #f9f9f9;
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
        
        .no-connections {
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> Catprox 设备监控看板</h1>
            <p>实时监控账号设备使用情况</p>
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
                    <div class="info-label">进程状态</div>
                    <div class="info-value" id="processStatus">-</div>
                </div>
                <div class="info-item">
                    <div class="info-label">告警阈值</div>
                    <div class="info-value" id="thresholdInfo">-</div>
                </div>
                <div class="info-item">
                    <div class="info-label">更新时间</div>
                    <div class="info-value" id="updateTime">-</div>
                </div>
            </div>
            
            <h3 style="margin-top: 30px; margin-bottom: 15px; color: #333;">连接详情</h3>
            <div id="connectionsContainer">
                <div class="no-connections">暂无连接数据</div>
            </div>
        </div>
        
        <div class="refresh-info">
            每 5 秒自动刷新 • 数据来自网络连接监控
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
                    if (data.status === 'danger') {
                        statusIndicator.className = 'status-indicator status-danger';
                        statusIndicator.textContent = '⚠️ 超出限制!';
                    } else if (data.status === 'warning') {
                        statusIndicator.className = 'status-indicator status-warning';
                        statusIndicator.textContent = '⚠️ 接近上限';
                    } else {
                        statusIndicator.className = 'status-indicator status-normal';
                        statusIndicator.textContent = '✅ 正常';
                    }
                    
                    // 更新信息
                    document.getElementById('processStatus').textContent = 
                        data.process_running ? '✅ 运行中' : ' 未运行';
                    document.getElementById('thresholdInfo').textContent = 
                        `${data.threshold} (预留${data.max_allowed - data.threshold}台)`;
                    document.getElementById('updateTime').textContent = data.timestamp;
                    
                    // 更新连接列表
                    const container = document.getElementById('connectionsContainer');
                    if (data.connections && data.connections.length > 0) {
                        let html = '<table class="connections-table">';
                        html += '<thead><tr><th>#</th><th>本地端口</th><th>远程地址</th><th>远程端口</th><th>首次连接</th><th>持续时长</th></tr></thead>';
                        html += '<tbody>';
                        
                        data.connections.forEach((conn, index) => {
                            const minutes = Math.floor(conn.duration / 60);
                            const seconds = conn.duration % 60;
                            html += `<tr>
                                <td>${index + 1}</td>
                                <td>${conn.local_port}</td>
                                <td>${conn.remote_addr}</td>
                                <td>${conn.remote_port}</td>
                                <td>${conn.first_seen}</td>
                                <td>${minutes}分${seconds}秒</td>
                            </tr>`;
                        });
                        
                        html += '</tbody></table>';
                        container.innerHTML = html;
                    } else {
                        container.innerHTML = '<div class="no-connections">暂无活跃连接</div>';
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


@app.route('/')
def dashboard():
    """主看板页面"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/status')
def api_status():
    """API: 获取监控状态"""
    return jsonify(monitor.get_status())


@app.route('/api/connections')
def api_connections():
    """API: 获取连接详情"""
    return jsonify(monitor.get_connection_details())


@app.route('/api/test-alert', methods=['POST'])
def test_alert():
    """API: 测试告警功能"""
    status = monitor.get_status()
    status['active_count'] = 7  # 模拟超限
    if alert_callback:
        alert_callback(status)
    return jsonify({'message': '告警已触发'})


if __name__ == '__main__':
    print("=" * 50)
    print(" Catprox 监控看板服务器启动中...")
    print("=" * 50)
    print("📊 看板地址: http://localhost:5000")
    print("🔌 API接口: http://localhost:5000/api/status")
    print("=" * 50)
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
