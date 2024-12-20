

import psutil
import time
import logging
import csv
import json
from datetime import datetime
import os

class CPUMonitor:
    def __init__(self):
        # 디렉토리 생성
        self.log_dir="/var/log/cpu_monitor"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 날짜 문자열
        self.date_str = datetime.now().strftime('%Y%m%d')
        
        # 로그 파일 설정
        log_file = os.path.join(self.log_dir, f"cpu_usage_{self.date_str}.log")
        
        # CSV 파일 설정
        self.csv_file = os.path.join(self.log_dir, f"cpu_usage_{self.date_str}.csv")
        
        # 로깅 설정
        self.logger = logging.getLogger('CPUMonitor')
        self.logger.setLevel(logging.INFO)
        
        # 파일 핸들러 설정
        self.file_handler = logging.FileHandler(log_file)
        self.file_handler.setLevel(logging.INFO)
        
        # 포맷터 설정
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        self.file_handler.setFormatter(formatter)
        
        # 핸들러 추가
        self.logger.addHandler(self.file_handler)
        
        # 콘솔 출력 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # CPU 코어 수 확인
        self.cpu_count = psutil.cpu_count()
        self.cpu_count_logical = psutil.cpu_count(logical=True)

        # CSV 파일 헤더 작성
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'CPU_Usage(%)', 'Load_Avg_1min', 
                               'Load_Avg_5min', 'Load_Avg_15min', ])

    def get_cpu_info(self):
        """CPU 정보 수집"""
        # CPU 사용률 (1초 간격으로 측정)
        cpu_percent = psutil.cpu_percent()
        
        # 시스템 로드 평균
        load_avg = psutil.getloadavg()

        return {
            'cpu_percent': cpu_percent,
            'load_avg': load_avg,
            
        }

    def get_top_processes(self, limit=5):
        
        
        
        # 실제 측정
        processes = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_info = proc.info
                proc_info['cpu_percent'] = proc.cpu_percent()
                
                
                if proc_info['cpu_percent'] > 0.1:
                    processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:limit]

    def log_to_csv(self, cpu_info):
        """CSV 파일에 CPU 정보 저장"""
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                cpu_info['cpu_percent'],
                cpu_info['load_avg'][0],
                cpu_info['load_avg'][1],
                cpu_info['load_avg'][2]
                
            ])
    
            
            
    def monitor(self, sample_interval=3, report_interval=6):
        """
        sample_interval: 샘플링 간격 (초)
        report_interval: 보고 간격 (초)
        """
        self.logger.info("Starting CPU monitoring...")
        self.logger.info(f"System has {self.cpu_count} physical cores and {self.cpu_count_logical} logical cores")
        
        try:
            count = 0
            cpu_usage_sum = 0
            process_usage = {}  # 프로세스별 CPU 사용량 누적
            
            while True:
                # CPU 정보 수집
                cpu_info = self.get_cpu_info()
                
                cpu_usage_sum += cpu_info['cpu_percent']
                
                # 프로세스 정보 수집 및 누적
                top_processes = self.get_top_processes()
                for proc in top_processes:
                    pid = proc['pid']
                    if pid not in process_usage:
                        process_usage[pid] = {'total': 0, 'count': 0, 'name': proc['name']}
                    process_usage[pid]['total'] += proc['cpu_percent']
                    process_usage[pid]['count'] += 1
                
                count += 1
                
                # 60초가 되면 평균 계산 및 로깅
                if count >= report_interval:
                    
                    
                    # 60초에 한번씩 날짜가 변했는지 확인 후 저장
                    current_date_str = datetime.now().strftime('%Y%m%d')
                    if self.date_str != current_date_str:
                        self.date_str = current_date_str
                        
                        # 로그 파일 설정
                        log_file = os.path.join(self.log_dir, f"cpu_usage_{self.date_str}.log")
                        

                        # 파일 핸들러 설정
                        file_handler = logging.FileHandler(log_file)
                        file_handler.setLevel(logging.INFO)
                        # 포맷터 설정
                        formatter = logging.Formatter('%(asctime)s - %(message)s')
                        file_handler.setFormatter(formatter)
                        
                        # 핸들러 추가
                        self.file_handler.close()
                        self.file_handler = file_handler
                        self.logger.addHandler(self.file_handler)
                        
                    avg_cpu_usage = cpu_usage_sum / count
                    

                    self.logger.info(f"\n{'='*50}")
                    self.logger.info(f"Last {report_interval} seconds summary:")
                    self.logger.info(f"Average CPU Usage: {avg_cpu_usage:.1f}%")
                    self.logger.info(f"Load Average: {cpu_info['load_avg']}")
                    
                    
                    
                    # 프로세스별 평균 사용량 계산 및 로깅
                    self.logger.info("\nTop CPU-Consuming Processes (Average):")
                    process_averages = { pid: (usage['name'], usage['total'] / usage['count']) for pid, usage in process_usage.items()}
                    
                    # 상위 5개 프로세스 출력
                    top_5_processes = sorted( process_averages.items(), key=lambda x: x[1][1],  reverse=True)[:5]
                    
                    for pid, avg_usage in top_5_processes:
                        self.logger.info(f"Process: {pid}, Name: {avg_usage[0]} Average CPU Usage: {avg_usage[1]:.1f}%")
                    
                    self.logger.info(f"{'='*50}\n")
                    
                    
                    # 카운터와 누적값 초기화
                    count = 0
                    cpu_usage_sum = 0
                    process_usage.clear()
                
                time.sleep(sample_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Stopping CPU monitoring...")
        except Exception as e:
            self.logger.error(f"Error occurred: {str(e)}")
    
    
        
        
def main():
    monitor = CPUMonitor()
    monitor.monitor()

if __name__ == "__main__":
    main()