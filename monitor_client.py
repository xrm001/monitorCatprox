"""
Catprox 分布式监控系统 - 客户端
部署在每台使用Catprox的电脑上,检测进程并发送心跳

首次运行会弹出窗口让用户输入服务器IP
"""

import time
import requests
import psutil
import socket
import os
import sys
from datetime import datetime

# 单实例运行 - 防止重复启动
import tempfile
import win32api
import win32event
import winerror

SINGLE_INSTANCE_MUTEX = "CatproxMonitor_SingleInstance_Mutex"
mutex = win32event.CreateMutex(None, False, SINGLE_INSTANCE_MUTEX)
if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
    print("❌ 程序已在运行中,请勿重复启动!")
    sys.exit(0)

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.txt")

# 默认配置
DEFAULT_SERVER_IP = "192.168.8.97"
SERVER_PORT = 5000

# 监控的进程名称
PROCESS_NAME = "Catprox.exe"

# 心跳发送间隔(秒)
INTERVAL = 60


def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return f.read().strip()
        except:
            pass
    return None


def save_config(ip):
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            f.write(ip)
    except:
        pass


def get_config_with_gui():
    """通过GUI获取服务器IP配置"""
    # 尝试使用tkinter弹出窗口
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        return None
    
    saved_ip = load_config()
    
    root = tk.Tk()
    root.title("Catprox 监控客户端配置")
    root.geometry("400x200")
    root.resizable(False, False)
    
    # 居中显示
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (400 // 2)
    y = (root.winfo_screenheight() // 2) - (200 // 2)
    root.geometry(f"400x200+{x}+{y}")
    
    # 标签
    tk.Label(root, text="请输入监控服务器IP地址:", font=("Arial", 12)).pack(pady=20)
    
    # 输入框
    ip_var = tk.StringVar(value=saved_ip if saved_ip else DEFAULT_SERVER_IP)
    entry = ttk.Entry(root, textvariable=ip_var, width=30, font=("Arial", 12))
    entry.pack(pady=10)
    entry.focus()
    
    def on_ok():
        ip = ip_var.get().strip()
        if ip:
            save_config(ip)
            root.server_ip = ip
            root.destroy()
    
    def on_cancel():
        root.server_ip = None
        root.destroy()
    
    # 按钮
    btn_frame = ttk.Frame(root)
    btn_frame.pack(pady=20)
    ttk.Button(btn_frame, text="确定", command=on_ok, width=10).pack(side="left", padx=10)
    ttk.Button(btn_frame, text="取消", command=on_cancel, width=10).pack(side="left", padx=10)
    
    # 回车确认
    entry.bind("<Return>", lambda e: on_ok())
    
    root.mainloop()
    
    return getattr(root, 'server_ip', None)


def get_config():
    """获取配置,优先使用GUI,失败则用配置文件或默认值"""
    # 先尝试加载保存的配置
    saved_ip = load_config()
    if saved_ip:
        return saved_ip
    
    # 尝试GUI
    ip = get_config_with_gui()
    if ip:
        return ip
    
    # 如果无法使用GUI,返回默认IP
    print("⚠️ 无法显示配置窗口,将使用默认IP或已保存的配置")
    return saved_ip if saved_ip else DEFAULT_SERVER_IP


def is_process_running(process_name):
    """检测特定名称的进程是否在运行"""
    for proc in psutil.process_iter(['name']):
        try:
            if process_name.lower() in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def get_hostname():
    """获取本机名称"""
    return socket.gethostname()


def send_heartbeat(server_ip):
    """向服务端发送在线状态"""
    url = f"http://{server_ip}:{SERVER_PORT}/heartbeat"
    payload = {
        "hostname": get_hostname(),
        "status": "online"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 心跳上报成功 - {server_ip}")
            return True
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 无法连接服务器 {server_ip}: {e}")
    
    return False


def main():
    """主程序"""
    # 获取服务器IP配置
    SERVER_IP = get_config()
    
    if not SERVER_IP:
        print("❌ 未配置服务器IP,程序退出")
        input("按回车键退出...")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print(" Catprox 状态监控客户端")
    print("=" * 50)
    print(f"目标服务器: {SERVER_IP}:{SERVER_PORT}")
    print(f"监控进程: {PROCESS_NAME}")
    print(f"心跳间隔: {INTERVAL}秒")
    print("=" * 50)
    print("提示: 程序将在后台静默运行")
    print("按 Ctrl+C 可停止客户端\n")
    
    try:
        while True:
            if is_process_running(PROCESS_NAME):
                send_heartbeat(SERVER_IP)
            else:
                # 进程未运行,不发送心跳
                pass
            
            time.sleep(INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n客户端已停止")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    finally:
        # 清理互斥锁
        if mutex:
            win32api.CloseHandle(mutex)