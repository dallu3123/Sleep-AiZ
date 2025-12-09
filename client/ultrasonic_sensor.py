import RPi.GPIO as GPIO
import time
import logging

logger = logging.getLogger(__name__)


class UltrasonicSensor:
    """HC-SR04 초음파 센서"""
    
    def __init__(self, trig_pin: int = 23, echo_pin: int = 24):
        """
        Args:
            trig_pin: TRIG 핀 번호 (BCM)
            echo_pin: ECHO 핀 번호 (BCM)
        """
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        
        # GPIO 설정
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        
        # 초기화
        GPIO.output(self.trig_pin, False)
        time.sleep(0.1)
        
        logger.info(f"초음파 센서 초기화 완료 (TRIG: GPIO{trig_pin}, ECHO: GPIO{echo_pin})")
    
    def measure_distance(self) -> float:
        """
        거리 측정
        
        Returns:
            거리 (cm), 측정 실패 시 -1
        """
        try:
            # TRIG 핀에 10us 펄스 전송
            GPIO.output(self.trig_pin, True)
            time.sleep(0.00001)  # 10 microseconds
            GPIO.output(self.trig_pin, False)
            
            # ECHO 핀이 HIGH가 될 때까지 대기
            timeout = time.time() + 0.1  # 100ms 타임아웃
            while GPIO.input(self.echo_pin) == 0:
                pulse_start = time.time()
                if pulse_start > timeout:
                    logger.warning("ECHO 시작 타임아웃")
                    return -1
            
            # ECHO 핀이 LOW가 될 때까지 대기
            timeout = time.time() + 0.1
            while GPIO.input(self.echo_pin) == 1:
                pulse_end = time.time()
                if pulse_end > timeout:
                    logger.warning("ECHO 종료 타임아웃")
                    return -1
            
            # 거리 계산 (음속: 34300 cm/s)
            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 34300 / 2
            
            return round(distance, 1)
            
        except Exception as e:
            logger.error(f"거리 측정 오류: {e}")
            return -1
    
    def detect_hand(self, threshold: float = 30.0, duration: float = 5.0, check_interval: float = 0.2) -> bool:
        """
        손 감지 (일정 거리 이내에 지속적으로 물체 감지)
        
        Args:
            threshold: 감지 거리 임계값 (cm)
            duration: 지속 시간 (초)
            check_interval: 체크 간격 (초)
            
        Returns:
            True: 손이 지속적으로 감지됨
            False: 손이 감지되지 않음
        """
        logger.info(f"손 감지 시작 ({threshold}cm 이내, {duration}초 동안)")
        
        start_time = time.time()
        continuous_detection = 0
        required_checks = duration / check_interval
        
        while time.time() - start_time < duration + 1:  # 여유 시간
            distance = self.measure_distance()
            
            if distance > 0 and distance <= threshold:
                continuous_detection += 1
                logger.debug(f"감지: {distance}cm ({continuous_detection}/{int(required_checks)})")
                
                if continuous_detection >= required_checks:
                    logger.info(f"✅ 손 감지 완료! ({duration}초 지속)")
                    return True
            else:
                if continuous_detection > 0:
                    logger.debug(f"감지 중단: {distance}cm")
                continuous_detection = 0
            
            time.sleep(check_interval)
        
        logger.info("손 감지 실패 (시간 초과)")
        return False
    
    def monitor_for_alarm_stop(self, threshold: float = 30.0, duration: float = 5.0, 
                               callback=None, check_interval: float = 0.2):
        """
        알람 끄기 모니터링 (연속 모드)
        
        Args:
            threshold: 감지 거리 (cm)
            duration: 지속 시간 (초)
            callback: 손 감지 시 호출할 함수
            check_interval: 체크 간격 (초)
        """
        logger.info("알람 끄기 모니터링 시작")
        
        try:
            while True:
                if self.detect_hand(threshold, duration, check_interval):
                    logger.info("🖐️ 손 동작 감지! 알람 끄기 요청")
                    
                    if callback:
                        callback()
                    
                    # 잠시 대기 (중복 감지 방지)
                    time.sleep(2)
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            logger.info("모니터링 중단")
    
    def cleanup(self):
        """리소스 정리"""
        GPIO.cleanup()
        logger.info("초음파 센서 리소스 정리 완료")


def test_sensor():
    """센서 테스트"""
    print("HC-SR04 테스트 시작")
    print("센서 앞에 손을 5초 동안 가져다 대세요!")
    print("Ctrl+C로 종료\n")
    
    sensor = UltrasonicSensor(trig_pin=23, echo_pin=24)
    
    def on_hand_detected():
        print("✅ 알람 끄기!")
    
    try:
        # 거리 측정 테스트
        print("=== 거리 측정 테스트 (10회) ===")
        for i in range(10):
            distance = sensor.measure_distance()
            print(f"{i+1}. 거리: {distance}cm")
            time.sleep(0.5)
        
        print("\n=== 손 감지 테스트 ===")
        print("30cm 이내에 5초 동안 손을 대세요!")
        
        if sensor.detect_hand(threshold=30.0, duration=5.0):
            print("✅ 손 감지 성공!")
        else:
            print("❌ 손 감지 실패")
        
        print("\n=== 연속 모니터링 (Ctrl+C로 종료) ===")
        sensor.monitor_for_alarm_stop(
            threshold=30.0,
            duration=5.0,
            callback=on_hand_detected
        )
        
    except KeyboardInterrupt:
        print("\n테스트 종료")
    finally:
        sensor.cleanup()


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_sensor()