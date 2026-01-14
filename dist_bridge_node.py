import os
import json
import socket
import time

# 설계도에 정의된 격리된 워크스페이스 경로
BASE_DIR = "C:/AI_Workspace"
LEDGER_FILE = os.path.join(BASE_DIR, "Queue/shared_ledger.json")

class DistributedBridgeNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "any_input": ("*",),
                "task_name": ("STRING", {"default": "Project_2026"}),
                "destination": (["Master (Home)", "Sub-Master (School)"],),
                "performance_mode": (["Low", "Medium", "High"], {"default": "Low"}),
            }
        }

    RETURN_TYPES = ("*",)
    FUNCTION = "intercept_and_dispatch"
    OUTPUT_NODE = True # 실행의 마침표 역할
    CATEGORY = "Distributed_Control"

    def intercept_and_dispatch(self, any_input, task_name, destination, performance_mode):
        # 장부 파일이 없으면 자동 생성
        if not os.path.exists(LEDGER_FILE):
            os.makedirs(os.path.dirname(LEDGER_FILE), exist_ok=True)
            with open(LEDGER_FILE, 'w') as f: 
                json.dump({"sub_master": "", "last_heartbeat": 0, "tasks": []}, f)
        
        with open(LEDGER_FILE, 'r+') as f:
            ledger = json.load(f)
            new_task = {
                "task_id": f"{task_name}_{int(time.time())}",
                "origin": socket.gethostname(),
                "dest": destination,
                "perf": performance_mode, # 저/중/고 설정 전달
                "status": "pending",
                "timestamp": time.time()
            }
            ledger["tasks"].append(new_task)
            f.seek(0); json.dump(ledger, f, indent=4); f.truncate()
            
        print(f"[*] 작업 '{task_name}'이 장부에 등록되었습니다. 슬레이브가 연산을 시작합니다.")
        return (any_input,)

NODE_CLASS_MAPPINGS = {"DistributedBridgeNode": DistributedBridgeNode}