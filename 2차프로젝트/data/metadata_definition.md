# 📚 스마트 조선소 정반 배치 데이터셋 메타정의서 (Data Dictionary)

> **프로젝트:** 스마트 조선소 시공간 정반 배치 최적화 (Spatial-Temporal Block Platen Scheduling & Optimization)  
> **기준 데이터셋:** 총 872개 선박 조립 블록, 66개 조립 정반 작업장, 3,000 에피소드 DRL 학습 로그 및 5대 휴리스틱 벤치마크  
> **저장 위치:** `samsung_project/2차프로젝트/data/standardized/`

---

## 📑 1. 블록 정보 테이블 (`block_information.csv`)

- **설명:** 조선소 대조립 공정에 투입되는 선박 블록(Block)의 물리적 규격, 납기 일정, 공정 소요 기간을 정의한 원천 데이터셋입니다.
- **총 레코드 수:** 872건

| 컬럼명 (English) | 원본 한자명 | 한글 설명 | 데이터 타입 | 예시값 | 제약조건 및 비즈니스 의미 |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`seq_id`** | 序号 | 블록 일련번호 | `Integer` | `757` | 블록 고유 식별자 (PK) |
| **`ship_id`** | 船号 | 선박 호선 번호 | `String` | `H1088` | 건조 대상 선박 고유 코드 |
| **`block_id`** | 分段号 | 블록 번호 | `String` | `284` | 선체 내 조립 블록 식별 번호 |
| **`block_type`** | 分段类型 | 블록 유형 | `String` | `平` (평블록) | 블록 형상 (평블록, 곡블록, 입체블록 등) |
| **`length_m`** | 长 | 블록 길이 (m) | `Float` | `20.0` | 블록의 가로 길이 (정반 가로 길이 이하이어야 함) |
| **`width_m`** | 宽 | 블록 폭 (m) | `Float` | `18.4` | 블록의 세로 폭 (정반 세로 폭 이하이어야 함) |
| **`weight_ton`** | 分段重量 | 블록 중량 (Ton) | `Float` | `211.02` | 블록 무게 (정반 크레인 인양 능력 이하이어야 함) |
| **`assembly_start_date`** | 上胎日期 | 정반 탑재 요구일 | `Date` | `2018-03-03` | 조립 작업 착수 희망 기준일 |
| **`earliest_start_date`** | 最早开工时间 | 착공 가능 최선일 | `Date` | `2018-02-24` | 선행 공정 완료 후 정반에 올릴 수 있는 가장 빠른 날짜 (EST) |
| **`due_date`** | 最晚开工时间 | 착공 마감 기한 | `Date` | `2018-06-30` | 납기 준수를 위해 반드시 착공해야 하는 마감일 (LST) |
| **`lead_time_days`** | 胎位周期 | 정반 공정 소요 기간 | `Integer` | `72` | 정반 점유 일수 (조립 완료까지 걸리는 작업 기간, Days) |
| **`block_output_value`** | 分段产出 | 블록 산출 가치 | `Float` | `368.0` | 블록 조립에 따른 생산 기여도/공수 가치 |
| **`is_combined`** | 是否组合 | 콤비네이션 여부 | `Boolean` | `False` | 2개 이상 블록이 정반에서 결합 조립되는지 여부 |
| **`combined_block_id`** | 组合分段 | 결합 블록 번호 | `String` | `None` | 동시 결합 조립되는 연계 블록 번호 |

---

## 📑 2. 정반 정보 테이블 (`platen_information.csv`)

- **설명:** 선박 블록이 거치되어 용접 및 조립 작업이 수행되는 옥내/옥외 정반(Platen/Bed)의 물리적 한계 및 작업장 사양을 정의합니다.
- **총 레코드 수:** 66개 정반

