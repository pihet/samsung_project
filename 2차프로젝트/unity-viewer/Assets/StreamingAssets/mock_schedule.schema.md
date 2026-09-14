# `mock_schedule.json` 전송 계약 (schema_version 1.0.0)

Unity 뷰어가 로드하는 Mock 스케줄 페이로드의 필드 정의다.
DTO(`Assets/Scripts/Data/SchedulePayloadDto.cs`)와 1:1로 대응하며,
검증 규칙은 `Assets/Scripts/Runtime/SchedulePayloadMapper.cs` 가 강제한다.

## 좌표·시간 규약

- 단위: **meter**. Unity **XZ 평면이 지면**, **Y가 높이(up)**.
- `position` 은 **길이 3 배열 `[x, y, z]`**. 매핑 시 유한값 검증 후 `Vector3` 로 변환.
- **`position` 은 언제나 "최소 코너"(min corner)** 이지 중심이 아니다.
  - 정반: 판 바닥면의 최소 코너(월드). 판은 로컬 `x∈[0,length]`, `z∈[0,width]`,
    `y∈[0,slabThickness]` 를 차지한다.
  - 블록: 배정 정반 원점 기준, 블록 발자국의 최소 코너. `y` 는 **판 상면으로부터의 추가 높이**(보통 0).
  - 프리팹은 중심 피벗 큐브를 가정하므로 스포너가 크기의 절반을 더해 중심을 맞춘다.
- `size` 개념: 각 엔티티의 `length`→X, `width`→Z, `height`→Y.
- 시간은 **오프셋을 명시한 ISO-8601 문자열**(`...Z` 또는 `...+09:00`). `DateTimeOffset` 으로 파싱.
  오프셋이 없으면 검증 오류.

`schema_version` 의 **메이저 버전이 다르면 파서가 즉시 실패**한다. 위 좌표 의미(코너 기준)가
바뀌는 변경은 메이저를 올려야 하며, 그래야 조용히 잘못 그리는 대신 로드가 멈춘다.

## 최상위 필드

| 필드 | 타입 | 의미 |
| --- | --- | --- |
| `schema_version` | string | 계약 버전. 현재 `"1.0.0"`. **필수** — 메이저가 `1` 이 아니면 로드 거부. |
| `generated_at` | string(ISO-8601+offset) | 이 파일 생성 시각. |
| `project_epoch` | string(ISO-8601+offset) | 실제 CSV의 정수 경과일(`planned_start_day` 등)을 절대 시각으로 되돌릴 기준일. 확장 연동용. **선택** — 생략하면 `2018-01-01T00:00:00+09:00`. 단, 값이 있는데 오프셋이 없으면 오류. |
| `algorithm` | string | 스케줄 산출 알고리즘 이름(예: `mock-ortools`). |
| `coordinate_system` | object | `{ units, up_axis, ground_plane }` — 문서화·자기설명용. |
| `kpi` | object | `{ makespan_days, delayed_blocks, total_delay_days }` (int). |
| `platens` | array | 정반 정적 스펙. 초기 Mock 은 5~10개. |
| `blocks` | array | 블록 배치·일정. 초기 Mock 은 30~50개. |

## `platens[]`

| 필드 | 타입 | 규칙 |
| --- | --- | --- |
| `platen_id` | string | 비어 있으면 안 됨, **중복 불가**. 블록의 `platform_id` 가 이 값을 참조. |
| `platen_idx` | int | 격자 폴백 배치에 사용(`YardLayoutConfig`). |
| `platen_name` | string | 표시명. 비면 `platen_id` 로 대체. |
| `primary_area`, `secondary_area` | string | 공장 구역 라벨. |
| `length`, `width`, `height` | number | 모두 **> 0**. height 는 실제 데이터의 `height_limit_m` 에 해당(시각은 판으로 표현). |
| `position` | number[3] \| 없음 | 정반 바닥 **최소 코너**(월드, m). **실제 데이터에는 좌표가 없어 Mock 이 부여**. **필드를 생략하면** `YardLayoutConfig` 격자 폴백이 `platen_idx` 로 위치를 계산한다. `[0,0,0]` 은 "좌표 없음"이 아니라 원점에 놓인 정상 좌표다. |
| `crane_capacity_ton` | number | 크레인 인양 한계. |
| `accepts_block_type` | string | `"FLAT"` \| `"CURVED"` \| `"ANY"`. 생략하면 `ANY`. 그 외 값은 오류. |

