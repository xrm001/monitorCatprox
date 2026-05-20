"""
Catprox 网络监控核心模块
监控Catprox进程的网络连接,统计活跃会话数
"""

import psutil
import time
from typing import Dict, List, Set
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConnectionInfo:
    """连接信息"""
    local_port: int
    remote_addr: str
    remote_port: int
    state: str
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class CatproxMonitor:
    """Catprox网络监控器"""
    
    def __init__(self, process_name: str = "Catprox.exe", threshold: int = 6):
        """
        初始化监控器
        
        Args:
            process_name: 进程名称
            threshold: 告警阈值(默认6,留2台余量)
        """
        self.process_name = process_name
        self.threshold = threshold
        self.connections: Dict[str, ConnectionInfo] = {}
        self.alert_cooldown = 300  # 告警冷却时间(秒)
        self.last_alert_time = 0
        
    def get_catprox_pids(self) -> List[int]:
        """获取Catprox进程的PID列表"""
        pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == self.process_name.lower():
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return pids
    
    def get_active_connections(self) -> Set[str]:
        """
        获取Catprox的活跃网络连接
        
        Returns:
            活跃连接的标识集合(格式: "local_port-remote_addr:remote_port")
        """
        pids = self.get_catprox_pids()
        if not pids:
            return set()
        
        active_conns = set()
        
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                connections = proc.net_connections(kind='tcp')
                
                for conn in connections:
                    if conn.status == 'ESTABLISHED' and conn.raddr:
                        # 过滤掉本地回环连接,只统计真实VPN连接
                        # 根据之前的测试,Catprox会连接127.0.0.1:39798
                        if conn.raddr.ip != '127.0.0.1' or conn.raddr.port == 39798:
                            conn_id = f"{conn.laddr.port}-{conn.raddr.ip}:{conn.raddr.port}"
                            active_conns.add(conn_id)
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return active_conns
    
    def update_connections(self):
        """更新连接状态"""
        current_conns = self.get_active_connections()
        now = time.time()
        
        # 更新已存在的连接
        for conn_id in current_conns:
            if conn_id in self.connections:
                self.connections[conn_id].last_seen = now
            else:
                # 新连接
                parts = conn_id.split('-')
                local_port = int(parts[0])
                remote_parts = parts[1].split(':')
                remote_addr = remote_parts[0]
                remote_port = int(remote_parts[1])
                
                self.connections[conn_id] = ConnectionInfo(
                    local_port=local_port,
                    remote_addr=remote_addr,
                    remote_port=remote_port,
                    state='ESTABLISHED'
                )
        
        # 标记超时连接(60秒未活动)
        timeout = 60
        expired = []
        for conn_id, conn_info in self.connections.items():
            if conn_id not in current_conns and (now - conn_info.last_seen > timeout):
                expired.append(conn_id)
        
        for conn_id in expired:
            del self.connections[conn_id]
    
    def get_active_count(self) -> int:
        """获取当前活跃连接数"""
        self.update_connections()
        return len(self.connections)
    
    def get_connection_details(self) -> List[Dict]:
        """获取连接详细信息"""
        self.update_connections()
        details = []
        
        for conn_id, conn_info in self.connections.items():
            details.append({
                'id': conn_id,
                'local_port': conn_info.local_port,
                'remote_addr': conn_info.remote_addr,
                'remote_port': conn_info.remote_port,
                'first_seen': datetime.fromtimestamp(conn_info.first_seen).strftime('%H:%M:%S'),
                'duration': int(time.time() - conn_info.first_seen)
            })
        
        return details
    
    def should_alert(self) -> bool:
        """判断是否应该触发告警"""
        count = self.get_active_count()
        now = time.time()
        
        if count > self.threshold and (now - self.last_alert_time > self.alert_cooldown):
            self.last_alert_time = now
            return True
        
        return False
    
    def get_status(self) -> Dict:
        """获取完整状态信息"""
        count = self.get_active_count()
        details = self.get_connection_details()
        
        return {
            'active_count': count,
            'threshold': self.threshold,
            'max_allowed': 8,
            'status': 'warning' if count > self.threshold else 'normal',
            'process_running': len(self.get_catprox_pids()) > 0,
            'connections': details,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
