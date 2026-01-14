import os
import time
import json
import socket
import threading
import subprocess
import configparser

BASE_DIR = "C:/AI_Workspace"
CONFIG_FILE = os.path.join(BASE_DIR, "config.ini")
LEDGER_FILE = os.path.join(BASE_DIR, "Queue/shared_ledger.json")

class SchoolNodeManagerV4:
    def __init__(self):
        self.node_id = socket.gethostname()
        self.role = "Slave"
        self.is_running = True
        self.config = configparser.ConfigParser()
        self.setup_env()

    def setup_env(self):
        """최초 실행 시 Low 모드로 config 생성 및 폴더 격리"""
        os.makedirs(os.path.join(BASE_DIR, "Queue"), exist_ok=True)
        os.makedirs(os.path.join(BASE_DIR, "Outputs"), exist_ok=True)
        if not os.path.exists(CONFIG_FILE):
            self.config['NETWORK'] = {'Master_Home_IP': '100.x.x.x'}
            self.config['COMFYUI_SETTINGS'] = {
                'Performance_Mode': 'Low', 
                'Listen_Port': '8188',
                'Comfy_Path': 'C:/ComfyUI_windows_portable/main.py'
            }
            with open(CONFIG_FILE, 'w') as f: self.config.write(f)
        else: self.config.read(CONFIG_FILE)

    def is_port_in_use(self, port):
        """포트 충돌 방지 로직"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', int(port))) == 0

    def start_comfyui(self, mode=None):
        """백그라운드에서 설정된 인수로 ComfyUI 실행"""
        port = self.config.get('COMFYUI_SETTINGS', 'Listen_Port', fallback='8188')
        if self.role == "Sub-Master" and self.is_port_in_use(port): return
        
        mode = mode if mode else self.config.get('COMFYUI_SETTINGS', 'Performance_Mode')
        presets = {
            "Low": "--lowvram --fp8_e4m3fn-textenc", 
            "Medium": "--normalvram --fp16-vae", 
            "High": "--highvram --fp16-vae"
        }
        args = presets.get(mode, presets["Low"])
        path = self.config.get('COMFYUI_SETTINGS', 'Comfy_Path')
        
        # 업데이트 팝업 차단 및 콘솔 창 제거
        cmd = f"python \"{path}\" --port {port} {args} --skip-reinstall-manager --disable-auto-launch"
        subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def task_worker(self):
        """장부를 감시하여 작업 수행"""
        while self.is_running:
            try:
                with open(LEDGER_FILE, 'r+') as f:
                    ledger = json.load(f)
                    for task in ledger['tasks']:
                        if task['status'] == "pending" and self.role == "Slave":
                            task['status'] = "processing"
                            task['worker'] = self.node_id
                            f.seek(0); json.dump(ledger, f, indent=4); f.truncate()
                            self.start_comfyui(task['perf'])
                            break
            except: pass
            time.sleep(5)

    def heartbeat_election(self):
        """Raft 기반 자동 서브마스터 선출"""
        while self.is_running:
            try:
                with open(LEDGER_FILE, 'r+') as f:
                    ledger = json.load(f)
                    now = time.time()
                    if not ledger.get("sub_master") or (now - ledger.get("last_heartbeat", 0) > 30):
                        ledger["sub_master"], ledger["last_heartbeat"], self.role = self.node_id, now, "Sub-Master"
                    elif ledger["sub_master"] == self.node_id:
                        ledger["last_heartbeat"], self.role = now, "Sub-Master"
                    else: self.role = "Slave"
                    f.seek(0); json.dump(ledger, f, indent=4); f.truncate()
            except: pass
            time.sleep(10)

if __name__ == "__main__":
    node = SchoolNodeManagerV4()
    threading.Thread(target=node.heartbeat_election, daemon=True).start()
    threading.Thread(target=node.task_worker, daemon=True).start()
    print(f"[{node.node_id}] 시스템 가동 중 | 역할: {node.role}")
    while True: time.sleep(1)