## `blocks[]`

| 필드 | 타입 | 규칙 |
| --- | --- | --- |
| `block_id` | string | 비어 있으면 안 됨, **중복 불가**. |
| `seq_id` | int | 원본 `seq_id`. |
| `ship_id` | string | 호선 번호. |
| `platform_id` | string | **존재하는 `platens[].platen_id` 중 하나여야 함**. 아니면 오류. |
| `block_type` | string | **`"FLAT"` \| `"CURVED"` 만 허용**. 생략·빈 값·그 외는 오류(값을 날조하지 않는다). |
| `length`, `width`, `height` | number | 모두 **> 0**. |
| `position` | number[3] | **필수**. 배정 정반 원점 기준, 블록 발자국 **최소 코너**(m). 길이 3·유한값. |
| `status` | string | **`"waiting"` \| `"in_progress"` \| `"completed"` 만 허용**. 단, 화면 색상은 이 값이 아니라 `start_time`/`end_time` + 현재 시각으로 계산. |
| `start_time` | string(ISO-8601+offset) | 정반 점유 시작. |
| `end_time` | string(ISO-8601+offset) | 정반 점유 종료. **`start_time` 보다 뒤여야 함**. |
| `due_time` | string(ISO-8601+offset) | 선택. `end_time` 이 이보다 뒤면 "지연"으로 강조색 적용. |

## 오류 처리

매퍼는 위반을 모두 모아 `SchedulePayloadValidationException` 하나로 던지며,
각 항목은 문맥(`block 'B0007': platform_id 'PPTXXXX' 에 해당하는 정반이 없습니다.`)을 포함한다.
`MockScheduleLoader` 는 이 메시지를 `LoadFailed` 이벤트와 콘솔 에러로 노출한다.

깨진 입력을 직접 시험하려면 이 JSON 사본에서 예를 들어
`platform_id` 를 존재하지 않는 값으로 바꾸거나, `position` 을 2개로 줄이거나,
`end_time` 을 `start_time` 보다 앞으로 두면 로드가 컨텍스트 있는 에러로 중단된다.

## Mock 의 블록 배치 방식

현재 `mock_schedule.json` 은 정반마다 블록 5개를 **3×2 격자 셀**에 배치해
발자국이 서로 겹치지 않게 했다(셀의 85% 크기). 40개 블록이 동시에 보여도
z-fighting 없이 색 변화(회색→파랑→초록)를 한눈에 볼 수 있게 하기 위한 **교육용 단순화**다.

실제 조선소에서는 정반 하나에 **동시에 블록 하나만** 올라간다(시공간 비중첩 제약).
물리적으로 정직한 화면을 원하면 `ViewerSceneBindings.hideOutsideTimeWindow` 를 켜면
작업 기간 밖(착수 전/완료) 블록이 숨겨진다. Mock 의 시간 배치는 이미 정반별 비중첩이라
이 옵션을 켜면 정반당 최대 1개만 보인다.

## 확장(66 정반 / 872 블록) — 구현 완료

**어댑터는 백엔드에 있다.** `GET /api/viewer/schedule/{algorithm}` 이 이 계약을 그대로 내보낸다
(`backend/app/main.py`). 원시 `GET /api/schedule/{algorithm}` 이 아니다 — 그쪽은 CSV 레코드를
그대로 돌려주므로 계약과 다르다.

Unity 쪽은 `MockScheduleLoader` 의 `source` 를 `RestApi` 로 바꾸고 `apiBaseUrl` 과 `algorithm`
을 채우면 끝이다. 파서·매퍼·`ScheduleDataset`·스포너·색상 갱신은 한 줄도 바뀌지 않는다.

서버 어댑터가 처리하는 것:

