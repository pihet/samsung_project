using System;
using System.Collections.Generic;

namespace ShipyardTwin.Data
{
    /// <summary>Newtonsoft 역직렬화 단계에서 JSON 자체가 깨졌을 때.</summary>
    public sealed class SchedulePayloadParseException : Exception
    {
        public SchedulePayloadParseException(string message, Exception inner)
            : base(message, inner) { }
    }

    /// <summary>
    /// DTO -> 런타임 모델 매핑 단계에서 계약 위반이 하나 이상 발견됐을 때.
    /// 개별 위반은 문맥(어느 id, 어느 필드)을 포함한 문자열로 누적한다.
    /// </summary>
    public sealed class SchedulePayloadValidationException : Exception
    {
        public IReadOnlyList<string> Errors { get; }

        public SchedulePayloadValidationException(IReadOnlyList<string> errors)
            : base(BuildMessage(errors))
        {
            Errors = errors;
        }

        private static string BuildMessage(IReadOnlyList<string> errors)
        {
            if (errors == null || errors.Count == 0)
            {
                return "스케줄 페이로드 검증 실패 (상세 없음)";
            }

            return $"스케줄 페이로드 검증 실패: {errors.Count}건\n - " + string.Join("\n - ", errors);
        }
    }
}
