using System;
using Newtonsoft.Json;

namespace ShipyardTwin.Data
{
    /// <summary>
    /// JSON 전송 계약(DTO)만 담당한다. 검증·좌표 변환·상태 계산 로직은 두지 않는다.
    /// 실행 중 상태는 ShipyardTwin.Runtime 의 일반 C# 런타임 모델이 담당한다.
    ///
    /// 좌표 규약: 단위 meter, Unity XZ 평면이 지면, Y 가 높이(up).
    /// position 은 항상 길이 3 배열 [x, y, z] 이며 매핑 단계에서 Vector3 로 변환·검증한다.
    /// 시간은 오프셋(Z 또는 +09:00 등)을 명시한 ISO-8601 문자열이며 DateTimeOffset 으로 파싱한다.
    /// </summary>
    [Serializable]
    public sealed class SchedulePayloadDto
    {
        [JsonProperty("schema_version")]
        public string SchemaVersion { get; set; }

        /// <summary>Mock JSON 생성 시각(오프셋 포함).</summary>
        [JsonProperty("generated_at")]
        public string GeneratedAt { get; set; }

        /// <summary>
        /// 실제 스케줄 CSV(planned_start_day 등)는 정수 "프로젝트 경과일"이다.
        /// 정수 일수를 절대 시각으로 되돌릴 기준일. REST/CSV 연동 확장 시 사용한다.
        /// </summary>
        [JsonProperty("project_epoch")]
        public string ProjectEpoch { get; set; }

        [JsonProperty("algorithm")]
        public string Algorithm { get; set; }

        [JsonProperty("coordinate_system")]
        public CoordinateSystemDto CoordinateSystem { get; set; }

        [JsonProperty("kpi")]
        public ScheduleKpiDto Kpi { get; set; }

        [JsonProperty("platens")]
        public PlatenDto[] Platens { get; set; }

        [JsonProperty("blocks")]
        public BlockDto[] Blocks { get; set; }
    }

    [Serializable]
    public sealed class CoordinateSystemDto
    {
        [JsonProperty("units")]
        public string Units { get; set; }

        [JsonProperty("up_axis")]
        public string UpAxis { get; set; }

        [JsonProperty("ground_plane")]
        public string GroundPlane { get; set; }
    }

    [Serializable]
    public sealed class ScheduleKpiDto
    {
        [JsonProperty("makespan_days")]
        public int MakespanDays { get; set; }

        [JsonProperty("delayed_blocks")]
        public int DelayedBlocks { get; set; }

        [JsonProperty("total_delay_days")]
        public int TotalDelayDays { get; set; }
    }

    /// <summary>정반(Platen) 정적 스펙. 실제 /api/platens 응답과 필드 의미를 맞춘다.</summary>
    [Serializable]
    public sealed class PlatenDto
    {
        [JsonProperty("platen_id")]
        public string PlatenId { get; set; }

        [JsonProperty("platen_idx")]
        public int PlatenIdx { get; set; }

        [JsonProperty("platen_name")]
        public string PlatenName { get; set; }

        [JsonProperty("primary_area")]
        public string PrimaryArea { get; set; }

        [JsonProperty("secondary_area")]
        public string SecondaryArea { get; set; }

        /// <summary>정반 가로 길이(m). Unity X 축.</summary>
        [JsonProperty("length")]
        public double Length { get; set; }

        /// <summary>정반 세로 폭(m). Unity Z 축.</summary>
        [JsonProperty("width")]
        public double Width { get; set; }

        /// <summary>작업 높이 한계(m). Unity Y 축. 실제 데이터의 height_limit_m 에 해당.</summary>
        [JsonProperty("height")]
        public double Height { get; set; }

        /// <summary>야드 내 정반 원점 [x, y, z] (m). 실제 데이터에는 좌표가 없어 Mock 이 부여한다.</summary>
        [JsonProperty("position")]
        public double[] Position { get; set; }

        [JsonProperty("crane_capacity_ton")]
        public double CraneCapacityTon { get; set; }

        /// <summary>이 정반이 우선 수용하는 블록 형상. "FLAT" | "CURVED" | "ANY".</summary>
        [JsonProperty("accepts_block_type")]
        public string AcceptsBlockType { get; set; }
    }

    /// <summary>블록(Block) 배치·일정 계약.</summary>
    [Serializable]
    public sealed class BlockDto
    {
        [JsonProperty("block_id")]
        public string BlockId { get; set; }

        [JsonProperty("seq_id")]
        public int SeqId { get; set; }

        [JsonProperty("ship_id")]
        public string ShipId { get; set; }

        /// <summary>배정된 정반 참조. PlatenDto.platen_id 중 하나와 일치해야 한다.</summary>
        [JsonProperty("platform_id")]
        public string PlatformId { get; set; }

        /// <summary>블록 형상. "FLAT" | "CURVED".</summary>
        [JsonProperty("block_type")]
        public string BlockType { get; set; }

        /// <summary>블록 가로 길이(m). Unity X 축.</summary>
        [JsonProperty("length")]
        public double Length { get; set; }

        /// <summary>블록 세로 폭(m). Unity Z 축.</summary>
        [JsonProperty("width")]
        public double Width { get; set; }

        /// <summary>블록 높이(m). Unity Y 축.</summary>
        [JsonProperty("height")]
        public double Height { get; set; }

        /// <summary>배정 정반 원점 기준 로컬 오프셋 [x, y, z] (m).</summary>
        [JsonProperty("position")]
        public double[] Position { get; set; }

        /// <summary>계획 생명주기 상태. "waiting" | "in_progress" | "completed".
        /// 렌더링 색상은 이 값이 아니라 start_time/end_time 과 현재 시각으로 계산한다.</summary>
        [JsonProperty("status")]
        public string Status { get; set; }

        /// <summary>정반 점유 시작(오프셋 포함 ISO-8601).</summary>
        [JsonProperty("start_time")]
        public string StartTime { get; set; }

        /// <summary>정반 점유 종료(오프셋 포함 ISO-8601). start_time 보다 뒤여야 한다.</summary>
        [JsonProperty("end_time")]
        public string EndTime { get; set; }

        /// <summary>납기(오프셋 포함 ISO-8601). 선택 필드. end_time 보다 앞이면 지연.</summary>
        [JsonProperty("due_time")]
        public string DueTime { get; set; }
    }
}
