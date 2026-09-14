using System;
using Newtonsoft.Json;

namespace ShipyardTwin.Data
{
    /// <summary>
    /// WebSocket 실시간 채널(`/api/viewer/stream`)이 밀어주는 메시지 1건의 전송 계약.
    ///
    /// 최초 스냅샷은 REST 가 주고, 이 채널은 **증분만** 전달한다.
    /// 전체 스케줄 CSV 는 변하지 않으므로 재전송할 것이 없고, 런타임에 실제로
    /// 생기는 변화는 긴급 블록 배정뿐이다.
    ///
    /// type 값:
    ///  - "hello"          연결 직후 1회. 서버의 project_epoch 확인용.
    ///  - "block_added"    긴급 블록이 정반에 배정됨. Block 에 계약 형태의 블록 1개가 실린다.
    ///  - "block_rejected" 배정 실패 또는 계약으로 표현할 수 없는 입력. Reason 에 사유.
    ///
    /// 블록 본문은 스냅샷과 **같은 BlockDto** 를 재사용한다. 따라서 검증도
    /// SchedulePayloadMapper.MapBlock 이라는 같은 경로를 탄다.
    /// </summary>
    [Serializable]
    public sealed class ScheduleStreamMessageDto
    {
        [JsonProperty("schema_version")]
        public string SchemaVersion { get; set; }

        [JsonProperty("type")]
        public string Type { get; set; }

        [JsonProperty("event_id")]
        public string EventId { get; set; }

        [JsonProperty("sent_at")]
        public string SentAt { get; set; }

        /// <summary>"block_added" 일 때만 채워진다.</summary>
        [JsonProperty("block")]
        public BlockDto Block { get; set; }

        /// <summary>"block_rejected" 일 때 원본 요청의 block_id.</summary>
        [JsonProperty("block_id")]
        public string BlockId { get; set; }

        /// <summary>"block_rejected" 일 때 사람이 읽을 수 있는 사유.</summary>
        [JsonProperty("reason")]
        public string Reason { get; set; }

        /// <summary>긴급도 라벨(예: CRITICAL). 표시용 메타.</summary>
        [JsonProperty("emergency_level")]
        public string EmergencyLevel { get; set; }

        /// <summary>납기 대비 지연 일수. 표시용 메타이며 색상은 시각으로 계산한다.</summary>
        [JsonProperty("delay_days")]
        public int DelayDays { get; set; }

        /// <summary>"hello" 일 때 서버가 쓰는 기준일.</summary>
        [JsonProperty("project_epoch")]
        public string ProjectEpoch { get; set; }

        /// <summary>"hello" 일 때 현재 연결 수.</summary>
        [JsonProperty("connected_clients")]
        public int ConnectedClients { get; set; }
    }
}
