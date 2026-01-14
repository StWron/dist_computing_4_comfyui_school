import os
import time
import json
import socket
import threading
import subprocess
import configparser
import sys
import logging

# [로그 설정] C:/AI_Workspace/relay.log에 작업 내역 기록
logging.basicConfig(
    filename="C:/AI_Workspace/relay.log",
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

BASE_DIR = "C:/AI_Workspace"
LEDGER_FILE = os.path.join(BASE_DIR, "Queue/shared_ledger.json")
MAX_RETRIES = 3  # [무한 에러 방지] 최대 재시도 횟수

class SchoolNodeManagerV4_1:
    def __init__(self):
        self.node_id = socket.gethostname()
        self.role = "Slave"
        self.is_running = True
        self.setup_env()

    def find_comfyui_exe(self):
        """현재 폴더 및 하위 폴더에서 ComfyUI.exe 자동 탐색"""
        current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        target = os.path.join(current_dir, "ComfyUI.exe")
        if os.path.exists(target): return target
        for root, dirs, files in os.walk(current_dir):
            if "ComfyUI.exe" in files: return os.path.join(root, "ComfyUI.exe")
        return None

    def setup_env(self):
        os.makedirs(os.path.join(BASE_DIR, "Queue"), exist_ok=True)
        os.makedirs(os.path.join(BASE_DIR, "Outputs"), exist_ok=True)
        self.config = configparser.ConfigParser()
        detected_path = self.find_comfyui_exe()
        
        config_path = os.path.join(BASE_DIR, "config.ini")
        if not os.path.exists(config_path):
            self.config['COMFYUI_SETTINGS'] = {
                'Performance_Mode': 'Low', 
                'Listen_Port': '8188',
                'Comfy_Exe_Path': detected_path if detected_path else "Not_Found"
            }
            with open(config_path, 'w', encoding='utf-8') as f: self.config.write(f)
        else: self.config.read(config_path, encoding='utf-8')
        self.comfy_exe_path = self.config.get('COMFYUI_SETTINGS', 'Comfy_Exe_Path')

    def is_port_in_use(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', int(port))) == 0

    def start_comfyui(self, mode, task_id):
        """엔진 실행 및 결과 파일 생성 여부 실질 검증"""
        port = self.config.get('COMFYUI_SETTINGS', 'Listen_Port', fallback='8188')
        args = "--lowvram --fp8_e4m3fn-textenc" if mode == "Low" else "--normalvram"
        
        # 실행 전 결과물 폴더 상태 기록
        output_path = os.path.join(BASE_DIR, "Outputs")
        initial_files = set(os.listdir(output_path))
        
        cmd = f"\"{self.comfy_exe_path}\" --port {port} {args} --skip-reinstall-manager --disable-auto-launch"
        try:
            subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            logging.info(f"Task {task_id} 연산 시작")
            
            # 연산 완료 대기 (워크플로우에 따라 시간 조절 가능)
            time.sleep(60) 
            
            # 실행 후 파일 생성 여부 대조
            current_files = set(os.listdir(output_path))
            if len(current_files) > len(initial_files):
                logging.info(f"Task {task_id} 결과물 확인 성공")
                return True
            else:
                logging.warning(f"Task {task_id} 연산은 수행되었으나 결과물이 없음")
                return False
        except Exception as e:
            logging.error(f"Task {task_id} 시스템 에러: {str(e)}")
            return False

    def task_worker(self):
        while self.is_running:
            try:
                if os.path.exists(LEDGER_FILE):
                    with open(LEDGER_FILE, 'r+') as f:
                        ledger = json.load(f)
                        for task in ledger['tasks']:
                            if 'retry_count' not in task: task['retry_count'] = 0
                            
                            if task['status'] == "pending" and self.role == "Slave":
                                task['status'] = "processing"
                                task['worker'] = self.node_id
                                f.seek(0); json.dump(ledger, f, indent=4); f.truncate()
                                
                                # 실질 완료 판정 수행
                                success = self.start_comfyui(task['perf'], task['task_id'])
                                
                                # 결과 장부 반영
                                f.seek(0); ledger = json.load(f)
                                for t in ledger['tasks']:
                                    if t['task_id'] == task['task_id']:
                                        if success:
                                            t['status'] = "completed"
                                        else:
                                            t['retry_count'] += 1
                                            if t['retry_count'] >= MAX_RETRIES:
                                                t['status'] = "failed"
                                                t['error_msg'] = "최대 재시도 초과 (결과물 미생성)"
                                            else:
                                                t['status'] = "pending"
                                        break
                                f.seek(0); json.dump(ledger, f, indent=4); f.truncate()
                                break
            except: pass
            time.sleep(5)

    def heartbeat_election(self):
        while self.is_running:
            try:
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
    node = SchoolNodeManagerV4_1()
    threading.Thread(target=node.heartbeat_election, daemon=True).start()
    threading.Thread(target=node.task_worker, daemon=True).start()
    print(f"[{node.node_id}] V4.1 가동 | 역할: {node.role}")
    while True: time.sleep(1)