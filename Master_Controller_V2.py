import os
import json
import time

BASE_DIR = "C:/AI_Workspace"
LEDGER_FILE = os.path.join(BASE_DIR, "Queue/shared_ledger.json")

def monitor():
    print("=== [Smart Factory Master Monitor V2] ===")
    while True:
        if os.path.exists(LEDGER_FILE):
            try:
                with open(LEDGER_FILE, 'r') as f: ledger = json.load(f)
                sm = ledger.get("sub_master", "None")
                hb = ledger.get("last_heartbeat", 0)
                status = "정상" if (time.time() - hb < 40) else "점검 필요"
                
                tasks = ledger.get("tasks", [])
                pending = [t for t in tasks if t['status']=='pending']
                failed = [t for t in tasks if t['status']=='failed']
                
                # 실시간 요약 정보
                print(f"\r리더: {sm} | 상태: {status} | 대기: {len(pending)} | 실패: {len(failed)}", end="")
                
                # 실패 내역 존재 시 출력
                if failed:
                    print("\n\n[최근 에러 리포트]")
                    for ft in failed[-3:]:
                        print(f"- ID: {ft['task_id']} | 사유: {ft.get('error_msg', '연산 실패')}")
                    print("-" * 40)
            except: pass
        time.sleep(5)

if __name__ == "__main__": monitor()