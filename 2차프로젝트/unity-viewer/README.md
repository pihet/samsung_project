# unity-viewer — 조선소 정반 스케줄링 3D 디지털 트윈 (학습용)

조선소 스마트 정반 스케줄링 MLOps 결과를 **Unity 6 LTS + URP** 로 시각화하는
학습형 3D 디지털 트윈 뷰어. 이 폴더는 상위 프로젝트(FastAPI/Kafka/Flink/React)와
독립적이며 기존 서비스·React 대시보드에 전혀 영향을 주지 않는다.

- 초기: **Mock JSON**(정반 8개, 블록 40개)으로 로드→검증→스폰→시간 기준 색상 갱신 파이프라인 검증.
- 확장(구현 완료): 66개 정반 / 872개 블록. 백엔드 `GET /api/viewer/schedule/{algorithm}` 연동.
- 첫 구현은 **DOTween 없이 Coroutine** 만 사용.

> **현재 상태:** Unity 에디터 생성물이 모두 커밋되어 있다.
> `ProjectSettings/`, `Packages/`, `*.meta`, 씬 `Assets/Scenes/Viewer.unity`,
> 프리팹 2개, ScriptableObject 자산 3개가 저장소에 들어 있다.
> **클론 후 에디터로 열면 바로 Play 가 된다.** 단 커밋된 씬은 실데이터(REST) 모드가 기본이라
> 백엔드가 필요하다. 백엔드 없이 보려면 로더의 `Source` 를 `Streaming Assets File` 로 되돌린다.
> 아래 §3·§4 는 이 자산들을 처음 만든 절차 기록이며, 새로 셋업할 때만 따르면 된다.

---

## 1. 지금 들어 있는 것 (커밋된 내용)

```
unity-viewer/
├── README.md                         ← 이 문서 (에디터 설정 절차 포함)
├── .gitignore                        ← Unity 산출물 제외 규칙
└── Assets/
    ├── Scripts/
    │   ├── Data/                     ← JSON 전송 계약(DTO) + 파서 + 예외
    │   │   ├── SchedulePayloadDto.cs
    │   │   ├── ScheduleStreamDto.cs          (WebSocket 증분 메시지 계약)
    │   │   ├── SchedulePayloadParser.cs
    │   │   └── SchedulePayloadException.cs
    │   └── Runtime/                  ← 런타임 모델 + 로더 + 스폰 + 색상
    │       ├── Models/
    │       │   ├── BlockLifecycleStatus.cs   (enum: waiting/in_progress/completed + 파서)
    │       │   ├── TimelinePhase.cs          (enum: Scheduled/Active/Completed + 계산)
    │       │   ├── PlatenModel.cs
    │       │   └── BlockModel.cs
    │       ├── ScheduleDataset.cs            (검증 통과 집합 + id 조회 맵 + 기간)
    │       ├── SchedulePayloadMapper.cs      (DTO→모델 + 전체 계약 검증)
    │       ├── MockScheduleLoader.cs         (스냅샷 로드: 로컬 Mock 또는 REST)
    │       ├── ScheduleStreamClient.cs       (WebSocket 증분 수신, MonoBehaviour)
    │       ├── TimelineClock.cs              (시뮬레이션 현재 시각, MonoBehaviour)
    │       ├── YardBlockSpawner.cs           (정반/블록 스폰, MonoBehaviour)
    │       ├── BlockView.cs                  (스폰된 블록 뷰 핸들)
    │       ├── BlockStatusColorizer.cs       (시각 기준 색상 갱신, Coroutine)
    │       ├── ViewerBootstrap.cs            (로더→클럭 배선점)
    │       └── Config/                       ← ScriptableObject "클래스" 정의(코드)
    │           ├── StatusColorPalette.cs
    │           ├── YardLayoutConfig.cs
    │           └── ViewerSceneBindings.cs
    ├── StreamingAssets/
    │   ├── mock_schedule.json        ← 정반 8 / 블록 40 Mock (schema_version 1.0.0)
    │   └── mock_schedule.schema.md   ← 전송 계약 상세
    ├── Prefabs/                      ← 에디터에서 만든 프리팹 (커밋됨)
    │   ├── Platen.prefab              (판 slab 원본, 단위 큐브)
    │   ├── Block.prefab               (블록 원본, 단위 큐브 + MeshRenderer)
    │   └── README.md                  (만드는 절차)
    ├── ScriptableObjects/            ← 에디터에서 만든 설정 자산 (커밋됨)
    │   ├── StatusColorPalette.asset
    │   ├── YardLayoutConfig.asset
    │   ├── ViewerSceneBindings.asset  (프리팹·팔레트·레이아웃 참조 연결 완료)
    │   └── README.md                  (만드는 절차)
    └── Scenes/
        ├── Viewer.unity               ← 실행할 씬. ViewerRoot 1개에 컴포넌트 5개
        └── SampleScene.unity          (URP 템플릿 기본 씬, 미사용)
```

