import os
import json
import time

BASE_DIR = "C:/AI_Workspace"
LEDGER_FILE = os.path.join(BASE_DIR, "Queue/shared_ledger.json")

def monitor():
    print("=== [Smart Factory Master Monitor] ===")
    while True:
        if os.path.exists(LEDGER_FILE):
            try:
                with open(LEDGER_FILE, 'r') as f: ledger = json.load(f)
                sm = ledger.get("sub_master", "None")
                hb = ledger.get("last_heartbeat", 0)
                status = "정상" if (time.time() - hb < 40) else "점검 필요"
                tasks = ledger.get("tasks", [])
                pending = len([t for t in tasks if t['status']=='pending'])
                print(f"\r현장 리더: {sm} | 상태: {status} | 대기 작업: {pending}개", end="")
            except: pass
        time.sleep(5)

if __name__ == "__main__": monitor()