

import psutil
import time
import logging
import csv
from datetime import datetime
import os

class CPUMonitor:
    def __init__(self, log_dir="/var/log/cpu_monitor"):
        # 디렉토리 생성
        os.makedirs(log_dir, exist_ok=True)
        
        # 날짜 문자열
        self.date_str = datetime.now().strftime('%Y%m%d')
        
        # 로그 파일 설정
        log_file = os.path.join(log_dir, f"cpu_usage_{self.date_str}.log")
        
        # CSV 파일 설정
        self.csv_file = os.path.join(log_dir, f"cpu_usage_{self.date_str}.csv")
        
        # 로깅 설정
        self.logger = logging.getLogger('CPUMonitor')
        self.logger.setLevel(logging.INFO)
        
        # 파일 핸들러 설정
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # 포맷터 설정
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 핸들러 추가
        self.logger.addHandler(file_handler)
        
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
                               'Load_Avg_5min', 'Load_Avg_15min', 
                               'Frequency_Current(MHz)', 'Temperature(°C)'])

    def get_cpu_info(self):
        """CPU 정보 수집"""
        # CPU 사용률 (1초 간격으로 측정)
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 시스템 로드 평균
        load_avg = psutil.getloadavg()
        
        # CPU 주파수 (현재/최소/최대)
        freq = psutil.cpu_freq()
        
        # CPU 온도 (지원되는 경우)
        try:
            temp = psutil.sensors_temperatures()
            if 'coretemp' in temp:
                temperature = temp['coretemp'][0].current
            else:
                temperature = None
        except (AttributeError, KeyError):
            temperature = None

        return {
            'cpu_percent': cpu_percent,
            'load_avg': load_avg,
            'frequency': freq.current if freq else None,
            'temperature': temperature
        }

    def get_top_processes(self, limit=5):
        """CPU 사용량 상위 프로세스 조회"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                proc_info = proc.info
                proc_info['cpu_percent'] = proc.cpu_percent()
                if proc_info['cpu_percent'] > 0.1:  # 0.1% 이상 사용하는 프로세스만
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
                cpu_info['load_avg'][2],
                cpu_info['frequency'],
                cpu_info['temperature']
            ])

    def monitor(self, interval=60):
        """주기적으로 CPU 모니터링 실행"""
        self.logger.info("Starting CPU monitoring...")
        self.logger.info(f"System has {self.cpu_count} physical cores and {self.cpu_count_logical} logical cores")
        self.date_str = datetime.now().strftime('%Y%m%d')
        try:
            while True:
                # CPU 정보 수집
                cpu_info = self.get_cpu_info()
                
                # CSV 파일에 CPU 정보 저장
                self.log_to_csv(cpu_info)
                
                # 로그 파일에 CPU 상태 정보 저장
                self.logger.info("System CPU Status:")
                self.logger.info(
                    f"CPU Usage: {cpu_info['cpu_percent']}%, "
                    f"Load Average: {cpu_info['load_avg']}, "
                    f"Current Frequency: {cpu_info['frequency']:.0f}MHz"
                )
                if cpu_info['temperature']:
                    self.logger.info(f"CPU Temperature: {cpu_info['temperature']}°C")
                
                # 상위 프로세스 로깅
                top_processes = self.get_top_processes()
                self.logger.info("Top 5 CPU-Consuming Processes:")
                for proc in top_processes:
                    self.logger.info(
                        f"Process: {proc['name']}, PID: {proc['pid']}, "
                        f"CPU Usage: {proc['cpu_percent']:.1f}%"
                    )
                
                # 경고 조건 확인
                if cpu_info['cpu_percent'] > 90:
                    self.logger.warning(f"High CPU usage alert! {cpu_info['cpu_percent']}% used")
                if cpu_info['temperature'] and cpu_info['temperature'] > 80:
                    self.logger.warning(f"High CPU temperature alert! {cpu_info['temperature']}°C")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("Stopping CPU monitoring...")
        except Exception as e:
            self.logger.error(f"Error occurred: {str(e)}")

def main():
    monitor = CPUMonitor()
    monitor.monitor()

if __name__ == "__main__":
    main()