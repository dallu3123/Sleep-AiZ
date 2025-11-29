import time
import board
import adafruit_dht
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class DHT22Sensor:
    """DHT22 온습도 센서 클래스"""

    def __init__(self, pin_number: int, retry_count: int = 3, retry_delay: int = 2):
        """
        Args:
            pin_number: GPIO 핀 번호
            retry_count: 읽기 실패 시 재시도 횟수
            retry_delay: 재시도 대기 시간 (초)
        """
        self.retry_count = retry_count
        self.retry_delay = retry_delay

        # GPIO 핀 매핑
        pin_map = {
            4: board.D4,
            17: board.D17,
            27: board.D27,
            22: board.D22,
            # 필요한 핀 추가
        }

        if pin_number not in pin_map:
            raise ValueError(f"지원하지 않는 핀 번호: {pin_number}. 지원 핀: {list(pin_map.keys())}")

        self.pin = pin_map[pin_number]
        self.device = adafruit_dht.DHT22(self.pin)
        logger.info(f"DHT22 센서 초기화 완료 (GPIO {pin_number})")

    def read(self) -> Optional[Tuple[float, float]]:
        """
        온도와 습도 읽기

        Returns:
            (temperature, humidity) 튜플 또는 실패 시 None
        """
        for attempt in range(self.retry_count):
            try:
                temperature = self.device.temperature
                humidity = self.device.humidity

                # 유효성 검사
                if temperature is not None and humidity is not None:
                    # 합리적인 범위 체크
                    if -40 <= temperature <= 80 and 0 <= humidity <= 100:
                        logger.info(f"센서 읽기 성공: {temperature:.1f}°C, {humidity:.1f}%")
                        return (round(temperature, 2), round(humidity, 2))
                    else:
                        logger.warning(f"비정상 값 감지: {temperature}°C, {humidity}%")

            except RuntimeError as e:
                logger.warning(f"센서 읽기 시도 {attempt + 1}/{self.retry_count} 실패: {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"예상치 못한 오류: {e}")
                break

        logger.error("센서 읽기 최종 실패")
        return None

    def close(self):
        """센서 리소스 해제"""
        try:
            self.device.exit()
            logger.info("센서 리소스 해제 완료")
        except Exception as e:
            logger.warning(f"센서 종료 중 오류: {e}")


def test_sensor(pin_number: int = 4):
    """센서 테스트 함수"""
    print(f"DHT22 센서 테스트 시작 (GPIO {pin_number})")
    print("Ctrl+C로 종료")

    sensor = DHT22Sensor(pin_number)

    try:
        while True:
            result = sensor.read()
            if result:
                temp, hum = result
                print(f"온도: {temp}°C, 습도: {hum}%")
            else:
                print("센서 읽기 실패")

            time.sleep(5)  # 5초마다 테스트

    except KeyboardInterrupt:
        print("\n테스트 종료")
    finally:
        sensor.close()


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 센서 테스트
    test_sensor(pin_number=4)