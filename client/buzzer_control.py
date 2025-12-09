import RPi.GPIO as GPIO
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Buzzer:
    """부저 제어 클래스"""
    
    def __init__(self, pin: int = 18):
        """
        Args:
            pin: 부저가 연결된 GPIO 핀 번호 (BCM)
        """
        self.pin = pin
        self.is_buzzing = False
        
        # GPIO 설정
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)
        
        logger.info(f"부저 초기화 완료 (GPIO {self.pin})")
    
    def on(self):
        """부저 켜기"""
        GPIO.output(self.pin, GPIO.HIGH)
        self.is_buzzing = True
        logger.info("부저 ON")
    
    def off(self):
        """부저 끄기"""
        GPIO.output(self.pin, GPIO.LOW)
        self.is_buzzing = False
        logger.info("부저 OFF")
    
    def beep(self, duration: float = 0.5):
        """짧게 삑 소리 내기"""
        self.on()
        time.sleep(duration)
        self.off()
    
    def beep_pattern(self, pattern: str = "short"):
        """
        패턴으로 부저 울리기
        
        Args:
            pattern: "short" (짧게), "long" (길게), "alarm" (알람)
        """
        if pattern == "short":
            self.beep(0.2)
        elif pattern == "long":
            self.beep(1.0)
        elif pattern == "alarm":
            # 알람: 3번 연속으로 삑삑삑
            for _ in range(3):
                self.beep(0.3)
                time.sleep(0.2)
    
    def alarm_sound(self, duration: int = 60):
        """
        알람 소리 (연속)
        
        Args:
            duration: 울리는 시간 (초)
        """
        logger.info(f"알람 시작 ({duration}초)")
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                # 0.5초 ON, 0.5초 OFF 반복
                self.on()
                time.sleep(0.5)
                self.off()
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("알람 중단")
        finally:
            self.off()
    
    def cleanup(self):
        """리소스 정리"""
        self.off()
        GPIO.cleanup()
        logger.info("부저 리소스 정리 완료")


def test_buzzer(pin: int = 18):
    """부저 테스트"""
    print(f"부저 테스트 시작 (GPIO {pin})")
    
    buzzer = Buzzer(pin)
    
    try:
        print("짧은 삑 소리...")
        buzzer.beep_pattern("short")
        time.sleep(1)
        
        print("긴 삑 소리...")
        buzzer.beep_pattern("long")
        time.sleep(1)
        
        print("알람 패턴...")
        buzzer.beep_pattern("alarm")
        time.sleep(1)
        
        print("5초 알람 (Ctrl+C로 중단)...")
        buzzer.alarm_sound(5)
        
        print("테스트 완료!")
        
    except KeyboardInterrupt:
        print("\n테스트 중단")
    finally:
        buzzer.cleanup()


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 테스트 실행
    test_buzzer(pin=18)  # GPIO 핀 번호 변경 가능