| 실데이터 문제 | 어댑터 처리 |
| --- | --- |
| 시간이 정수 경과일 | `project_epoch`(2018-03-03+09:00) + N일 → ISO-8601 |
| 스케줄 CSV 에 블록 치수 없음 | `seq_id` 로 `block_information.csv` 조인(872건 전부 매칭) |
| `block_id` 중복(872행에 고유값 97개) | 표시용 id 를 `{ship_id}_{block_id}_{seq_id}` 로 합성 |
| 알고리즘별 납기 컬럼 이름 상이 | `due_date_day`(ortools) / `due_day`(나머지) 자동 선택 |
| 정반 야드 좌표 없음 | `position` 을 **생략**해 `YardLayoutConfig` 격자 폴백에 맡김 |
| 블록 로컬 좌표 없음 | 정반 중앙 배치. 안 들어가면 90도 회전(872개 중 86개) |
| 블록 높이 컬럼 없음 | 표시용 공칭 3.0m. 데이터 출처가 아님을 `adapter_notes` 에 명시 |
| `status` 가 `ALLOCATED` 단일값 | 계약 통과용 `waiting` 고정. 색상은 시각으로 계산 |

**2D 팩킹은 필요 없다.** 실스케줄을 검사한 결과 같은 정반에서 기간이 겹치는 블록 쌍이 **0건**이라
어느 순간에도 정반 위 블록은 최대 1개다. 그래서 중앙 배치로 충분하다. 다만 872개를 동시에 그리면
정반당 13개가 같은 자리에 겹쳐 보이므로, 실데이터에서는
`ViewerSceneBindings.hideOutsideTimeWindow` 를 **켜는 것이 정상 사용법**이다.

검증은 `tests/test_viewer_payload_contract.py` 가 이 문서의 규칙을 미러링해 8개 알고리즘 전부에
대해 자동으로 확인한다.

---

## 실시간 증분 채널 (WebSocket)

`WS /api/viewer/stream`. **최초 스냅샷은 REST 가 주고, 이 채널은 증분만 보낸다.**
전체 스케줄 CSV 는 변하지 않으므로 재전송할 것이 없다. 런타임에 실제로 생기는 변화는
`POST /api/v1/emergency/stream-publish` 로 들어오는 긴급 블록 배정뿐이다.

메시지는 항상 `schema_version` 과 `type` 을 갖는다. 메이저가 다르면 스냅샷과 같이 즉시 거부한다.

| `type` | 시점 | 본문 |
| --- | --- | --- |
| `hello` | 연결 직후 1회 | `project_epoch`, `connected_clients` |
| `block_added` | 긴급 블록이 정반에 배정됨 | `block` (아래), `event_id`, `emergency_level`, `delay_days` |
| `block_rejected` | 배정 실패 또는 계약으로 표현 불가 | `block_id`, `reason` |

`block_added` 의 `block` 은 **`blocks[]` 항목과 완전히 같은 형태**다. 따라서 Unity 도
`SchedulePayloadMapper.MapBlock` 이라는 스냅샷과 같은 검증 경로를 탄다.

`block_id` 는 `EMG_{ship_id}_{block_id}_{event_id}` 로 합성한다. 기존 872개와 겹치면
매퍼가 중복으로 거부하므로 `event_id` 로 고유성을 보장한다.

### 표현할 수 없으면 지어내지 않고 거부한다

아래는 전부 `block_rejected` 로 나간다. 계약을 억지로 통과시키려고 값을 만들어내지 않는다.

- 수용 가능한 정반이 없음 (크기·하중 초과, 전용 정반 타입 불일치)
- `block_type` 이 `FLAT`/`CURVED` 가 아님
- 배정된 정반의 스펙을 찾을 수 없음
- 작업 기간이 0일 이하 (매퍼가 `start < end` 를 요구한다)
- 블록 치수가 0 이하

### 발행 경로는 디스패치를 막지 않는다

긴급 디스패치 엔드포인트는 동기 함수이고 스레드풀에서 돈다. 브로드캐스트는
`loop.call_soon_threadsafe` 로 asyncio 큐에 넣기만 하며, 큐나 루프가 없으면 조용히
실패하고 원래 응답에는 영향을 주지 않는다.
