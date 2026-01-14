import os
import time
import json
import socket
import threading
import subprocess
import configparser
import sys

# 관제탑 워크스페이스 (데이터 공유용)
BASE_DIR = "C:/AI_Workspace"
CONFIG_FILE = os.path.join(BASE_DIR, "config.ini")
LEDGER_FILE = os.path.join(BASE_DIR, "Queue/shared_ledger.json")

class SchoolNodeManagerV4:
    def __init__(self):
        self.node_id = socket.gethostname()
        self.role = "Slave"
        self.is_running = True
        self.config = configparser.ConfigParser()
        self.comfy_exe_path = None
        self.setup_env()

    def find_comfyui_exe(self):
        """현재 실행 폴더 및 하위 폴더에서 ComfyUI.exe를 자동 탐색"""
        # 1. 현재 EXE가 실행된 위치 (빌드 후에는 sys.executable 기준)
        current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        
        print(f"[*] 엔진 탐색 시작: {current_dir}")
        
        # 2. 우선 현재 폴더에 있는지 확인
        target = os.path.join(current_dir, "ComfyUI.exe")
        if os.path.exists(target): return target
        
        # 3. 하위 폴더 전체 탐색 (깊이 제한 없이 탐색)
        for root, dirs, files in os.walk(current_dir):
            if "ComfyUI.exe" in files:
                return os.path.join(root, "ComfyUI.exe")
        
        return None

    def setup_env(self):
        """환경 설정 및 엔진 자동 연결"""
        os.makedirs(os.path.join(BASE_DIR, "Queue"), exist_ok=True)
        os.makedirs(os.path.join(BASE_DIR, "Outputs"), exist_ok=True)
        
        # 엔진 자동 탐색
        detected_path = self.find_comfyui_exe()
        
        if not os.path.exists(CONFIG_FILE):
            self.config['NETWORK'] = {'Master_Home_IP': '100.x.x.x'}
            self.config['COMFYUI_SETTINGS'] = {
                'Performance_Mode': 'Low', 
                'Listen_Port': '8188',
                'Comfy_Exe_Path': detected_path if detected_path else "Not_Found"
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: self.config.write(f)
        else:
            self.config.read(CONFIG_FILE, encoding='utf-8')
            # 기존 설정에 경로가 없거나 Not_Found면 새로 탐색한 경로 적용
            if self.config.get('COMFYUI_SETTINGS', 'Comfy_Exe_Path') == "Not_Found" and detected_path:
                self.config.set('COMFYUI_SETTINGS', 'Comfy_Exe_Path', detected_path)
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f: self.config.write(f)

        self.comfy_exe_path = self.config.get('COMFYUI_SETTINGS', 'Comfy_Exe_Path')
        if self.comfy_exe_path == "Not_Found":
            print("[!] 경고: ComfyUI.exe를 찾지 못했습니다. config.ini를 수동 확인하세요.")

    def is_port_in_use(self, port):
        """포트 체크를 통해 중복 실행 방지 (서브마스터용)"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', int(port))) == 0

    def start_comfyui(self, mode=None):
        """ComfyUI.exe 직접 실행 (백그라운드)"""
        if not self.comfy_exe_path or self.comfy_exe_path == "Not_Found": return
        
        port = self.config.get('COMFYUI_SETTINGS', 'Listen_Port', fallback='8188')
        
        # 이미 사용자가 켰거나 다른 프로세스가 사용 중이면 실행 스킵
        if self.is_port_in_use(port): 
            print(f"[*] 포트 {port} 사용 중. 엔진 실행을 생략합니다.")
            return
        
        mode = mode if mode else self.config.get('COMFYUI_SETTINGS', 'Performance_Mode')
        presets = {
            "Low": "--lowvram --fp8_e4m3fn-textenc", 
            "Medium": "--normalvram", 
            "High": "--highvram"
        }
        args = presets.get(mode, presets["Low"])
        
        # EXE 직접 실행 명령 구성
        cmd = f"\"{self.comfy_exe_path}\" --port {port} {args} --skip-reinstall-manager --disable-auto-launch"
        subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        print(f"[*] ComfyUI 엔진 가동 ({mode} 모드)")

    def task_worker(self):
        """장부 감시 및 작업 수행"""
        while self.is_running:
            try:
                if os.path.exists(LEDGER_FILE):
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
        """서브마스터 선출 및 하트비트"""
        while self.is_running:
            try:
                # 장부 파일 자동 생성 로직 포함
                if not os.path.exists(LEDGER_FILE):
                    os.makedirs(os.path.dirname(LEDGER_FILE), exist_ok=True)
                    with open(LEDGER_FILE, 'w') as f: json.dump({"sub_master": "", "last_heartbeat": 0, "tasks": []}, f)

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
    print(f"[{node.node_id}] 매니저 가동 중 | 역할: {node.role} | 엔진: {node.comfy_exe_path}")
    while True: time.sleep(1)