| 컬럼명 (English) | 원본 한자명 | 한글 설명 | 데이터 타입 | 예시값 | 제약조건 및 비즈니스 의미 |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`seq_id`** | 序号 | 정반 일련번호 | `Integer` | `1` | 정반 고유 식별자 (PK) |
| **`primary_area`** | 一级区域 | 1차 공장 구역 | `String` | `曲面` (곡면) | 조립 공장 대분류 (곡면공장, 평면공장, 옥외 등) |
| **`secondary_area`** | 二级区域 | 2차 세부 구역 | `String` | `48米` | 공장 내 세부 베이(Bay) 위치 |
| **`platen_id`** | 胎位编号 | 정반 고유 코드 | `String` | `BQM4801A` | 시스템 정반 식별 코드 |
| **`platen_name`** | 胎位描述 | 정반 현장 명칭 | `String` | `48南-1` | 현장 작업자가 부르는 정반 이름 |
| **`dimensions`** | 尺寸 | 정반 크기 (L*W) | `String` | `20*20` | 정반 가로/세로 물리 크기 (m 단위) |
| **`crane_capacity_ton`** | 起重能力(T) | 크레인 인양 한계 | `Float` | `240.0` | 정반 상부 크레인이 들 수 있는 최대 블록 무게 (Ton) |
| **`height_limit_m`** | 高度限制(M) | 작업 높이 한계 | `Float` | `9.0` | 공장 건물 층고에 따른 블록 높이 제한 (m) |
| **`subcontractor_team`** | 劳务队 | 전담 작업 협력반 | `String` | `MZ`, `ZH` | 해당 정반에 배속된 용접/취부 전담 작업반 ID |
| **`assigned_block_type`** | 指定分段 | 전용 블록 타입 | `String` | `110` | 특정 정반에 우선 배정되는 권장 블록 유형 |
| **`platen_type`** | 属性 | 정반 가변성 속성 | `String` | `定置` (고정) | 고정식 정반(Fixed) 또는 가변 결합형 정반(Flexible) |
| **`notes`** | 列1 | 비고/특이사항 | `String` | `None` | 기타 특수 작업 제약사항 |

---

## 📑 3. 초기 정반 점유 현황 테이블 (`initial_platen_status.csv`)

- **설명:** 신규 스케줄링 시점 기준, 각 정반에 이미 올라가 작업 중인 기존 블록들의 예상 완료일 현황입니다.
- **총 레코드 수:** 35개 점유 블록

| 컬럼명 (English) | 원본 한자명 | 한글 설명 | 데이터 타입 | 예시값 | 설명 |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`ship_id`** | 船号 | 선박 호선 번호 | `String` | `H1156` | 기작업 중인 선박 코드 |
| **`ship_type`** | 船型 | 선형/선종 | `String` | `17.7` | 선박 제원 및 크기 |
| **`block_id`** | 分段号 | 블록 번호 | `String` | `825` | 현재 정반을 차지하고 있는 블록 번호 |
| **`start_day_serial`** | 最早开工时间 | 작업 착공일 시리얼 | `Integer` | `43031` | Excel Date 시리얼 (착공 날짜) |
| **`platen_name`** | 胎位描述 | 점유 중인 정반명 | `String` | `48北-1` | 점유된 정반 위치 |
| **`expected_end_day_serial`** | 预期完工时间 | 예상 완료일 시리얼 | `Integer` | `43049` | 이 날짜 이후에만 신규 블록 탑재 가능 |

---

## 📑 4. 정반 배치 스케줄링 결과 테이블 (`eddqn_scheduling_results.csv` 등)

- **설명:** 딥러닝(EDDQN/DDQN) 및 휴리스틱(EST, LPT, SPT 등)이 872개 블록을 66개 정반에 최적 배분한 최종 스케줄링 산출물입니다.

