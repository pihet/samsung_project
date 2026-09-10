# `mock_schedule.json` 전송 계약 (schema_version 1.0.0)

Unity 뷰어가 로드하는 Mock 스케줄 페이로드의 필드 정의다.
DTO(`Assets/Scripts/Data/SchedulePayloadDto.cs`)와 1:1로 대응하며,
검증 규칙은 `Assets/Scripts/Runtime/SchedulePayloadMapper.cs` 가 강제한다.

## 좌표·시간 규약

- 단위: **meter**. Unity **XZ 평면이 지면**, **Y가 높이(up)**.
- `position` 은 항상 **길이 3 배열 `[x, y, z]`**. 매핑 시 유한값 검증 후 `Vector3` 로 변환.
- `size` 개념: 각 엔티티의 `length`→X, `width`→Z, `height`→Y.
- 시간은 **오프셋을 명시한 ISO-8601 문자열**(`...Z` 또는 `...+09:00`). `DateTimeOffset` 으로 파싱.
  오프셋이 없으면 검증 오류.

## 최상위 필드

| 필드 | 타입 | 의미 |
| --- | --- | --- |
| `schema_version` | string | 계약 버전. 현재 `"1.0.0"`. |
| `generated_at` | string(ISO-8601+offset) | 이 파일 생성 시각. |
| `project_epoch` | string(ISO-8601+offset) | 실제 CSV의 정수 경과일(`planned_start_day` 등)을 절대 시각으로 되돌릴 기준일. 확장 연동용. |
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
| `position` | number[3] | 야드 내 정반 원점(월드, m). **실제 데이터에는 좌표가 없어 Mock 이 부여**. |
| `crane_capacity_ton` | number | 크레인 인양 한계. |
| `accepts_block_type` | string | `"FLAT"` \| `"CURVED"` \| `"ANY"`. |

## `blocks[]`

| 필드 | 타입 | 규칙 |
| --- | --- | --- |
| `block_id` | string | 비어 있으면 안 됨, **중복 불가**. |
| `seq_id` | int | 원본 `seq_id`. |
| `ship_id` | string | 호선 번호. |
| `platform_id` | string | **존재하는 `platens[].platen_id` 중 하나여야 함**. 아니면 오류. |
| `block_type` | string | `"FLAT"` \| `"CURVED"`. |
| `length`, `width`, `height` | number | 모두 **> 0**. |
| `position` | number[3] | 배정 정반 원점 기준 **로컬 오프셋**(m). 길이 3·유한값. |
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

## 확장(66 정반 / 872 블록, REST·WebSocket)

- REST: `GET /api/schedule/{algorithm}` 응답(`schedule[]`)과 `GET /api/platens` 응답을
  이 계약 형태로 어댑팅. 실제 응답은 시간이 **정수 경과일**이므로 `project_epoch + N일` 로 변환하고,
  좌표가 없으므로 `YardLayoutConfig` 격자 폴백(정반) + 팩킹 결과(블록 로컬 오프셋)를 채워야 한다.
- 교체 지점은 `MockScheduleLoader.LoadRoutine` 의 바이트 획득부 한 곳. 파서·매퍼·스포너는 재사용.
