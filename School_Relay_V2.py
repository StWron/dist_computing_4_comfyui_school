import os
import time
import json
import socket
import threading
import configparser

BASE_DIR = "C:/AI_Workspace"
LEDGER_FILE = f"{BASE_DIR}/Queue/shared_ledger.json"

class SchoolNodeManagerV2:
    def __init__(self):
        self.node_id = socket.gethostname()
        self.role = "Slave"
        self.is_running = True
        self.setup_env()

    def setup_env(self):
        os.makedirs(f"{BASE_DIR}/Queue", exist_ok=True)
        if not os.path.exists(LEDGER_FILE):
            with open(LEDGER_FILE, 'w') as f: json.dump({"sub_master": "", "last_heartbeat": 0, "tasks": []}, f)

    def heartbeat_election(self):
        """Raft 기반의 리더 선출 및 생존 신고 로직"""
        while self.is_running:
            try:
                with open(LEDGER_FILE, 'r+') as f:
                    ledger = json.load(f)
                    now = time.time()
                    last_hb = ledger.get("last_heartbeat", 0)
                    
                    # 1. 서브마스터가 없거나 죽었을 때 (30초 초과) 자동 승격
                    if not ledger.get("sub_master") or (now - last_hb > 30):
                        ledger["sub_master"] = self.node_id
                        ledger["last_heartbeat"] = now
                        self.role = "Sub-Master"
                    # 2. 내가 서브마스터라면 생존 신고 갱신
                    elif ledger["sub_master"] == self.node_id:
                        ledger["last_heartbeat"] = now
                        self.role = "Sub-Master"
                    else:
                        self.role = "Slave"
                        
                    f.seek(0)
                    json.dump(ledger, f, indent=4)
                    f.truncate()
            except: pass
            time.sleep(10)

    def guardian(self):
        """GTX 1660 온도 감시 (80도 제한)"""
        while self.is_running:
            # 임의 온도값, 실제 구현 시 GPU 센서 데이터 연결
            if 75 > 80: print("과열 방지를 위해 low 모드 유지 중...")
            time.sleep(30)

if __name__ == "__main__":
    node = SchoolNodeManagerV2()
    threading.Thread(target=node.heartbeat_election, daemon=True).start()
    threading.Thread(target=node.guardian, daemon=True).start()
    print(f"[{node.node_id}] 가동 시작. 현재 역할: {node.role}")
    while True: time.sleep(1)