### 책임 분리 (요청 3)

| 조각 | 파일 | 책임 | 하지 않는 것 |
| --- | --- | --- | --- |
| DTO | `Data/SchedulePayloadDto.cs` | JSON 필드 ↔ C# 속성 매핑만 | 검증, 좌표 변환, 상태 계산 |
| 파서 | `Data/SchedulePayloadParser.cs` | 문자열 → DTO (Newtonsoft) | 계약 검증 |
| 런타임 모델 | `Runtime/Models/*` | 검증된 값만 담는 불변 객체 | I/O, Unity 씬 접근 |
| 매퍼/검증 | `Runtime/SchedulePayloadMapper.cs` | DTO → 모델, 모든 위반 누적 후 1회 throw | 씬 스폰 |
| 로더 | `Runtime/MockScheduleLoader.cs` | StreamingAssets 바이트 → 파서 → 매퍼 → 이벤트 | 렌더링 |
| 스포너 | `Runtime/YardBlockSpawner.cs` | 데이터셋 → GameObject 배치 | 색상, 시간 |
| 색상 갱신 | `Runtime/BlockStatusColorizer.cs` | 클럭 시각 → `TimelinePhase` → 색 (Coroutine 폴링) | 스폰, 로드 |
| 클럭 | `Runtime/TimelineClock.cs` | 시뮬레이션 현재 시각 1개 | 그 외 전부 |
| ScriptableObject | `Runtime/Config/*` | 정적 편집 설정(배치/색/프리팹 참조) | 실행 중 상태 |

---

## 2. 실제 데이터와 설계의 충돌 (요청 1 조사 결과)

상위 프로젝트의 실제 산출물을 확인한 결과, 설계 원칙 중 다음이 **실데이터와 불일치**한다.
Mock 계약은 설계 원칙을 그대로 따르되, 확장 시 아래 갭을 어댑터가 메워야 한다.

| # | 설계 전제 | 실제 데이터 | 해소 방법 |
| --- | --- | --- | --- |
| C1 | 블록에 `start_time`/`end_time`(오프셋 포함 시각) | `data/processed/schedules/ortools_scheduling_results.csv` 는 **정수 경과일** `planned_start_day`, `planned_end_day` (예: 368). 시각·타임존 없음 | Mock 은 계약대로 ISO-8601+offset 사용. 확장 어댑터가 `project_epoch + N일` 로 변환. 계약에 `project_epoch` 필드 포함 |
| C2 | `status` ∈ {`waiting`,`in_progress`,`completed`} | CSV `status` 는 `ALLOCATED` (단일값). 생명주기 구분 없음 | 계약은 3-상태 문자열을 검증하되, **화면 색상은 `start`/`end` + 현재 시각으로 계산**(`TimelinePhase`). 확장 어댑터가 `ALLOCATED` → 시각 기준으로 `status` 를 채움 |
| C3 | 블록·정반에 `position` (길이 3) | 실데이터에 **좌표가 전혀 없음**. 정반 야드 위치도, 블록 2D 팩킹 좌표도 없음 | Mock 이 좌표를 부여. 확장에서는 정반 `position` 을 생략해 `YardLayoutConfig` 격자 폴백에 맡기고, 블록은 정반 중앙에 놓는다. **2D 팩킹은 불필요**(§2-1 참조) |
| C4 | 정반 `length`/`width`/`height` | `platen_information.csv` 는 `dimensions` 를 `"5*10"` 문자열로 보관. `featured_platens.csv` 에만 `platen_length_m`/`platen_width_m`. 높이는 `height_limit_m`(작업 높이 한계) | 계약은 숫자 `length`/`width`/`height` 사용. `height` 는 `height_limit_m` 의미로 문서화. 어댑터가 `"L*W"` 파싱 |
| C5 | 블록이 참조하는 정반 키 이름 `platform_id` | 실데이터/`/api/platens` 는 `platen_id` / `platen_idx` | 계약은 블록에 `platform_id`(요청 명세대로), 정반에 `platen_id` 를 쓰고 **`platform_id` → `platen_id` 참조**로 검증. 어댑터가 매핑 |
| C6 | `block_type` 열거 | `block_information.csv` 는 `FLAT`/`CURVED`, 그러나 메타 정의서엔 `平`/`曲`, 정반 `assigned_block_type` 은 `110.0` 같은 숫자 | 계약은 `FLAT`/`CURVED`(정반은 `ANY` 허용). 알 수 없는 값은 매퍼가 보존만 함 |
| C7 | 알고리즘별 스키마 동일 | `ortools_*` 는 `due_date_day`, `ppo_*` 는 `due_day`+`lead_time_days`+`reward` 로 **열이 다름** | 어댑터를 알고리즘별로 두거나 공통 필드만 사용 |
| C8 | 규모 | 실데이터 정반 66 / 블록 872 (확인함). 초기 Mock 은 8 / 40 | 계약·코드는 규모 비의존. 로더 교체만으로 확장 |

