# 🚢 AI 기반 조선소 정반 최적 배치 및 실시간 스케줄링 플랫폼

본 프로젝트는 **872개 선박 블록과 66개 옥외/옥내 정반**을 대상으로, 조선소 생산 현장의 물리적·시간적 제약을 완벽히 준수하면서 공정 지연(Delay)과 총 소요 시간(Makespan)을 최소화하는 **수리적 최적화(OR-Tools), 심층 강화학습(PPO/DQN), 규칙 기반 휴리스틱(EST/LPT/SPT 등)** 융합 스케줄링 플랫폼입니다.

---

## 1. 🎯 4대 핵심 물리/시간 제약 조건 (Hard Constraints)

모든 알고리즘은 아래 4대 제약 조건을 100% 준수하도록 검증 엔진([eval_metrics.py](file:///home/kjc/workspace/samsung_project/2차프로젝트/modeling/eval_metrics.py))을 통해 전수 감사되었습니다:

1. **공간 적합성 제약 (Spatial Feasibility)**:
   - 블록 치수($L \times W$)가 정반 치수를 초과하지 않아야 함 ($\max(L,W) \le \max(P_L,P_W) \land \min(L,W) \le \min(P_L,P_W)$).
   - 평면 90도 회전 배치를 기본 허용.
2. **크레인 인양 하중 제약 (Crane Capacity Feasibility)**:
   - 블록 중량($\text{Weight}$)이 해당 정반에 설치된 크레인의 정격 인양 하중($\text{Crane Cap}$) 이하이어야 함.
3. **착수 가능일 제약 (EST Precedence Constraint)**:
   - 블록의 계획 착수일은 선행 가공 공정 완료일(Earliest Start Date / Release Date) 이후이어야 함 ($\text{Start} \ge \text{EST}$).
4. **정반 단일 점유 및 비중첩 제약 (Sequential Non-overlapping Constraint)**:
   - 동일 정반 내에서는 선행 블록의 제작 완료일(End Day) 이후에만 차기 블록이 착수 가능 ($\text{Start}_{i+1} \ge \text{End}_i$).

---

## 2. 📊 통합 벤치마크 리더보드 (872개 블록 전수 검증)

모든 알고리즘은 동일한 블록 데이터셋(872개), 동일한 정반 환경(66개), 동일한 시뮬레이터 환경 하에서 실측되었습니다.

| 순위 | 알고리즘 | 모델 분류 | Makespan (일) | 지연 블록 수 (율) | 평균 지연 (일) | 정반 가동률 | 제약 위반 | 무결성 | 실측 계산 시간 |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Google OR-Tools CP-SAT (Ours)** | 수리적 최적화 (MIP/CP) | **1,210일** | **246개 (28.21%)** | **50.53일** | **29.41%** | 0건 | **PASS** | 18.92초 |
| **2** | **EST Heuristic (Unified Sim)** | 규칙 기반 휴리스틱 | **1,254일** | 248개 (28.44%) | 55.80일 | 28.37% | 0건 | **PASS** | 12.28초 |
| **3** | **PPO Actor-Critic (V4 Best)** | 심층 강화학습 (RL) | **1,371일** | 602개 (69.04%) | 143.06일 | 25.95% | 0건 | **PASS** | **0.65초 (0.74ms/blk)** |
| 4 | LPT Heuristic (Unified Sim) | 규칙 기반 휴리스틱 | 1,438일 | 623개 (71.44%) | 211.10일 | 24.74% | 0건 | **PASS** | 10.00초 |
| 5 | SPT Heuristic (Unified Sim) | 규칙 기반 휴리스틱 | 1,474일 | 528개 (60.55%) | 174.60일 | 24.14% | 0건 | **PASS** | 10.32초 |
| 6 | RTB Heuristic (Unified Sim) | 규칙 기반 휴리스틱 | 1,560일 | 677개 (77.64%) | 251.09일 | 22.81% | 0건 | **PASS** | 9.68초 |
| 7 | RUB Heuristic (Unified Sim) | 규칙 기반 휴리스틱 | 1,969일 | 734개 (84.17%) | 322.50일 | 18.07% | 0건 | **PASS** | 10.90초 |
| 8 | Action-Masked DQN (Ours) | 가치 기반 강화학습 (DQN) | 5,827일 | 835개 (95.76%) | 1,567.43일 | 6.11% | 0건 | **PASS** | 14.20초 |

---

## 3. 🔬 강화학습(RL) 실험 분석 및 통계 검증

### ① PPO V1 $\rightarrow$ V2 $\rightarrow$ V3 Ablation Study (3-Seed: `42, 100, 2024`)
- **V1 (Vanilla)**: 물리 제약 특성만 사용, 단순 선형 보상 $\rightarrow$ **$1,599.3 \pm 70.2$ 일**
- **V2 (Feature Eng)**: Slack, Urgency, Cluster 반영 $\rightarrow$ **$1,670.7 \pm 152.2$ 일**
- **V3 (Reward Eng)**: 다목적 가동률/분산 보상 $\rightarrow$ **$1,958.7 \pm 284.9$ 일**
- **정직한 결과 해석**: 고정된 30 에피소드 예산에서는 특성/보상 변경만으로 극적인 Makespan 단축이 발생하지 않으며, 탐색률(Entropy)과 학습률(LR)의 결합 튜닝(V4)이 필수적임을 실증함.

### ② V4 하이퍼파라미터 튜닝 및 3-Seed 통계 분석
- **최종 선정 Configuration**: `LR=1e-3, Gamma=0.99, Entropy=0.05, Reward=V2, Temperature=0.5`
- **3-Seed (`42, 100, 2024`) 통계 성과**:
  - **Makespan**: **$1,414.3 \pm 42.5$ 일** (최고 단일 Seed: **1,371일**)
  - **지연 블록 수**: **$609.7 \pm 7.5$ 개 ($69.9\%$)**
  - **872블록 전체 추론 시간**: **$0.6744 \pm 0.0823$ 초 ($0.773\text{ ms / block}$)**
  - **학습 소요 시간**: **$24.62 \pm 1.69$ 초**

---

## 4. 🚨 동적 시나리오 (5개 긴급 블록 실시간 재배치 실측)

스케줄 운영 도중(Day 100 마스터 스케줄 점유 상태) 5건의 긴급 납기 블록이 유입되었을 때의 실측 성능입니다:

| 평가 항목 | Action-Masked PPO RL (Ours) | EST Heuristic Rule | Google OR-Tools CP-SAT |
| :--- | :---: | :---: | :---: |
| **5개 긴급 블록 총 배정 시간** | **7.06 ms** | **0.83 ms** | N/A - full re-optimization not executed |
| **블록당 평균 의사결정 지연** | **1.412 ms / block** | **0.167 ms / block** | N/A |
| **긴급 블록 총 지연 일수** | **2,141일** | **2,078일** | N/A |
| **물리적 제약 위반 건수** | **0건 (100% Feasible)** | **0건 (100% Feasible)** | N/A |
| **기존 마스터 스케줄 간섭** | **0건 (큐 안전 적재)** | **0건 (큐 안전 적재)** | N/A |

> **분포 변화(Distribution Shift) 진단**: PPO는 Day 0부터 빈 정반에 순차 투입되는 환경으로만 사전 학습되었기 때문에, 정반 가용일이 1,000일 이상으로 차 있는 중간 상태에서는 상태 공간 분포 변화를 겪어 단순 1-Step 탐욕 규칙인 EST보다 약 63일의 추가 지연이 발생함. 향후 "돌발 시나리오 데이터 증강(Dynamic Scenario Augmentation)" 학습이 추가 고도화 과제로 도출됨.

---

## 5. 🏆 다기준 의사결정 분석 (MCDA) 및 최종 역할 정의

```
MCDA Score = 10 * [0.35 * (Min_Makespan / Makespan) + 0.25 * (Min_Delay / Delay) + 
                   0.15 * (Util / Max_Util) + 0.15 * (Min_Latency / Latency) + 0.10 * Overhead_Score]
```

| 후보 모델 | Makespan | 지연 블록 | 정반 가동률 | 블록당 지연시간 | MCDA 점수 | 최종 권장 역할 |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Google OR-Tools** | **1,210일** | **246개** | **29.41%** | 21.697 ms | **8.55점** | **정기 마스터 계획 수립 (주간/월간 배치)** |
| **EST Heuristic** | 1,254일 | 248개 | 28.37% | 14.088 ms | **8.38점** | **초경량 무결점 안전 백업 (Zero-overhead Fallback)** |
| **Action-Masked PPO** | 1,371일 | 602개 | 25.95% | **0.743 ms** | **7.83점** | **실시간 지능형 AI 디스패처 (밀리초 단위 추천)** |
| **Action-Masked DQN** | 5,827일 | 835개 | 6.11% | 16.281 ms | **2.14점** | 이산 행동 가치 기반 베이스라인 비교군 |

---

## 6. 🗂️ 아티팩트 보존 및 폴더 구조 (`data/processed/`)

모든 결과물은 5대 서브폴더로 체계적으로 분리·보존되어 있습니다:

```plaintext
data/processed/
├── 📁 features/          # featured_blocks.csv, featured_platens.csv
├── 📁 schedules/         # ortools, heuristic_*, ppo, dqn 최종 스케줄 CSV
├── 📁 models/            # best_rl_model.pth, ppo_model.pth, dqn_model.pth
├── 📁 experiments/       # ablation_*, hyperparameter_*, dynamic_scenario_*, mcda_*
└── 📁 reports/           # benchmark_metrics.json, *.png 시각화 차트
```

---

## 7. ⚠️ 데이터 한계점 및 향후 고도화 과제 (Current Limitations)

1. **정반 내 다중 블록 2D 패킹(Geometric Multi-Block Nesting)**:
   - 본 모델은 정반 비중첩 순차 점유(Sequential 1-Block Occupancy)를 가정합니다. 정반 내 여러 소형 블록을 테트리스처럼 동시 배치하는 2D 기하 패킹은 추후 2D Grid 시뮬레이터 확장이 필요합니다.
2. **크레인 동적 주행 궤적 및 물리 간섭(Crane Interference)**:
   - 정격 하중 한계는 모델링되었으나, 동일 베이 내 복수 크레인의 물리 주행 간섭 시간 데이터 부재로 정적 인양 적합성만 검증되었습니다.
3. **PPO 돌발 시나리오 사전 적응**:
   - 향후 학습 파이프라인에 돌발 긴급 블록 삽입 에피소드를 30% 비율로 혼합하는 Curriculum Reinforcement Learning 적용이 권장됩니다.
