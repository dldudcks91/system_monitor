#%%

import asyncio
import logging
import psutil
import json
from datetime import datetime
import websockets
from logging.handlers import TimedRotatingFileHandler

class SystemMonitor:
    def __init__(self, websocket_port=8765):
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
        processes = []
         
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                proc_info = {
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cpu_percent': proc.cpu_percent()
                }
                if proc_info['cpu_percent'] > 0:
                    processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # CPU 사용률 기준으로 정렬하고 상위 5개 선택
        top_processes = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]
        metrics['processes'] = top_processes
        return metrics
    def test_monitor(self):
        
        while True:
            metrics = self.get_metrics()
            print(metrics)
        
        
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