정반↔블록 공간 비중첩(4대 제약 중 #3)은 **좌표가 있어야 검증 가능**하므로 Mock 범위 밖이다.
Mock 은 같은 정반의 블록들을 시간상 비중첩으로만 배치한다.

### 2-1. 확장 구현 중 추가로 확인한 사실

실데이터를 직접 검사해 §2 표의 전제 하나를 뒤집고, 새 결함 3개를 찾았다.

| 발견 | 근거 | 영향 |
| --- | --- | --- |
| **2D 팩킹이 필요 없다** | 8개 알고리즘 전부에서 같은 정반의 기간 겹침 쌍이 **0건**. 어느 순간에도 정반 위 블록은 최대 1개 | 블록을 정반 중앙에 놓으면 충분하다. 팩킹 단계를 짜지 않았다 |
| **블록이 정반에 다 들어간다** | 872개 중 786개가 그대로, 86개는 90도 회전하면 수용. 못 들어가는 블록 0개 | 축 정렬 박스라 `length`/`width` 교환이 곧 회전이다 |
| **`block_id` 가 고유하지 않다** | 872행에 고유 `block_id` 97개, `(ship_id, block_id)` 조합도 174개뿐. 유일 키는 `seq_id` | 매퍼가 중복 id 를 거부하므로 표시용 id 를 합성해야 한다 |
| **블록 치수가 REST 에 없다** | 스케줄 CSV 에는 날짜·정반 배정만 있고 `length_m`/`width_m` 은 `block_information.csv` 에만 존재 | 어댑터가 `seq_id` 로 조인한다(872건 전부 매칭) |
| **블록 높이 컬럼이 아예 없다** | `length_m`, `width_m`, `weight_ton` 뿐 | 표시용 공칭 3.0m 를 쓰고 데이터 출처가 아님을 응답에 명시 |
| **수치 컬럼에 단위 문자가 섞여 있다** | `height_limit_m` 에 `'9M'`, 문자열 컬럼 결측은 `NaN` | 이 때문에 기존 `/api/platens` 가 500 을 내고 있었다. 관용 파서로 수정 |

경과일 0의 기준일도 확정했다. `planned_start_day == 0` 인 블록의 `assembly_start_date` 가
2018-03-03 이므로 이 날이 `project_epoch` 다. 스케줄은 1254일까지 이어진다.

---

## 3. Unity 프로젝트 생성 (완료됨 — 최초 셋업 기록)

> 이 절은 이미 수행되어 `ProjectSettings/`, `Packages/manifest.json` 이 커밋돼 있다.
> 커밋된 버전은 Unity `6000.5.10f1`, URP `17.5.0`, `com.unity.nuget.newtonsoft-json` `3.2.1` 이다.
> 기존 클론에서는 이 절을 건너뛴다.

### 3-1. Unity 6 LTS + URP 프로젝트 생성

1. **Unity Hub** 에서 Unity **6000.x LTS** 에디터를 설치한다(모듈: 사용 플랫폼 Build Support).
2. Hub → **New project** → 템플릿 **Universal 3D** (URP) 선택.
3. **Project name** 을 `unity-viewer`, **Location** 을 이 저장소의 프로젝트 루트
   (`.../2차프로젝트/`) 로 지정한다. 결과 경로가 정확히 `.../2차프로젝트/unity-viewer/` 가 되어야 한다.
   - Hub 가 "폴더가 비어 있지 않다"며 거부하면: 임의 위치에 `unity-viewer` 로 생성한 뒤,
     Unity 를 닫고 **생성된 `Assets/` 안에 이 저장소의 `unity-viewer/Assets/` 내용을 병합**하고
     (`Scripts/`, `StreamingAssets/`, `Prefabs/`, `ScriptableObjects/` 를 덮어쓰기 없이 추가),
     프로젝트 폴더 전체를 `.../2차프로젝트/unity-viewer/` 로 옮긴다.
4. Unity 가 프로젝트를 열면서 `ProjectSettings/`, `Packages/manifest.json`,
   `Library/`, 그리고 `Assets/**/*.meta` 를 자동 생성한다. `.gitignore` 가 `Library/` 등을 제외한다.
5. 프로젝트가 열린 뒤 `.gitignore` 에서 `*.meta` 줄을 **삭제**하고 `Assets/` 하위 `.meta` 를 커밋 대상에 포함한다
   (Unity 프로젝트에서 meta 는 정상 커밋 대상).

### 3-2. Newtonsoft.Json 패키지 설치

1. **Window → Package Manager**.
2. 좌상단 **+** → **Install package by name...**.
3. 이름: `com.unity.nuget.newtonsoft-json` → **Install**.
   (URP 템플릿에 이미 전이 의존성으로 들어와 있으면 버전만 확인.)
4. 콘솔에 `Newtonsoft.Json` 관련 컴파일 에러가 없어야 한다. `Assets/Scripts/Data/*` 가 이 패키지를 참조한다.

### 3-3. URP 확인

- **Edit → Project Settings → Graphics** 에 URP Asset(Render Pipeline Asset)이 지정돼 있는지 확인.
- Universal 3D 템플릿이면 기본 설정돼 있다. 블록 색상은 URP `_BaseColor` 로 설정된다.

---

## 4. 에디터 자산 생성 및 연결 (완료됨 — 최초 셋업 기록)

> 프리팹 2개, ScriptableObject 자산 3개, `Assets/Scenes/Viewer.unity` 가 모두 커밋돼 있다.
> 머티리얼 `Platen_Mat`/`Block_Mat` 은 만들지 않았고 URP 기본 Lit 머티리얼을 쓴다(§4-2 는 선택).
>
> **커밋된 씬은 실데이터(REST) 모드가 기본이다.** 그대로 Play 하려면 백엔드가 떠 있어야 한다(§5).
> 백엔드 없이 보려면 `MockScheduleLoader.Source` 를 `Streaming Assets File` 로 되돌린다.
> 그러면 정반 8개 / 블록 40개 Mock 으로 즉시 동작한다.

### 4-1. 프리팹 2개 — `Assets/Prefabs/`

`Assets/Prefabs/README.md` 참조. 요약:

| 프리팹 | 만드는 법 | 요건 |
| --- | --- | --- |
| `Platen.prefab` | `3D Object > Cube`, 이름 `Platen`, Scale (1,1,1) | 판용 머티리얼 1개. 색 갱신 대상 아님 |
| `Block.prefab` | `3D Object > Cube`, 이름 `Block`, Scale (1,1,1) | **Renderer 1개 이상 필수**. URP Lit/Unlit 머티리얼 1개 |

두 큐브를 각각 `Assets/Prefabs/` 로 드래그해 프리팹화한 뒤 하이어라키에서 삭제한다.
피벗은 기본값(중심) 그대로 둔다 — 스포너가 코너 기준 좌표를 중심 피벗에 맞게 보정한다.

스폰 시 만들어지는 계층은 다음과 같다. **정반 루트는 스케일 1인 빈 오브젝트**이고
`Platen.prefab` 은 그 자식 `Slab` 이 된다. 루트를 스케일하지 않아야 자식 블록의
위치·크기가 정반 크기만큼 곱해지지 않는다.

```
Platen_PPT1000A_Bay10-N-1   (빈 GameObject, scale 1, 위치 = 정반 최소 코너)
├─ Slab                      (Platen.prefab, scale = 28 × 0.5 × 18)
├─ Block_B0001_H1080         (Block.prefab,  scale = 7.4 × 3 × 6.8)
└─ ...
```

### 4-2. 머티리얼

- `Assets/` 에 폴더 `Materials/` 생성(선택).
- `Create → Material` × 2: `Platen_Mat`(어두운 회색), `Block_Mat`.
  Shader 는 `Universal Render Pipeline/Lit` 권장. `Block_Mat` 을 `Block.prefab` 의 MeshRenderer 에 지정.
- 색은 런타임에 `MaterialPropertyBlock` 으로 덮이므로 초기색은 아무거나 무방.

### 4-3. ScriptableObject 자산 3개 — `Assets/ScriptableObjects/`

`Assets/ScriptableObjects/README.md` 참조. `Create > Shipyard Twin > ...` 메뉴로 생성:

1. `StatusColorPalette.asset`
2. `YardLayoutConfig.asset`
3. `ViewerSceneBindings.asset` — 슬롯 연결:
   - `platenPrefab` ← `Assets/Prefabs/Platen.prefab`
   - `blockPrefab` ← `Assets/Prefabs/Block.prefab`
   - `colorPalette` ← `StatusColorPalette.asset`
   - `yardLayout` ← `YardLayoutConfig.asset`

### 4-4. 씬 구성

1. `Assets/Scenes/` 에 새 씬 `Viewer.unity` 생성(URP 템플릿 SampleScene 복제해도 됨).
2. 빈 GameObject **`ViewerRoot`** 생성. 아래 컴포넌트를 **모두 이 하나에** 추가한다:
   - `MockScheduleLoader`
   - `TimelineClock`
   - `YardBlockSpawner`
   - `BlockStatusColorizer`
   - `ViewerBootstrap`
3. 인스펙터 연결:

   | 컴포넌트 | 필드 | 값 |
   | --- | --- | --- |
   | `MockScheduleLoader` | `fileName` | `mock_schedule.json` (기본값) |
   | | `loadOnStart` | ✔ |
   | `YardBlockSpawner` | `loader` | `ViewerRoot` (자기 자신) |
   | | `bindings` | `ViewerSceneBindings.asset` |
   | | `container` | 비움(자동으로 자기 Transform) 또는 별도 빈 오브젝트 |
   | `BlockStatusColorizer` | `spawner` | `ViewerRoot` |
   | | `clock` | `ViewerRoot` |
   | | `bindings` | `ViewerSceneBindings.asset` |
   | | `refreshIntervalSeconds` | `0.25` |
   | `TimelineClock` | `hoursPerRealSecond` | `24` (1초 = 1일) |
   | `ViewerBootstrap` | `loader` | `ViewerRoot` |
   | | `clock` | `ViewerRoot` |

4. 카메라: 야드 격자(약 X 0~135m, Z 0~35m)를 내려다보도록 `Main Camera` 를
   position `(88, 90, -20)`, rotation `(60, 0, 0)` 으로 둔다(커밋된 `Viewer.unity` 의 값). Directional Light 는 템플릿 기본 유지.

### 4-5. 실행

- **Play**. 콘솔에 `[MockScheduleLoader] 로드 완료: 정반 8개, 블록 40개 ...` 가 뜨면 성공.
- 정반 8개 판이 4×2 격자(X 0~135m, Z 0~35m)로 놓이고, 각 판 위에 블록 5개가
  판 안쪽 **3×2 셀 격자**로 서로 겹치지 않게 올라간다.
- 시간이 흐르며(1초=1일) 블록 색이 회색(착수 전)→파랑(작업 중)→초록(완료) 으로 바뀌고,
  납기 초과 블록은 빨강 기가 섞인다.
- 실제로는 정반 하나에 동시에 블록 하나만 올라간다. 물리적으로 정직한 화면을 보려면
  `ViewerSceneBindings.hideOutsideTimeWindow` 를 켠다(작업 기간 밖 블록이 숨겨짐).
- 깨진 입력 시험: `Assets/StreamingAssets/mock_schedule.json` 사본에서
  어떤 블록의 `platform_id` 를 없는 값으로 바꾸면
  `[MockScheduleLoader] 스케줄 페이로드 검증 실패: 1건 - block 'Bxxxx': platform_id '...' 에 해당하는 정반이 없습니다.` 로 중단된다.

---

## 5. 확장 (66 정반 / 872 블록) — 구현 완료

### 5-1. 어댑터는 백엔드에 있다

`backend/app/main.py` 의 `GET /api/viewer/schedule/{algorithm}` 이 §1 의 전송 계약을
그대로 내보낸다. 원시 `GET /api/schedule/{algorithm}` 과 혼동하면 안 된다. 그쪽은 CSV
레코드를 가공 없이 돌려주므로 계약과 형태가 다르다.

서버에서 끝내는 일은 경과일을 ISO 시각으로 바꾸는 것, `seq_id` 로 블록 치수를 조인하는 것,
알고리즘별 납기 컬럼 차이를 흡수하는 것, 블록을 정반 중앙에 놓는 것이다. 상세 대응표는
`Assets/StreamingAssets/mock_schedule.schema.md` 의 확장 절에 있다.

서버에 둔 이유는 블록 치수가 어느 REST 응답에도 없어서 어느 쪽이든 백엔드를 건드려야 했고,
조인·날짜 연산·컬럼 분기를 C# 으로 옮기면 에디터 없이는 검증할 수 없기 때문이다.

### 5-2. Unity 쪽에서 할 일

`MockScheduleLoader` 인스펙터만 바꾸면 된다. 코드 수정은 없다.

| 필드 | 커밋된 값 |
| --- | --- |
| `Source` | `Rest Api` |
| `Api Base Url` | `http://localhost:8000` |
| `Algorithm` | `ortools` (다른 값: `ppo`, `dqn`, `est`, `spt`, `lpt`, `rtb`, `rub`) |
| `Request Timeout Seconds` | `30` (응답이 약 300KB) |

`Source` 를 `Streaming Assets File` 로 되돌리면 백엔드 없이 Mock 으로 돌아간다.

백엔드 기동은 Kafka 주소를 바꿔줘야 한다. 기본값이 쿠버네티스 안의 브로커라
로컬에서는 연결을 기다리다 기동이 끝나지 않는다.

```
cd 2차프로젝트/backend
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:1 python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

에셋 로딩에 약 30초가 걸린 뒤 포트가 열린다.
`http://localhost:8000/api/viewer/schedule/ortools` 가 JSON 을 돌려주면 준비된 것이다.

### 5-3. 실데이터용 씬 설정

커밋된 씬은 아래 값으로 맞춰져 있다. Mock(8정반 야드)과 실데이터(66정반 야드)는
규모가 달라 카메라가 같을 수 없다.

| 대상 | 필드 | 값 | 이유 |
| --- | --- | --- | --- |
| `ViewerSceneBindings` | `hideOutsideTimeWindow` | 켬 | 872개를 다 그리면 정반당 13개가 같은 자리에 겹친다. 실제로는 정반당 동시 1개(§2-1) |
| `Main Camera` | position `(175, 320, -90)` | 야드가 X 0~351m, Z 0~302m | Mock 야드(135m)의 2.6배라 기존 위치로는 화면 밖으로 넘친다 |
| `TimelineClock` | `hoursPerRealSecond` 240 | 1초 = 10일 | 스케줄이 1254일이라 24(1초=1일)면 전체를 보는 데 21분 걸린다 |

### 5-4. 화면 읽는 법

색은 `start_time`/`end_time` 과 현재 시각으로 계산한다. `hideOutsideTimeWindow` 를 켜면
작업 중인 블록만 남으므로 실질적으로 두 색만 보인다.

- **파랑** — 작업 중이고 납기 안에 든다.
- **탁한 분홍** — 작업 중이지만 납기를 넘겼다. 파랑에 `delayedTint` 를 60% 섞은 색이다.

동시 작업 블록 수는 구간별로 크게 다르다(ortools 기준).

| 경과일 | 작업 중 | 그중 납기 초과 |
| --- | --- | --- |
| 0 | 2 | 0 |
| 60 | 48 | 0 |
| 200 | 62 | 27 |
| 400 | 9 | 4 |
| 1250 | 1 | 1 |

초반과 후반은 한산하다. 60~200일 구간이 가장 볼 만하고, 후반으로 갈수록 작업 중인
블록이 거의 다 지연 상태라 파랑을 보기 어렵다.

### 5-5. 실시간 증분 채널 (WebSocket) — 구현 완료

`WS /api/viewer/stream` 이 런타임 변화를 push 한다. **스냅샷 재전송은 하지 않는다.**
스케줄 CSV 는 변하지 않으므로 다시 보낼 것이 없고, 실제로 생기는 변화는
`POST /api/v1/emergency/stream-publish` 로 들어오는 긴급 블록 배정뿐이다.

흐름은 이렇다. 긴급 블록 요청이 들어오면 기존 디스패처가 66개 정반의 물리 제약을 검사해
정반을 배정하고, 그 결과를 계약의 블록 1개로 바꿔 접속된 모든 뷰어에 보낸다. 뷰어는
스냅샷과 **같은 검증 경로**(`SchedulePayloadMapper.MapBlock`)를 태운 뒤 해당 정반 위에
블록을 얹는다. 색상 갱신은 기존 폴링이 그대로 집어간다.

메시지 형식은 `Assets/StreamingAssets/mock_schedule.schema.md` 의 실시간 증분 채널 절에 있다.

#### 씬 배선

`ViewerRoot` 에 `ScheduleStreamClient` 컴포넌트를 추가하고 슬롯 2개를 채운다.

| 필드 | 값 |
| --- | --- |
| `Loader` | `ViewerRoot` (백엔드 주소와 데이터셋을 여기서 얻는다) |
| `Spawner` | `ViewerRoot` |
| `Override Base Url` | 비움 (로더의 `Api Base Url` 을 `ws://` 로 바꿔 쓴다) |
| `Connect On Load` | 체크 (스냅샷 로드가 끝나면 자동 접속) |

#### 시험하는 법

뷰어를 Play 한 상태에서 긴급 블록을 하나 던진다.

```
curl -X POST http://localhost:8000/api/v1/emergency/stream-publish \
  -H "Content-Type: application/json" \
  -d '{"block_id":"E001","ship_id":"H9999","length_m":15.0,"width_m":14.0,
       "weight_ton":120.0,"lead_time_days":20,"due_date_day":300,"block_type":"FLAT"}'
```

Unity 콘솔에 `[ScheduleStreamClient] 긴급 블록 추가: ... -> 정반 ...` 이 뜨고, 해당 정반에
블록이 생긴다. `hideOutsideTimeWindow` 를 켜 뒀다면 타임라인이 그 블록의 작업 기간에
도달할 때 나타난다.

#### 제약

- `ClientWebSocket` 을 쓰므로 **에디터와 스탠드얼론에서만 동작한다.** WebGL 빌드에서는
  브라우저 소켓 API 로 교체해야 한다.
- 추가만 있고 **삭제·수정은 없다.** 배정 취소나 일정 변경은 서버에도 그런 개념이 없다.
- 연결이 끊기면 5초 후 재접속하지만, **끊겨 있는 동안 발행된 이벤트는 유실된다.**
  서버가 이벤트를 버퍼링하지 않는다.

---

## 6. 검증 현황

`README` §"완료 보고" 및 저장소 루트 `AGENTS.md` §4 형식.

- **실행한 정적 검증**
  - `python3 -m json.tool mock_schedule.json` → 유효.
  - Mock 계약 자기검증 스크립트(매퍼 규칙 미러: 중복/누락 ID, 없는 `platform_id`,
    `position` 길이·유한값, `status` 열거, 시각 오프셋·파싱·`start<end`, 규모 5~10 / 30~50,
    **판 경계 안 배치 + 같은 정반 블록 쌍별 비중첩**)
    → `OK: 8 platens, 40 blocks, all contract checks pass`.
    겹침 검증기는 좌표를 일부러 충돌시킨 역테스트로 실제 검출됨을 확인.
  - C# 18개 파일 괄호/중괄호 균형 및 외부 의존성 스캔 → 균형 OK, 외부 의존성은 `Newtonsoft.Json` 만.
- **1차 코드리뷰 반영 (블로킹 3건 포함 10건 수정 완료)**
  - 정반 루트를 스케일해 자식 블록 좌표·크기가 곱해지던 버그 → 스케일 1인 빈 루트 + 자식 `Slab` 구조로 교체.
  - 중심 피벗 vs 코너 기준 좌표 불일치 → `position` 은 항상 최소 코너로 확정하고 스포너가 절반 보정.
  - Mock 블록 5개가 공간적으로 겹치던 문제 → 3×2 셀 격자 배치 + `hideOutsideTimeWindow` 옵션.
  - `project_epoch` 선택 필드화(죽은 `??` 제거), `position` 생략을 좌표 없음 센티널로 사용,
    `Loaded` 재생, `block_type` 날조 제거, Windows `file://` URI, `Clear()` 범위 축소,
    `schema_version` 메이저 검증.
- **에디터 실행 검증 완료** (2026-09-11, Unity `6000.5.10f1` / URP `17.5.0` / Windows DX12)
  - 스크립트 18개 **컴파일 통과**. 컴파일 에러 0건.
  - `Assets/Scenes/Viewer.unity` Play 결과 콘솔:
    `[MockScheduleLoader] 로드 완료: 정반 8개, 블록 40개, 알고리즘 'mock-ortools',
    기간 2018-01-21T00:00:00+09:00 ~ 2018-10-26T00:00:00+09:00` 및
    `[YardBlockSpawner] 정반 8개, 블록 40개 스폰 완료.`
  - **스폰 계층 구조 확인**: 정반 루트 8개가 4×2 격자로 생성되고, 각 루트 아래
    `Slab` 과 블록 5개가 판 경계 안 3×2 자리에 겹치지 않게 배치됨.
    1차 코드리뷰의 스케일 오염 블로킹 버그가 실행에서 재발하지 않음을 확인.
  - **URP `_BaseColor` 색 갱신 확인**: 시간 경과에 따라 회색 → 파랑 → 초록 전환,
    납기 초과 블록에 `delayedTint` 혼합이 화면에 반영됨.
  - **`UnityWebRequest` Windows 경로 처리 확인**: `file://` URI 로 StreamingAssets 로드 성공.
  - **인스펙터 직렬화 확인**: `ViewerSceneBindings` 슬롯 4개와
    씬 내 컴포넌트 상호 참조 5곳이 저장 후에도 유지됨.
  - 콘솔에 뜨는 `NoSubscription` 에러는 `com.unity.ai.assistant` 패키지 문제이며 이 뷰어와 무관하다.
- **실데이터 확장 검증** (`tests/test_viewer_payload_contract.py`, pytest 50건 통과)
  - 8개 알고리즘 × 계약 검증 / 판 경계 안 배치 / 정반당 시간 비중첩 / 규모 확인.
    검증 규칙은 C# 매퍼(`SchedulePayloadMapper.cs`)가 강제하는 항목을 파이썬으로 미러링한 것이다.
  - 모든 알고리즘에서 정반 66개, 블록 872개, 건너뛴 블록 0건.
  - HTTP 직렬화까지 확인: 어댑터 응답 200, 약 300KB. 없는 알고리즘은 404.
  - 부수 수정: 실데이터의 `'9M'` 과 `NaN` 때문에 500 을 내던 기존 `/api/platens` 를 복구했다.
  - **WebSocket 스트림 검증**: 실제 uvicorn 서버에 붙어 세 경우를 확인했다.
    수용 가능한 블록은 `block_added` 로 계약 형태의 블록이 오고, 초대형 블록은
    `block_rejected`, 계약에 없는 `block_type` 도 `block_rejected` 로 나온다.
    스트림 블록이 계약을 만족하고 기존 872개와 id 가 겹치지 않는 것도 테스트로 고정했다.
  - **에디터 실행 검증 완료** (2026-09-11, Unity `6000.5.10f1` / Windows):
    `Source = Rest Api` 로 로컬 백엔드에 붙여 콘솔에
    `[MockScheduleLoader] 로드 완료: 정반 66개, 블록 872개, 알고리즘 'ortools',
    기간 2018-03-03T00:00:00+09:00 ~ 2021-08-08T00:00:00+09:00` 및
    `[YardBlockSpawner] 정반 66개, 블록 872개 스폰 완료.` 확인.
    정반 66개가 8×9 격자로 배치되고, `hideOutsideTimeWindow` 를 켠 상태에서
    그 시점 작업 중인 블록만 파랑/분홍으로 표시되는 것을 눈으로 확인했다.
    938개 오브젝트 스폰에 체감 지연 없음.
- **남은 위험**
  - **좌표는 여전히 만들어낸 값**: 정반 배치는 `YardLayoutConfig` 격자 폴백이고
    블록은 정반 중앙이다. 실제 야드 배치도, 실제 블록 위치도 아니다.
  - **블록 높이 3.0m 는 공칭값**: 실데이터에 높이 컬럼이 없다. 데이터에서 온 값이 아니다.
  - **정반당 동시 1블록 제약은 화면에 강제되지 않음**: 기본값은 모두 보여주는
    교육용 표시다. 실데이터에서는 `hideOutsideTimeWindow` 를 켜야 정직한 화면이 된다.
  - **스트림은 추가 전용**: 블록 삭제·수정 경로가 없다. 서버에도 그 개념이 없다.
  - **끊긴 동안의 이벤트는 유실된다**: 서버가 버퍼링하지 않으므로 재접속해도 복구되지 않는다.
    정확성이 필요하면 재접속 시 REST 스냅샷을 다시 받아야 한다.
  - **WebGL 미지원**: `ClientWebSocket` 은 에디터·스탠드얼론 전용이다.
  - **스트림의 Unity 에디터 검증 미완**: 서버 쪽 push 와 계약은 확인했지만,
    Unity 가 실제로 받아서 블록을 얹는 것은 아직 눈으로 보지 않았다.
  - **머티리얼 미생성**: 판과 블록이 URP 기본 Lit 머티리얼을 공유한다. 색 구분은 런타임
    `MaterialPropertyBlock` 에만 의존하므로, 판 자체 색을 바꾸려면 `Platen_Mat` 을 따로 만들어야 한다.
  - **자동화 테스트 없음**: 검증은 정적 스크립트와 위 육안 확인뿐이다. Unity Test Framework
    기반 EditMode 테스트는 아직 없다.
