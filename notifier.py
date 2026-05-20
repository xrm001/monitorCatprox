"""
Windows 弹窗告警模块
用于服务端检测到设备超限时发送通知
"""


class WindowsNotifier:
    """Windows通知器"""
    
    def __init__(self):
        self.notification = None
        try:
            from plyer import notification
            self.notification = notification
        except ImportError:
            print("⚠️ 未安装plyer库,将使用控制台告警")
            print("   安装命令: pip install plyer")
    
    def send_alert(self, title: str, message: str, timeout: int = 10):
        """
        发送通知
        
        Args:
            title: 通知标题
            message: 通知内容
            timeout: 显示时长(秒)
        """
        if self.notification:
            try:
                self.notification.notify(
                    title=title,
                    message=message,
                    app_name='Catprox Monitor',
                    timeout=timeout
                )
                print(f"📢 弹窗通知已发送: {title}")
            except Exception as e:
                print(f"通知发送失败: {e}")
                self._fallback_alert(title, message)
        else:
            self._fallback_alert(title, message)
    
    def _fallback_alert(self, title: str, message: str):
        """备用告警方式(控制台输出)"""
        print("\n" + "=" * 60)
        print(f"🔔 {title}")
        print(f"📝 {message}")
        print("=" * 60 + "\n")


# 全局通知器实例
notifier = WindowsNotifier()


def alert_device_limit_exceeded(count: int, max_allowed: int, threshold: int):
    """
    设备超限告警
    
    Args:
        count: 当前设备数
        max_allowed: 最大允许数
        threshold: 告警阈值
    """
    title = "⚠️ Catprox 设备超限告警!"
    message = (
        f"当前活跃设备: {count}/{max_allowed}\n"
        f"已超过告警阈值({threshold})\n"
        f"可能影响正常使用,请检查!"
    )
    
    notifier.send_alert(title, message, timeout=15)


def alert_device_warning(count: int, max_allowed: int):
    """
    设备接近上限警告
    
    Args:
        count: 当前设备数
        max_allowed: 最大允许数
    """
    title = "⚠️ Catprox 设备接近上限"
    message = (
        f"当前活跃设备: {count}/{max_allowed}\n"
        f"建议检查使用情况"
    )
    
    notifier.send_alert(title, message, timeout=10)


def alert_service_started():
    """服务启动通知"""
    notifier.send_alert(
        title="✅ Catprox 监控服务已启动",
        message="正在监控设备使用情况",
        timeout=5
    )


def alert_service_stopped():
    """服务停止通知"""
    notifier.send_alert(
        title="🔴 Catprox 监控服务已停止",
        message="监控已关闭",
        timeout=5
    )
