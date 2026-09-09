from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
import subprocess
import time
from urllib.request import urlopen


@dataclass
class RestartSupervisor:
    """Orchestration contract only; process launch is intentionally injected."""
    states: list[str] = field(default_factory=list)

    def restart(self, *, drain: Callable[[], None], close_db: Callable[[], None], release_owner_lock: Callable[[], None], start_new: Callable[[], None], health_check: Callable[[], bool], restore_old: Callable[[], None]) -> dict:
        try:
            for state,action in (("DRAINING",drain),("CLOSE_DB",close_db),("RELEASE_OWNER_LOCK",release_owner_lock),("START_NEW",start_new)):
                self.states.append(state);action()
            self.states.append("HEALTH_CHECK")
            if not health_check(): raise RuntimeError("NEW_PROCESS_UNHEALTHY")
            self.states.append("READY")
            return {"status":"READY","states":self.states}
        except Exception as exc:
            self.states.append("ROLLBACK_OLD_CONFIG")
            restore_old()
            self.states.append("ROLLED_BACK")
            return {"status":"ROLLED_BACK","states":self.states,"error":str(exc)}


class LocalServiceSupervisor:
    """Real local-process adapter used only for controlled maintenance windows."""
    def __init__(self, command: list[str], health_url: str):
        self.command=command;self.health_url=health_url;self.process=None
    def start(self):
        self.process=subprocess.Popen(self.command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate();self.process.wait(timeout=10)
    def healthy(self, timeout_seconds=8):
        deadline=time.monotonic()+timeout_seconds
        while time.monotonic()<deadline:
            try:
                with urlopen(self.health_url,timeout=1) as response:
                    if response.status == 200:return True
            except Exception: time.sleep(.15)
        return False
