"""
Catprox 监控主程序
整合网络监控、Web看板和弹窗告警
"""

import sys
import time
import threading
from monitor_core import CatproxMonitor
from monitor_dashboard import app, set_alert_callback
from notifier import (
    alert_device_limit_exceeded, 
    alert_service_started,
    alert_service_stopped
)


def alert_handler(status: dict):
    """
    告警处理函数
    
    Args:
        status: 监控状态
    """
    count = status['active_count']
    max_allowed = status['max_allowed']
    
    print(f"\n{'='*60}")
    print(f"🔔 告警触发!")
    print(f"当前活跃设备: {count}/{max_allowed}")
    print(f"时间: {status['timestamp']}")
    print(f"{'='*60}\n")
    
    # 发送Windows弹窗通知
    alert_device_limit_exceeded(status)


def main():
    """主程序入口"""
    
    print("\n" + "="*60)
    print(" Catprox 设备监控系统 v1.0")
    print("="*60)
    print("功能:")
    print("  1. 实时监控Catprox网络连接")
    print("  2. Web看板: http://localhost:5000")
    print("  3. 超限自动弹窗告警")
    print("="*60 + "\n")
    
    # 发送启动通知
    alert_service_started()
    
    # 设置告警回调
    set_alert_callback(alert_handler)
    
    print("\n系统启动中...")
    print("看板地址: http://localhost:5000")
    print("按 Ctrl+C 停止监控\n")
    
    # 直接运行Flask应用(主线程)
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\n正在关闭监控系统...")
        alert_service_stopped()
        print("监控系统已停止")
        sys.exit(0)


if __name__ == '__main__':
    main()
