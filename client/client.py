import os
import sys
import json
import time
import logging
import requests
import schedule
import threading
from datetime import datetime
from camera_capture import RaspberryPiCamera
from sensor_reader import DHT22Sensor
from buzzer_control import Buzzer
from alarm_checker import AlarmChecker

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/sleep_aiz_client.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class SleepAiZClient:
    """Sleep-AiZ 메인 클라이언트"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Args:
            config_path: 설정 파일 경로
        """
        # 설정 로드
        self.config = self.load_config(config_path)
        
        # 서버 URL
        self.server_url = self.config['server']['base_url']
        self.timeout = self.config['system']['timeout_seconds']
        self.max_retries = self.config['system']['max_retries']
        
        # 카메라 초기화
        self.camera = RaspberryPiCamera(
            resolution=tuple(self.config['camera']['resolution']),
            image_format=self.config['camera']['image_format'],
            image_quality=self.config['camera']['image_quality']
        )
        
        # 센서 초기화
        self.sensor = DHT22Sensor(
            pin_number=self.config['sensor']['dht22_pin'],
            retry_count=self.config['sensor']['retry_count'],
            retry_delay=self.config['sensor']['retry_delay_seconds']
        )
        
        # 부저 초기화 (GPIO 18번 기본)
        self.buzzer = Buzzer(pin=18)
        
        # 알람 체커 초기화
        self.alarm_checker = AlarmChecker(self.server_url, self.timeout)
        
        # 알람 스레드 플래그
        self.alarm_running = False
        self.alarm_thread = None
        
        # 임시 이미지 디렉토리
        self.temp_image_dir = self.config['paths']['temp_image_dir']
        os.makedirs(self.temp_image_dir, exist_ok=True)
        
        logger.info("Sleep-AiZ 클라이언트 초기화 완료")
        logger.info(f"서버 주소: {self.server_url}")
    
    def load_config(self, config_path: str) -> dict:
        """설정 파일 로드"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"설정 파일 로드 완료: {config_path}")
            return config
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            raise
    
    def check_server_health(self) -> bool:
        """서버 연결 확인"""
        try:
            url = f"{self.server_url}/health"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                logger.info("✅ 서버 연결 정상")
                return True
            else:
                logger.warning(f"서버 응답 이상: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 서버 연결 실패: {e}")
            return False
    
    def read_and_upload_sensor(self) -> bool:
        """센서 읽기 및 서버 업로드"""
        try:
            logger.info("센서 데이터 읽기 시작")
            
            # 센서 읽기
            sensor_data = self.sensor.read()
            
            if not sensor_data:
                logger.error("센서 읽기 실패")
                return False
            
            temperature, humidity = sensor_data
            logger.info(f"센서 데이터: {temperature}°C, {humidity}%")
            
            # 서버로 업로드 (재시도 포함)
            for attempt in range(self.max_retries):
                try:
                    url = f"{self.server_url}/api/environment"
                    
                    data = {
                        'temperature': temperature,
                        'humidity': humidity
                    }
                    
                    logger.info(f"서버 업로드 시도 [{attempt + 1}/{self.max_retries}]...")
                    response = requests.post(
                        url,
                        json=data,
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"✅ 센서 데이터 업로드 성공: ID={result['id']}")
                        return True
                    else:
                        logger.warning(f"서버 응답 오류: {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"업로드 실패 [{attempt + 1}/{self.max_retries}]: {e}")
                    
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"{wait_time}초 후 재시도...")
                        time.sleep(wait_time)
            
            logger.error("❌ 센서 데이터 업로드 최종 실패")
            return False
            
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            return False
    
    def capture_and_upload(self) -> bool:
        """카메라 촬영 및 서버 업로드"""
        try:
            logger.info("=" * 50)
            logger.info("카메라 촬영 및 업로드 시작")
            
            # 1. 사진 촬영
            image_path = self.camera.capture_with_timestamp(self.temp_image_dir)
            
            if not image_path:
                logger.error("사진 촬영 실패")
                return False
            
            logger.info(f"사진 촬영 완료: {image_path}")
            
            # 2. 서버로 업로드 (재시도 포함)
            for attempt in range(self.max_retries):
                try:
                    url = f"{self.server_url}/api/posture"
                    
                    # 파일 열기
                    with open(image_path, 'rb') as image_file:
                        files = {
                            'image': (os.path.basename(image_path), image_file, 'image/jpeg')
                        }
                        
                        # AI 분석은 서버에서 자동으로
                        params = {
                            'analyzed_at': datetime.now().isoformat()
                        }
                        
                        logger.info(f"서버 업로드 시도 [{attempt + 1}/{self.max_retries}]...")
                        response = requests.post(
                            url,
                            files=files,
                            params=params,
                            timeout=self.timeout
                        )
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"✅ 업로드 성공: ID={result['id']}, 자세={result['posture_type']}")
                        
                        # 임시 파일 삭제
                        os.remove(image_path)
                        logger.info("임시 파일 삭제 완료")
                        
                        return True
                    else:
                        logger.warning(f"서버 응답 오류: {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"업로드 실패 [{attempt + 1}/{self.max_retries}]: {e}")
                    
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # 지수 백오프 (2, 4, 8초...)
                        logger.info(f"{wait_time}초 후 재시도...")
                        time.sleep(wait_time)
            
            logger.error("❌ 업로드 최종 실패")
            return False
            
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            return False
        """카메라 촬영 및 서버 업로드"""
        try:
            logger.info("=" * 50)
            logger.info("카메라 촬영 및 업로드 시작")
            
            # 1. 사진 촬영
            image_path = self.camera.capture_with_timestamp(self.temp_image_dir)
            
            if not image_path:
                logger.error("사진 촬영 실패")
                return False
            
            logger.info(f"사진 촬영 완료: {image_path}")
            
            # 2. 서버로 업로드 (재시도 포함)
            for attempt in range(self.max_retries):
                try:
                    url = f"{self.server_url}/api/posture"
                    
                    # 파일 열기
                    with open(image_path, 'rb') as image_file:
                        files = {
                            'image': (os.path.basename(image_path), image_file, 'image/jpeg')
                        }
                        
                        # AI 분석 결과는 나중에 추가 예정
                        params = {
                            'posture_type': '분석 대기중',  # AI 모델 연동 전 임시값
                            'analyzed_at': datetime.now().isoformat()
                        }
                        
                        logger.info(f"서버 업로드 시도 [{attempt + 1}/{self.max_retries}]...")
                        response = requests.post(
                            url,
                            files=files,
                            params=params,
                            timeout=self.timeout
                        )
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"✅ 업로드 성공: ID={result['id']}")
                        
                        # 임시 파일 삭제
                        os.remove(image_path)
                        logger.info("임시 파일 삭제 완료")
                        
                        return True
                    else:
                        logger.warning(f"서버 응답 오류: {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"업로드 실패 [{attempt + 1}/{self.max_retries}]: {e}")
                    
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # 지수 백오프 (2, 4, 8초...)
                        logger.info(f"{wait_time}초 후 재시도...")
                        time.sleep(wait_time)
            
            logger.error("❌ 업로드 최종 실패")
            return False
            
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            return False
    
    def job(self):
        """스케줄러가 실행할 작업"""
        logger.info("\n" + "=" * 50)
        logger.info(f"정기 작업 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)
        
        # 서버 연결 확인
        if not self.check_server_health():
            logger.warning("서버 연결 불가. 작업 건너뜀.")
            return
        
        # 센서 데이터 읽기 및 업로드
        sensor_success = self.read_and_upload_sensor()
        
        # 카메라 촬영 및 업로드
        camera_success = self.capture_and_upload()
        
        if sensor_success and camera_success:
            logger.info("✅ 모든 작업 완료")
        elif sensor_success or camera_success:
            logger.warning("⚠️  일부 작업 성공")
        else:
            logger.warning("⚠️  모든 작업 실패")
        
        logger.info("=" * 50 + "\n")
    
    def check_alarms(self):
        """알람 확인 및 처리"""
        try:
            # 울려야 할 알람 확인
            alarms_to_ring = self.alarm_checker.check_and_trigger_alarms()
            
            if alarms_to_ring and not self.alarm_running:
                # 알람 울리기 시작
                alarm = alarms_to_ring[0]  # 첫 번째 알람
                logger.info(f"🔔 알람 울림: {alarm.get('label', 'Alarm')} at {alarm.get('alarm_time')}")
                
                self.alarm_running = True
                self.alarm_thread = threading.Thread(
                    target=self._ring_alarm,
                    args=(alarm['id'],),
                    daemon=True
                )
                self.alarm_thread.start()
            
            # 서버에서 알람이 꺼졌는지 확인
            if self.alarm_running:
                ringing_alarms = self.alarm_checker.check_ringing_alarms()
                if not ringing_alarms:
                    # 알람이 꺼짐
                    logger.info("알람이 웹에서 꺼졌습니다")
                    self.alarm_running = False
                    self.buzzer.off()
        
        except Exception as e:
            logger.error(f"알람 확인 중 오류: {e}")
    
    def _ring_alarm(self, alarm_id: int):
        """알람 울리기 (별도 스레드)"""
        logger.info(f"알람 {alarm_id} 부저 시작")
        
        # 최대 10분 동안 울림
        max_duration = 600  # 10분
        start_time = time.time()
        
        while self.alarm_running and (time.time() - start_time < max_duration):
            self.buzzer.on()
            time.sleep(0.5)
            self.buzzer.off()
            time.sleep(0.5)
        
        self.buzzer.off()
        self.alarm_running = False
        logger.info(f"알람 {alarm_id} 부저 종료")
    
    def start(self):
        """클라이언트 시작"""
        try:
            logger.info("\n" + "=" * 50)
            logger.info("Sleep-AiZ 클라이언트 시작")
            logger.info("=" * 50)
            
            # 카메라 시작
            self.camera.start()
            
            # 서버 연결 확인
            if not self.check_server_health():
                logger.error("서버에 연결할 수 없습니다. 서버를 먼저 실행해주세요.")
                return
            
            # 즉시 한 번 실행
            logger.info("초기 작업 실행...")
            self.job()
            
            # 스케줄 설정
            interval = self.config['camera']['capture_interval_minutes']
            schedule.every(interval).minutes.do(self.job)
            
            # 알람 체크는 1분마다
            schedule.every(1).minutes.do(self.check_alarms)
            
            logger.info(f"\n스케줄러 시작:")
            logger.info(f"  - 데이터 수집: {interval}분마다")
            logger.info(f"  - 알람 체크: 1분마다")
            logger.info("종료하려면 Ctrl+C를 누르세요.\n")
            
            # 스케줄 실행
            while True:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n사용자에 의해 종료됨")
        except Exception as e:
            logger.error(f"치명적 오류: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """리소스 정리"""
        logger.info("리소스 정리 중...")
        try:
            self.alarm_running = False
            self.buzzer.off()
            self.buzzer.cleanup()
            self.camera.stop()
            self.camera.close()
            self.sensor.close()
            logger.info("✅ 정리 완료")
        except Exception as e:
            logger.warning(f"정리 중 오류: {e}")


def main():
    """메인 함수"""
    # 설정 파일 경로
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    
    # 클라이언트 생성 및 시작
    client = SleepAiZClient(config_path)
    client.start()


if __name__ == "__main__":
    main()