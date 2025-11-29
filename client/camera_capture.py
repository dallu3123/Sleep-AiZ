import os
import time
import logging
from datetime import datetime
from typing import Optional, Tuple
from picamera2 import Picamera2
from PIL import Image

logger = logging.getLogger(__name__)

class NoIRCamera:
    """ NoIR 카메라 클래스 """
    def __init__(
        self,
        resolution: Tuple[int, int] = (640, 480),
        image_format: str = "jpg",
        image_quality: int = 85,
    ):
        """
            Args:
            resolution: 카메라 해상도 (가로, 세로)
            image_format: 이미지 포맷
            image_quality: 이미지 품질
        """
        self.resolution = resolution
        self.image_format = image_format.lower()
        self.image_quality = image_quality

        self.camera = Picamera2()

        config = self.camera.create_still_configuration(
            main={"size": self.resolution, "format": "RGB888"},
        )

        self.camera.configure(config)

        logger.info(f"NoIR 카메라 초기화 완료 (해상도: {self.resolution}, 포맷: {self.image_format}, 품질: {self.image_quality})")

    def start(self):
        try:
            self.camera.start()
            time.sleep(2)
            logger.info("카메라 시작 완료")
        except Exception as e:
            logger.error(f"카메라 시작 실패: {e}")
            raise

    def capture(self, save_path: str) -> Optional[bytes]:
        """
        이미지 캡처

        Returns:
            bytes: 이미지 데이터
        """
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            logger.info("사진 촬영 중 ...")
            image = self.camera.capture_array()

            pil_image = Image.fromarray(image)

            if self.image_format == "jpg" or self.image_format == "jpeg":
                pil_image.save(save_path, "JPEG", quality=self.image_quality)
            elif self.image_format == "png":
                pil_image.save(save_path, "PNG")
            else:
                raise ValueError(f"지원하지 않는 이미지 포맷: {self.image_format}")

            file_size = os.path.getsize(save_path)
            logger.info(f"사진 촬영 완료 (파일 경로: {save_path}, 파일 크기: {file_size} bytes)")

            return save_path

        except Exception as e:
            logger.error(f"사진 촬영 실패: {e}")
            return None

    def capture_with_timestamp(self, save_path: str) -> Optional[str]:
        """
        타임스탬프 포함 사진 촬영

        Returns:
            str: 저장된 이미지 경로
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"sleep_{timestamp}.{self.image_format}"
        full_path = os.path.join(save_path, file_name)

        return self.capture(full_path)

    def stop(self):
        try:
            self.camera.stop()
            logger.info("카메라 종료 완료")
        except Exception as e:
            logger.error(f"카메라 종료 실패: {e}")

    def close(self):
        """카메라 리소스 해제"""
        try:
            self.camera.close()
            logger.info("카메라 리소스 해제 완료")
        except Exception as e:
            logger.error(f"카메라 리소스 해제 실패: {e}")

def test_camera(resolution: Tuple[int, int] = (640, 480),
                test_count: int = 3,
                interval: int = 2):
    """
    카메라 테스트 함수
    Args:
        resolution: 이미지 해상도
        test_count: 테스트 촬영 횟수
        interval: 촬영 간격 (초)
    """
    print(f"카메라 테스트 시작 ({resolution[0]}x{resolution[1]})")
    print(f"{test_count}장의 사진을 {interval}초 간격으로 촬영합니다.")

    test_dir = "/tmp/sleep_aiz_test"
    os.makedirs(test_dir, exist_ok=True)

    camera = NoIRCamera(resolution=resolution)

    try:
        camera.start()

        for i in range(test_count):
            print(f"\n[{i+1}/{test_count}] 촬영 중...")
            result = camera.capture_with_timestamp(test_dir)

            if result:
                print(f"✅ 저장 완료: {result}")
            else:
                print("❌ 촬영 실패")

            if i < test_count - 1:
                print(f"{interval}초 대기 중...")
                time.sleep(interval)

        print(f"\n테스트 완료! 저장 위치: {test_dir}")

    except KeyboardInterrupt:
        print("\n테스트 중단")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        camera.stop()
        camera.close()

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 카메라 테스트
    test_camera(resolution=(640, 480), test_count=3, interval=2)