| 컬럼명 (English) | 원본 한자명 | 한글 설명 | 데이터 타입 | 설명 및 비즈니스 평가 |
| :--- | :--- | :--- | :---: | :--- |
| **`platen_name`** | 胎位描述 | 배정된 정반명 | `String` | 블록이 최종 배치된 정반 위치 |
| **`platen_id`** | 胎位编号 | 배정된 정반 코드 | `String` | 정반 고유 식별 코드 |
| **`platen_length_m`** | 胎位长 | 정반 길이 (m) | `Float` | 배정 정반 가로 길이 |
| **`platen_width_m`** | 胎位宽 | 정반 폭 (m) | `Float` | 배정 정반 세로 폭 |
| **`subcontractor_team`** | 劳务队 | 담당 작업반 | `String` | 작업을 수행할 협력사 |
| **`ship_id`** | 船号 | 선박 호선 | `String` | 선박 번호 |
| **`block_seq_id`** | 分段序号 | 블록 일련번호 | `Integer` | 블록 Sequence ID |
| **`block_id`** | 分段号 | 블록 번호 | `String` | 블록 ID |
| **`block_length_m`** | 分段长 | 블록 길이 (m) | `Float` | 블록 가로 크기 |
| **`block_width_m`** | 分段宽 | 블록 폭 (m) | `Float` | 블록 세로 크기 |
| **`processing_time_days`** | 分段加工时间 | 실제 작업 일수 | `Integer` | 정반을 점유하는 총 일수 |
| **`block_output_value`** | 分段产值 | 생산 기여 가치 | `Float` | 블록 생산 가치 |
| **`planned_start_day`** | 计划开始时间 | 계획 착공일 | `Integer` | 배정된 작업 시작일 |
| **`planned_end_day`** | 计划结束时间 | 계획 완료일 | `Integer` | 배정된 작업 완료일 |
| **`due_date_day`** | 最晚完工时间 | 납기 마감일 | `Integer` | 준수해야 하는 최종 납기일 |
| **`delay_days`** | 延期天数 | **납기 지연 일수** | `Integer` | **0보다 크면 납기 지연 발생 (최소화 목표)** |
| **`early_days`** | 提前天数 | 납기 조기 완료일수 | `Integer` | 납기일보다 일찍 끝난 일수 |
| **`standard_early_days`** | 正常提前天数 | 표준 조기 완료일수 | `Integer` | 적정 여유 버퍼 일수 |

---

## 📑 5. 딥러닝 강화학습 훈련 로그 테이블 (`eddqn_training_logs.csv` 등)

- **설명:** EDDQN / DDQN 심층 강화학습 모델이 3,000 에피소드 동안 학습하면서 수렴해 가는 손실 함수 및 보상 지표 로그입니다.

| 컬럼명 (English) | 원본 컬럼명 | 한글 설명 | 데이터 타입 | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| **`episode`** | Episode | 훈련 반복 회차 | `Integer` | 1 ~ 3,000 에피소드 |
| **`makespan`** | Makespan | **총 소요 공기 (Days)** | `Integer` | **872개 전체 블록 조립이 끝나는 최종 완공일 (핵심 최소화 목적함수)** |
| **`std_dev_workload`** | std_dev_velue | 정반 부하 표준편차 | `Float` | 66개 정반 간의 작업 쏠림 현상 측정 (부하 균등화 지표) |
| **`avg_reward`** | Average_Reward | 에피소드 평균 보상 | `Float` | 강화학습 신경망의 보상 점수 |
| **`epsilon`** | Epsilon | 탐험율 (Exploration) | `Float` | 1.0 ➔ 0.05 로 감소하는 $\epsilon$-greedy 탐험 확률 |
| **`best_makespan_so_far`**| best_makespan_episode| 역대 최저 Makespan | `Integer` | 학습 중 달성한 최단 공기 기록 |
| **`best_std_dev_so_far`** | best_std_dev_velue_episode| 역대 최저 부하 표준편차| `Float`| 학습 중 달성한 최적 부하 균등도 기록 |

---

## ⚙️ 6. 수리적 제약조건 & 비즈니스 규칙 (Optimization Constraints)

스마트 정반 배치 딥러닝 모델이 반드시 만족해야 하는 4대 절대 제약조건(Hard Constraints)입니다:

1. **공간 제약 (Spatial Dimension Constraint):**  
   $$\text{Block Length} \le \text{Platen Length} \quad \text{and} \quad \text{Block Width} \le \text{Platen Width}$$
2. **중량 제약 (Crane Weight Limit Constraint):**  
   $$\text{Block Weight (Ton)} \le \text{Platen Crane Capacity (Ton)}$$
3. **시공간 비중첩 제약 (Non-overlapping Spatio-Temporal Constraint):**  
   동일한 정반에 배정된 서로 다른 블록 $A, B$에 대해 작업 기간 $[S_A, E_A]$과 $[S_B, E_B]$가 시간적으로 중첩될 경우, 정반 내 2D 팩킹 공간이 물리적으로 겹치지 않아야 함.
4. **선행 착공일 제약 (Precedence & Earliest Start Date Constraint):**  
   $$\text{Planned Start Day} \ge \text{Earliest Start Date (EST)}$$
