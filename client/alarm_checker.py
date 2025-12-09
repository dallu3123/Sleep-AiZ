import requests
import logging
from datetime import datetime, time as dt_time
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class AlarmChecker:
    """서버에서 알람 확인 및 관리"""
    
    def __init__(self, server_url: str, timeout: int = 10):
        """
        Args:
            server_url: 서버 URL
            timeout: 요청 타임아웃 (초)
        """
        self.server_url = server_url
        self.timeout = timeout
    
    def get_all_alarms(self) -> List[Dict]:
        """모든 알람 조회"""
        try:
            url = f"{self.server_url}/api/alarms"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"알람 조회 실패: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"알람 조회 중 오류: {e}")
            return []
    
    def check_ringing_alarms(self) -> List[Dict]:
        """현재 울리고 있는 알람 확인"""
        try:
            url = f"{self.server_url}/api/alarms/ringing/check"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('ringing_alarms', [])
            else:
                logger.error(f"울리는 알람 확인 실패: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"울리는 알람 확인 중 오류: {e}")
            return []
    
    def should_ring_now(self, alarm: Dict) -> bool:
        """지금 알람이 울려야 하는지 확인"""
        if not alarm.get('enabled'):
            return False
        
        # 현재 시간
        now = datetime.now()
        current_time = now.time()
        current_weekday = str(now.weekday())  # 0=월요일, 6=일요일
        
        # 알람 시간 파싱
        alarm_time_str = alarm.get('alarm_time')
        if not alarm_time_str:
            return False
        
        try:
            # "HH:MM" 또는 "HH:MM:SS" 형식
            time_parts = alarm_time_str.split(':')
            alarm_hour = int(time_parts[0])
            alarm_minute = int(time_parts[1])
            alarm_time = dt_time(alarm_hour, alarm_minute)
            
            # 시간이 일치하는지 확인 (분 단위)
            time_match = (current_time.hour == alarm_time.hour and 
                         current_time.minute == alarm_time.minute)
            
            if not time_match:
                return False
            
            # 반복 요일 확인
            repeat_days = alarm.get('repeat_days')
            if not repeat_days:
                # 반복 없으면 매일
                return True
            
            # 오늘이 반복 요일에 포함되는지 확인
            repeat_list = repeat_days.split(',')
            return current_weekday in repeat_list
            
        except Exception as e:
            logger.error(f"알람 시간 파싱 오류: {e}")
            return False
    
    def set_alarm_ringing(self, alarm_id: int, is_ringing: bool) -> bool:
        """알람 울림 상태 설정"""
        try:
            url = f"{self.server_url}/api/alarms/{alarm_id}/ring"
            params = {'is_ringing': is_ringing}
            response = requests.post(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                logger.info(f"알람 {alarm_id} 상태 변경: is_ringing={is_ringing}")
                return True
            else:
                logger.error(f"알람 상태 변경 실패: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"알람 상태 변경 중 오류: {e}")
            return False
    
    def check_and_trigger_alarms(self) -> List[Dict]:
        """
        알람 확인하고 울려야 할 알람 반환
        
        Returns:
            울려야 할 알람 리스트
        """
        alarms = self.get_all_alarms()
        alarms_to_ring = []
        
        for alarm in alarms:
            if self.should_ring_now(alarm) and not alarm.get('is_ringing'):
                # 서버에 울림 상태로 설정
                if self.set_alarm_ringing(alarm['id'], True):
                    alarms_to_ring.append(alarm)
                    logger.info(f"알람 트리거: {alarm.get('label', 'Alarm')} at {alarm.get('alarm_time')}")
        
        return alarms_to_ring


def test_alarm_checker(server_url: str):
    """알람 체커 테스트"""
    print(f"알람 체커 테스트: {server_url}")
    
    checker = AlarmChecker(server_url)
    
    # 모든 알람 조회
    print("\n=== 모든 알람 ===")
    alarms = checker.get_all_alarms()
    for alarm in alarms:
        print(f"- {alarm.get('alarm_time')} | {alarm.get('label')} | Enabled: {alarm.get('enabled')}")
    
    # 울려야 할 알람 확인
    print("\n=== 지금 울려야 할 알람 확인 ===")
    to_ring = checker.check_and_trigger_alarms()
    if to_ring:
        for alarm in to_ring:
            print(f"🔔 알람: {alarm.get('label')} at {alarm.get('alarm_time')}")
    else:
        print("울릴 알람 없음")
    
    # 울리고 있는 알람 확인
    print("\n=== 현재 울리고 있는 알람 ===")
    ringing = checker.check_ringing_alarms()
    if ringing:
        for alarm in ringing:
            print(f"🔔 울리는 중: {alarm.get('label')} at {alarm.get('alarm_time')}")
    else:
        print("울리는 알람 없음")


if __name__ == "__main__":
    import sys
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 테스트 실행
    if len(sys.argv) > 1:
        test_alarm_checker(sys.argv[1])
    else:
        print("사용법: python alarm_checker.py <서버_URL>")
        print("예: python alarm_checker.py http://172.30.1.13:8000")