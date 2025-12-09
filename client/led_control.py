import RPi.GPIO as GPIO
import time
import logging

logger = logging.getLogger(__name__)


class LED:
    """LED 제어 클래스"""
    
    def __init__(self, pin: int = 17):
        """
        Args:
            pin: LED가 연결된 GPIO 핀 번호 (BCM)
        """
        self.pin = pin
        self.is_on = False
        
        # GPIO 설정
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)
        
        logger.info(f"LED 초기화 완료 (GPIO {self.pin})")
    
    def on(self):
        """LED 켜기"""
        GPIO.output(self.pin, GPIO.HIGH)
        self.is_on = True
        logger.debug("LED ON")
    
    def off(self):
        """LED 끄기"""
        GPIO.output(self.pin, GPIO.LOW)
        self.is_on = False
        logger.debug("LED OFF")
    
    def toggle(self):
        """LED 토글"""
        if self.is_on:
            self.off()
        else:
            self.on()
    
    def blink(self, times: int = 3, interval: float = 0.5):
        """
        깜빡이기
        
        Args:
            times: 깜빡일 횟수
            interval: 깜빡임 간격 (초)
        """
        for _ in range(times):
            self.on()
            time.sleep(interval)
            self.off()
            time.sleep(interval)
    
    def pulse(self, duration: float = 2.0, steps: int = 50):
        """
        서서히 밝아졌다 어두워지기 (PWM)
        
        Args:
            duration: 지속 시간 (초)
            steps: 단계 수
        """
        pwm = GPIO.PWM(self.pin, 100)  # 100Hz
        pwm.start(0)
        
        try:
            step_delay = duration / (steps * 2)
            
            # 밝아지기
            for i in range(steps):
                duty = (i / steps) * 100
                pwm.ChangeDutyCycle(duty)
                time.sleep(step_delay)
            
            # 어두워지기
            for i in range(steps, 0, -1):
                duty = (i / steps) * 100
                pwm.ChangeDutyCycle(duty)
                time.sleep(step_delay)
        
        finally:
            pwm.stop()
            self.off()
    
    def fade_in(self, duration: float = 1.0):
        """서서히 켜기"""
        pwm = GPIO.PWM(self.pin, 100)
        pwm.start(0)
        
        steps = 50
        for i in range(steps + 1):
            duty = (i / steps) * 100
            pwm.ChangeDutyCycle(duty)
            time.sleep(duration / steps)
        
        pwm.stop()
        self.on()
    
    def fade_out(self, duration: float = 1.0):
        """서서히 끄기"""
        pwm = GPIO.PWM(self.pin, 100)
        pwm.start(100)
        
        steps = 50
        for i in range(steps, -1, -1):
            duty = (i / steps) * 100
            pwm.ChangeDutyCycle(duty)
            time.sleep(duration / steps)
        
        pwm.stop()
        self.off()
    
    def alarm_pattern(self):
        """알람 패턴 (빠른 깜빡임)"""
        for _ in range(5):
            self.on()
            time.sleep(0.1)
            self.off()
            time.sleep(0.1)
    
    def success_pattern(self):
        """성공 패턴 (천천히 3번)"""
        self.blink(times=3, interval=0.3)
    
    def cleanup(self):
        """리소스 정리"""
        self.off()
        GPIO.cleanup()
        logger.info("LED 리소스 정리 완료")


def test_led(pin: int = 17):
    """LED 테스트"""
    print(f"LED 테스트 시작 (GPIO {pin})")
    print("다양한 패턴을 테스트합니다...\n")
    
    led = LED(pin)
    
    try:
        print("1. 기본 켜기/끄기")
        led.on()
        time.sleep(1)
        led.off()
        time.sleep(1)
        
        print("2. 깜빡이기 (5번)")
        led.blink(times=5, interval=0.3)
        time.sleep(1)
        
        print("3. 펄스 효과")
        led.pulse(duration=3.0)
        time.sleep(1)
        
        print("4. 페이드 인")
        led.fade_in(duration=2.0)
        time.sleep(0.5)
        
        print("5. 페이드 아웃")
        led.fade_out(duration=2.0)
        time.sleep(1)
        
        print("6. 알람 패턴")
        led.alarm_pattern()
        time.sleep(1)
        
        print("7. 성공 패턴")
        led.success_pattern()
        
        print("\n테스트 완료!")
        
    except KeyboardInterrupt:
        print("\n테스트 중단")
    finally:
        led.cleanup()


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_led(pin=17)