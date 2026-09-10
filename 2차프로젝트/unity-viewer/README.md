# unity-viewer — 조선소 정반 스케줄링 3D 디지털 트윈 (학습용)

조선소 스마트 정반 스케줄링 MLOps 결과를 **Unity 6 LTS + URP** 로 시각화하는
학습형 3D 디지털 트윈 뷰어. 이 폴더는 상위 프로젝트(FastAPI/Kafka/Flink/React)와
독립적이며 기존 서비스·React 대시보드에 전혀 영향을 주지 않는다.

- 초기: **Mock JSON**(정반 8개, 블록 40개)으로 로드→검증→스폰→시간 기준 색상 갱신 파이프라인 검증.
- 확장: 66개 정반 / 872개 블록, REST(`/api/schedule/{algorithm}`, `/api/platens`) 또는 WebSocket 연동.
- 첫 구현은 **DOTween 없이 Coroutine** 만 사용.

> **중요:** 이 저장소에는 Unity 에디터가 생성해야 하는 `ProjectSettings/`, `Packages/`,
> `*.meta`, 씬(`.unity`), 프리팹(`.prefab`), `.asset` 을 **의도적으로 넣지 않았다**.
> 아래 절차대로 에디터에서 직접 생성한다. 버전 문자열을 임의로 꾸며낸 파일은 없다.

---

## 1. 지금 들어 있는 것 (커밋된 초안)

```
unity-viewer/
├── README.md                         ← 이 문서 (에디터 설정 절차 포함)
├── .gitignore                        ← Unity 산출물 제외 규칙
└── Assets/
    ├── Scripts/
    │   ├── Data/                     ← JSON 전송 계약(DTO) + 파서 + 예외
    │   │   ├── SchedulePayloadDto.cs
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
    │       ├── MockScheduleLoader.cs         (StreamingAssets 로드, MonoBehaviour)
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
    ├── Prefabs/README.md             ← 에디터에서 만들 프리팹 안내 (자산 자리)
    └── ScriptableObjects/README.md   ← 에디터에서 만들 .asset 안내 (자산 자리)
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
| C3 | 블록·정반에 `position` (길이 3) | 실데이터에 **좌표가 전혀 없음**. 정반 야드 위치도, 블록 2D 팩킹 좌표도 없음 | Mock 이 좌표를 부여. 확장 시 정반은 `YardLayoutConfig` 격자 폴백, 블록 로컬 오프셋은 별도 팩킹 단계 필요(현재 범위 밖) |
| C4 | 정반 `length`/`width`/`height` | `platen_information.csv` 는 `dimensions` 를 `"5*10"` 문자열로 보관. `featured_platens.csv` 에만 `platen_length_m`/`platen_width_m`. 높이는 `height_limit_m`(작업 높이 한계) | 계약은 숫자 `length`/`width`/`height` 사용. `height` 는 `height_limit_m` 의미로 문서화. 어댑터가 `"L*W"` 파싱 |
| C5 | 블록이 참조하는 정반 키 이름 `platform_id` | 실데이터/`/api/platens` 는 `platen_id` / `platen_idx` | 계약은 블록에 `platform_id`(요청 명세대로), 정반에 `platen_id` 를 쓰고 **`platform_id` → `platen_id` 참조**로 검증. 어댑터가 매핑 |
| C6 | `block_type` 열거 | `block_information.csv` 는 `FLAT`/`CURVED`, 그러나 메타 정의서엔 `平`/`曲`, 정반 `assigned_block_type` 은 `110.0` 같은 숫자 | 계약은 `FLAT`/`CURVED`(정반은 `ANY` 허용). 알 수 없는 값은 매퍼가 보존만 함 |
| C7 | 알고리즘별 스키마 동일 | `ortools_*` 는 `due_date_day`, `ppo_*` 는 `due_day`+`lead_time_days`+`reward` 로 **열이 다름** | 어댑터를 알고리즘별로 두거나 공통 필드만 사용 |
| C8 | 규모 | 실데이터 정반 66 / 블록 872 (확인함). 초기 Mock 은 8 / 40 | 계약·코드는 규모 비의존. 로더 교체만으로 확장 |

정반↔블록 공간 비중첩(4대 제약 중 #3)은 **좌표가 있어야 검증 가능**하므로 현재 범위 밖이다.
Mock 은 같은 정반의 블록들을 시간상 비중첩으로만 배치한다.

---

## 3. Unity 프로젝트 생성 (에디터에서 직접)

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

## 4. 에디터 자산 생성 및 연결

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
   position `(60, 90, -20)`, rotation `(60, 0, 0)` 정도로 둔다. Directional Light 는 템플릿 기본 유지.

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

## 5. 확장 (66 정반 / 872 블록, REST·WebSocket)

- **교체 지점은 한 곳**: `MockScheduleLoader.LoadRoutine()` 의 바이트 획득부.
  REST 라면 `UnityWebRequest.Get("http://localhost:8000/api/schedule/ortools")` 로 바꾸고,
  응답(JSON 열: 정수 경과일, `platen_id`, 좌표 없음)을 §2 표대로 이 계약 형태로 어댑팅한다.
- 파서·매퍼·`ScheduleDataset`·스포너·색상 갱신은 규모/소스에 비의존이라 그대로 재사용.
- 좌표 없는 정반은 JSON 에서 `position` **필드를 생략**하면 `YardLayoutConfig` 격자 폴백이
  `platen_idx` 로 자동 배치한다(`[0,0,0]` 은 폴백이 아니라 원점 좌표로 취급).
  블록 로컬 오프셋(2D 팩킹)은 별도 작업 필요.
- WebSocket 은 증분 업데이트 채널을 추가하고 `ScheduleDataset` 을 부분 갱신 + 스포너에 diff 적용하는
  후속 설계가 필요(현재 범위 밖).

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
- **실행하지 못한 검증과 위험**
  - **Unity 컴파일 / 플레이 모드 여전히 미검증**: 이 환경에 Unity 에디터가 없어
    `UnityEngine`·`UnityEngine.Networking` 참조 코드는 컴파일할 수 없다.
    위 수정도 **정적 검토만 거쳤고 실행으로 확인되지 않았다.**
    특히 스폰 계층 구조, URP `_BaseColor` 반영, `UnityWebRequest` 경로 처리, 인스펙터 직렬화는
    에디터 최초 실행에서 반드시 눈으로 확인해야 한다.
  - **`.meta` GUID 미생성**: 스크립트 간 참조는 네임스페이스 기반이라 문제없지만,
    프리팹/SO/씬은 에디터에서 만들어야 하므로 인스펙터 연결은 사용자가 수행한다.
  - **좌표·팩킹 부재**: Mock 좌표는 시각화용으로 이 저장소가 만들어낸 값이다.
    실데이터엔 좌표가 없어(§2 C3) 확장 시 2D 팩킹 단계가 없으면 블록이 겹쳐 보인다.
  - **정반당 동시 1블록 제약은 화면에 강제되지 않음**: 기본값은 40개를 모두 보여주는
    교육용 표시다. 물리적 정직함이 필요하면 `hideOutsideTimeWindow` 를 켠다.
