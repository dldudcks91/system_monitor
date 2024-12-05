import psutil
import time
import logging
from datetime import datetime
import os

class MemoryMonitor:
    def __init__(self):
        # 로그 디렉토리 생성
        self.log_dir ="/var/log/memory_monitor"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 로그 파일 설정
        log_file = os.path.join(self.log_dir, f"memory_usage_{datetime.now().strftime('%Y%m%d')}.log")
        
        
        # 로깅 설정
        self.logger = logging.getLogger('MemoryMonitor')
        self.logger.setLevel(logging.INFO)
        
        # 파일 핸들러 설정
        self.file_handler = logging.FileHandler(log_file)
        self.file_handler.setLevel(logging.INFO)
        
        # 포맷터 설정
        self.formatter = logging.Formatter('%(asctime)s - Memory Usage: %(message)s')
        self.file_handler.setFormatter(self.formatter)
        
        # 핸들러 추가
        self.logger.addHandler(self.file_handler)
        
        # 콘솔 출력 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)

    def get_memory_info(self):
        """시스템 메모리 정보 수집"""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'total': self.bytes_to_gb(memory.total),
            'available': self.bytes_to_gb(memory.available),
            'used': self.bytes_to_gb(memory.used),
            'free': self.bytes_to_gb(memory.free),
            'percent': memory.percent,
            'swap_total': self.bytes_to_gb(swap.total),
            'swap_used': self.bytes_to_gb(swap.used),
            'swap_free': self.bytes_to_gb(swap.free),
            'swap_percent': swap.percent
        }

    @staticmethod
    def bytes_to_gb(bytes_value):
        """바이트를 GB로 변환"""
        return round(bytes_value / (1024 ** 3), 2)

    def log_memory_usage(self):
        """메모리 사용량 로깅"""
        mem_info = self.get_memory_info()
        
        log_message = (
            f"Total: {mem_info['total']}GB, "
            f"Used: {mem_info['used']}GB ({mem_info['percent']}%), "
            f"Available: {mem_info['available']}GB, "
            f"Free: {mem_info['free']}GB, "
            f"Swap Used: {mem_info['swap_used']}GB/{mem_info['swap_total']}GB ({mem_info['swap_percent']}%)"
        )
        
        self.logger.info(log_message)
        
        # 경고 조건 확인
        if mem_info['percent'] > 90:
            self.logger.warning(f"High memory usage alert! {mem_info['percent']}% used")
        if mem_info['swap_percent'] > 50:
            self.logger.warning(f"High swap usage alert! {mem_info['swap_percent']}% used")

    def monitor(self, interval=60):
        """주기적으로 메모리 모니터링 실행"""
        self.logger.info("Starting memory monitoring...")
        
        try:
            while True:
                self.log_memory_usage()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.logger.info("Stopping memory monitoring...")
        except Exception as e:
            self.logger.error(f"Error occurred: {str(e)}")

def main():
    # 프로세스 정보도 포함하여 모니터링
    def get_process_memory():
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                proc_info = proc.info
                if proc_info['memory_percent'] > 1.0:  # 1% 이상 사용하는 프로세스만
                    processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return sorted(processes, key=lambda x: x['memory_percent'], reverse=True)

    monitor = MemoryMonitor()
    
    # 프로세스 정보를 포함한 확장된 로깅
    def extended_logging():
        monitor.log_memory_usage()
        top_processes = get_process_memory()[:5]  # 상위 5개 프로세스
        for proc in top_processes:
            monitor.logger.info(
                f"Process: {proc['name']}, "
                f"PID: {proc['pid']}, "
                f"Memory Usage: {proc['memory_percent']:.1f}%"
            )

    try:
        monitor.logger.info("Starting extended memory monitoring...")
        while True:
            log_file = os.path.join(monitor.log_dir, f"memory_usage_{datetime.now().strftime('%Y%m%d')}.log")
            monitor.file_handler = logging.FileHandler(log_file)
            monitor.file_handler.setLevel(logging.INFO)
            extended_logging()
            
            time.sleep(60)  # 60초 간격으로 모니터링
    except KeyboardInterrupt:
        monitor.logger.info("Monitoring stopped by user")
    except Exception as e:
        monitor.logger.error(f"Error in monitoring: {str(e)}")

if __name__ == "__main__":
    main()