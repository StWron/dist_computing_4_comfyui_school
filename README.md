# Distributed AI Computing Cluster for ComfyUI
**Smart Factory Hybrid Control Architecture Simulation**

본 프로젝트는 AI 프롬프트 엔지니어링 워크플로우를 다수의 저사양 gpu에서 작업하기 위해 제작된 분산 컴퓨팅 툴입니다
---

##보안 경고
**본 프로그램은 오직 폐쇄된 격리망 시뮬레이션 환경을 위해 설계되었습니다.**
* **실습 목적:** 본 코드는 암호화, 입력값 검증(Sanitization), 인증 로직을 포함하고 있지 않습니다.
* **보안 취약점:** 외부 노출 시 명령어 주입(Command Injection) 등의 위험이 있으므로, 실제 운영 환경에서의 사용을 금하며 연구 및 포트폴리오 시연 목적으로만 참고하시기 바랍니다.

---

## Key Architecture Features

### 1. 뗏목 합의 알고리즘 (분산 합의 기반 리더 선출)
* **High Availability:** 뗏목(Raft) 합의 알고리즘의 개념을 차용하여, 메인 마스터 부재 시 학원 노드 중 하나가 자동으로 **Sub-Master**로 승격되어 전체 클러스터를 통제합니다.
* **Heartbeat Mechanism:** 타임스탬프 기반의 생존 신고 로직을 통해 리더의 상태를 실시간 감시하고 자동 복구(Failover)를 수행합니다.

### 2. 하이브리드 작업 라우팅
* **유연한 작업 설정:** 사용자는 ComfyUI 노드에서 최종 작업 취합지(집 또는 학원)를 선택할 수 있으며, 서브마스터는 이 설정에 따라 결과물을 동적으로 라우팅합니다.

### 3. 하드웨어 보호
* **장비 보호:** 보급형 GPU의 과열을 방지하기 위해 실시간 온도 모니터링 및 `low` 성능 프로파일을 강제 적용하여 하드웨어 안정성을 확보합니다.

---

## File Structure
* `Master_Controller.py`: 중앙 관제 및 최종 결과물 수신 (마스터용)
* `School_Relay_V2.py`: 리더 선출 및 연산 분배 엔진 (서브마스터-슬레이브용)
* `dist_bridge_node.py`: ComfyUI 내부 분산 제어 브릿지 노드

---

## Environment Setup
1. **Networking:** Tailscale 기반 가상 전용선 구축
2. **Storage Sync:** Syncthing 등을 활용한 `C:/AI_Workspace` 폴더 동기화
3. **Engine:** Python 3.12 + 및 ComfyUI Portable 환경