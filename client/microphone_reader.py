import time
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import numpy as np
import logging

logger = logging.getLogger(__name__)


class MicrophoneReader:
    """MCP3008 + FQ-057 마이크로 소음 레벨 측정"""
    
    def __init__(self, channel: int = 0, threshold: int = 55):
        """
        Args:
            channel: MCP3008 채널 번호 (0-7)
            threshold: 코골이 감지 임계값 (dB)
        """
        self.channel = channel
        self.threshold = threshold
        
        # SPI 설정
        spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
        cs = digitalio.DigitalInOut(board.CE0)
        
        # MCP3008 초기화
        mcp = MCP.MCP3008(spi, cs)
        self.chan = AnalogIn(mcp, getattr(MCP, f'P{channel}'))
        
        logger.info(f"마이크 초기화 완료 (CH{channel}, 임계값: {threshold}dB)")
    
    def read_samples(self, duration: float = 1.0, sample_rate: int = 100):
        """
        일정 시간 동안 샘플 수집
        
        Args:
            duration: 측정 시간 (초)
            sample_rate: 초당 샘플 수
            
        Returns:
            샘플 배열
        """
        samples = []
        interval = 1.0 / sample_rate
        end_time = time.time() + duration
        
        while time.time() < end_time:
            samples.append(self.chan.value)
            time.sleep(interval)
        
        return np.array(samples)
    
    def calculate_decibel(self, samples):
        """
        샘플에서 데시벨 계산
        
        Args:
            samples: 아날로그 값 배열
            
        Returns:
            데시벨 값 (dB)
        """
        # RMS (Root Mean Square) 계산
        rms = np.sqrt(np.mean(samples ** 2))
        
        # 최소값 설정 (0으로 나누기 방지)
        if rms < 100:
            rms = 100
        
        # 최대 ADC 값
        max_value = 65472.0
        
        # 상대 데시벨 계산 (0-100 범위로 정규화)
        ratio = rms / max_value
        db = 20 * np.log10(ratio) + 100  # 기준값 조정
        
        # 실용적 범위로 제한 (30-90dB)
        db = max(30, min(90, db))
        
        return db
    
    def measure_noise_level(self, duration: float = 2.0):
        """
        소음 레벨 측정
        
        Args:
            duration: 측정 시간 (초)
            
        Returns:
            (평균 dB, 최대 dB, 코골이 감지 여부)
        """
        try:
            # 샘플 수집
            samples = self.read_samples(duration=duration, sample_rate=100)
            
            # 디버깅: 원시 값 출력
            logger.info(f"샘플 통계 - 최소: {np.min(samples)}, 최대: {np.max(samples)}, 평균: {np.mean(samples):.1f}")
            
            # 구간별 데시벨 계산 (0.5초씩)
            chunk_size = 50  # 100 samples/sec * 0.5 sec
            decibels = []
            
            for i in range(0, len(samples), chunk_size):
                chunk = samples[i:i+chunk_size]
                if len(chunk) > 0:
                    db = self.calculate_decibel(chunk)
                    decibels.append(db)
            
            avg_db = np.mean(decibels)
            max_db = np.max(decibels)
            
            # 코골이 감지 (임계값 초과)
            is_snoring = max_db > self.threshold
            
            logger.info(f"소음 측정: 평균 {avg_db:.1f}dB, 최대 {max_db:.1f}dB, 코골이: {is_snoring}")
            
            return (round(avg_db, 1), round(max_db, 1), is_snoring)
            
        except Exception as e:
            logger.error(f"소음 측정 실패: {e}")
            return (0.0, 0.0, False)
    
    def continuous_monitor(self, interval: int = 30, callback=None):
        """
        연속 모니터링
        
        Args:
            interval: 측정 간격 (초)
            callback: 결과 콜백 함수 (avg_db, max_db, is_snoring)
        """
        logger.info(f"연속 모니터링 시작 ({interval}초 간격)")
        
        try:
            while True:
                avg_db, max_db, is_snoring = self.measure_noise_level()
                
                if callback:
                    callback(avg_db, max_db, is_snoring)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("모니터링 중단")


def test_microphone(duration: int = 10):
    """마이크 테스트"""
    print(f"마이크 테스트 시작 ({duration}초)")
    print("조용한 환경에서 테스트 후, 소리를 내보세요.")
    print("Ctrl+C로 종료\n")
    
    mic = MicrophoneReader(channel=0, threshold=55)
    
    def print_result(avg_db, max_db, is_snoring):
        status = "🔴 코골이 감지!" if is_snoring else "🟢 정상"
        print(f"평균: {avg_db:.1f}dB | 최대: {max_db:.1f}dB | {status}")
    
    try:
        mic.continuous_monitor(interval=3, callback=print_result)
    except KeyboardInterrupt:
        print("\n테스트 종료")


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 테스트 실행
    test_microphone()