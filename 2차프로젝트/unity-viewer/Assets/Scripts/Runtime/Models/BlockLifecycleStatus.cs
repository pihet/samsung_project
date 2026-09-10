using System;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// Mock JSON 의 status 필드에서 검증되는 "계획 생명주기" 값.
    /// 화면 색상은 이 값이 아니라 TimelinePhase(시각 기준 계산)로 결정한다.
    /// </summary>
    public enum BlockLifecycleStatus
    {
        Waiting,
        InProgress,
        Completed,
    }

    public static class BlockLifecycleStatusParser
    {
        /// <summary>계약이 허용하는 정확한 문자열만 통과시킨다. 그 외에는 false.</summary>
        public static bool TryParse(string raw, out BlockLifecycleStatus status)
        {
            switch (raw)
            {
                case "waiting":
                    status = BlockLifecycleStatus.Waiting;
                    return true;
                case "in_progress":
                    status = BlockLifecycleStatus.InProgress;
                    return true;
                case "completed":
                    status = BlockLifecycleStatus.Completed;
                    return true;
                default:
                    status = BlockLifecycleStatus.Waiting;
                    return false;
            }
        }

        public const string AllowedValues = "waiting, in_progress, completed";
    }
}
