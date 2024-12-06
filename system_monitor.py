#%%
import os
import psutil
import json
import time
from datetime import datetime


import redis


class AsyncSystemMonitor:
    def __init__(self):
        
        self.log_dir="/var/log/system_monitor"
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
   
        
    def get_metrics(self):
        
        metrics = {
             'timestamp': datetime.now().isoformat(),
             'cpu': psutil.cpu_percent(),
             'memory': psutil.virtual_memory().percent,
             'swap_memory':psutil.swap_memory().percent
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
                if (proc_info['cpu_percent'] > 1.0) or (proc_info['memory_percent'] > 1.0):
                    processes.append(proc_info)
                    
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # CPU, memory 사용률 기준으로 정렬하고 상위 limit개 선택 후 합침
        
        processes_cpu = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:limit]
        processes_memory = sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:limit]
        
        processes_dict = {p['pid']: p for p in processes_cpu + processes_memory}
        processes_total = list(processes_dict.values())

        return processes_total
    
    
    def store_metrics(self, metrics):
        
        self.redis_client.set('current_system_monitor', json.dumps(metrics))
        # 히스토리 저장 (리스트 사용)
        self.redis_client.lpush('system_monitor_history', json.dumps(metrics))
        # 최대 1000개만 유지
        self.redis_client.ltrim('system_monitor_history', 0, 999)
        
        
    
    def monitor(self):
        last_save = 0
        metrics_buffer = []
        while True:
            try:
                metrics = self.get_metrics()
                self.store_metrics(metrics)
                current_time = datetime.now().timestamp()
                
                if current_time - last_save >= 60:
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    json_file = os.path.join(self.log_dir, f"system_monitor_{date_str.replace('-','')}.json") 
                    
                    
                    with open(json_file, 'a') as f:
                        for metric in metrics_buffer:
                            f.write(json.dumps(metric) + '\n')
                    
                    
                    metrics_buffer = []
                    last_save = current_time
                    #print(f'Save metrics: {current_time}')
                    
                    
                #print(metrics)
                metrics_buffer.append(metrics)
                time.sleep(3)
            except Exception as e:
                print(f"Error in test_monitor: {e}")
                time.sleep(3)
        
   
if __name__ == "__main__":
    monitor = AsyncSystemMonitor()
    monitor.monitor()