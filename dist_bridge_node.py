import os
import json
import socket
import time

BASE_DIR = "C:/AI_Workspace"
LEDGER_FILE = f"{BASE_DIR}/Queue/shared_ledger.json"

class DistributedBridgeNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "any_input": ("*",),
                "task_name": ("STRING", {"default": "Project_2026"}),
                "destination": (["Master (Home)", "Sub-Master (School)"],),
            }
        }

    RETURN_TYPES = ("*",)
    FUNCTION = "push_task"
    OUTPUT_NODE = True
    CATEGORY = "Distributed_Control"

    def push_task(self, any_input, task_name, destination):
        if not os.path.exists(LEDGER_FILE): return (any_input,)
        
        with open(LEDGER_FILE, 'r+') as f:
            ledger = json.load(f)
            new_task = {
                "task_id": f"{task_name}_{int(time.time())}",
                "origin": socket.gethostname(),
                "dest": destination,
                "status": "pending"
            }
            ledger["tasks"].append(new_task)
            f.seek(0)
            json.dump(ledger, f, indent=4)
        return (any_input,)

NODE_CLASS_MAPPINGS = {"DistributedBridgeNode": DistributedBridgeNode}