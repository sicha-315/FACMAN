import time
import threading
from datetime import datetime, timedelta, timezone

class SharedClock:
    """
    모든 쓰레드(시뮬레이터)가 공유하는 시뮬레이션 시간.
    - sleep_and_advance(seconds): 실제로 (seconds/sim_speed)만큼 time.sleep()하고,
      내부 current_datetime도 seconds만큼 증가.
    - get_time(): 현재 시뮬레이션 시간을 읽어온다.
    """
    def __init__(self, start_datetime, sim_speed=5.0):
        self._current_datetime = start_datetime
        self._lock = threading.Lock()
        self._sim_speed = sim_speed

    def sleep_and_advance(self, seconds):
        """
        - 실제 물리 시간으로는 seconds/self._sim_speed 초간 sleep
        - 시뮬레이션 시간(공유 Clock)은 seconds 만큼 증가
        """
        # 실제로 잠시 대기(5배속이면 seconds/5.0 만큼 대기)
        time.sleep(seconds / self._sim_speed)
        
        # 시뮬레이션 시간을 업데이트할 때는 Lock
        with self._lock:
            self._current_datetime += timedelta(seconds=seconds)

    def get_time(self):
        # 시뮬레이션 시간을 읽는 메서드
        with self._lock:
            return self._current_datetime