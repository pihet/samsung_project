using System;
using Newtonsoft.Json;

namespace ShipyardTwin.Data
{
    /// <summary>
    /// 책임: 원시 JSON 문자열 -> SchedulePayloadDto 한 단계만 수행한다.
    /// 계약 검증(중복 id, 존재하지 않는 platform_id, position 길이, 시간 범위 등)은
    /// SchedulePayloadMapper 가 담당한다.
    /// </summary>
    public static class SchedulePayloadParser
    {
        private static readonly JsonSerializerSettings Settings = new JsonSerializerSettings
        {
            // 계약에 없는 필드가 늘어도 로더가 죽지 않도록: 알 수 없는 멤버는 무시.
            MissingMemberHandling = MissingMemberHandling.Ignore,
            // 날짜는 문자열 그대로 받아 매핑 단계에서 DateTimeOffset 으로 파싱한다.
            DateParseHandling = DateParseHandling.None,
            NullValueHandling = NullValueHandling.Ignore,
            Culture = System.Globalization.CultureInfo.InvariantCulture,
        };

        public static SchedulePayloadDto Parse(string json)
        {
            if (string.IsNullOrWhiteSpace(json))
            {
                throw new SchedulePayloadParseException("스케줄 JSON 이 비어 있습니다.", null);
            }

            SchedulePayloadDto dto;
            try
            {
                dto = JsonConvert.DeserializeObject<SchedulePayloadDto>(json, Settings);
            }
            catch (JsonException ex)
            {
                throw new SchedulePayloadParseException(
                    $"스케줄 JSON 역직렬화 실패: {ex.Message}", ex);
            }

            if (dto == null)
            {
                throw new SchedulePayloadParseException("스케줄 JSON 이 null 로 역직렬화되었습니다.", null);
            }

            return dto;
        }
    }
}
