#%%
import os
import asyncio
import logging
import psutil
import json
import time
from datetime import datetime

from logging.handlers import TimedRotatingFileHandler
#import websockets


class SystemMonitor:
    def __init__(self, websocket_port=8765):
        
        self.log_dir="/var/log/system_monitor"
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.port = websocket_port
        self.clients = set()
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        logger = logging.getLogger('system_monitor')
        logger.setLevel(logging.INFO)
        
        handler = TimedRotatingFileHandler(
            'system_metrics.log',
            when='midnight',
            interval=1,
            backupCount=7  # 일주일치만 보관
        )
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        logger.addHandler(handler)
        return logger
        
    def get_metrics(self):
        
        metrics = {
             'timestamp': datetime.now().isoformat(),
             'cpu': psutil.cpu_percent(),
             'memory': psutil.virtual_memory().percent
             }
        
        metrics['processes'] = self.get_process()
        return metrics
    
    def get_process(self, limit = 5):
        
        processes = []
         
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_info = proc.info
                proc_info['cpu_percent'] = proc.cpu_percent()
                proc_info['memory_percent'] = round(proc.memory_percent(),3)
                if (proc_info['cpu_percent'] > 0.1) or (proc_info['memory_percent'] > 1.0):
                    processes.append(proc_info)
                    
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # CPU 사용률 기준으로 정렬하고 상위 5개 선택
        processes = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:limit]
        
        
        return processes
    
    
    def test_monitor(self):
        last_save = 0
        while True:
            try:
                metrics = self.get_metrics()
                current_time = datetime.now().timestamp()
                if current_time - last_save >= 60:
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    json_file = os.path.join(self.log_dir, f"cpu_usage_{date_str}.json") 
                    
                    
                    with open(json_file, 'a') as f:
                        f.write(json.dumps(metrics) + '\n')
                    
                    last_save = current_time
                time.sleep(3)
            except Exception as e:
                print(f"Error in test_monitor: {e}")
                time.sleep(3)
        
    async def monitor_metrics(self):
        last_save = 0
        while True:
            try:
                metrics = self.get_metrics()
                current_time = datetime.now().timestamp()
                
                # 웹소켓 브로드캐스트 (3초마다)
                if self.clients:  # 클라이언트가 있을 때만 전송
                    message = json.dumps(metrics)
                    await asyncio.gather(
                        *[client.send(message) for client in self.clients]
                    )
                
                # 파일 저장 (60초마다)
                if current_time - last_save >= 60:
                    self.logger.info(json.dumps(metrics))
                    last_save = current_time
                    
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"Error in monitor_metrics: {e}")
                await asyncio.sleep(3)
                
    async def handle_client(self, websocket):
        self.clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
            
    async def start(self):
        async with websockets.serve(self.handle_client, "localhost", self.port):
            await self.monitor_metrics()

if __name__ == "__main__":
    monitor = SystemMonitor()
    #asyncio.run(monitor.start())
    monitor.test_monitor()