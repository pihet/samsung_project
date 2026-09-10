using System;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 타임라인 시각화 상태. start_time / end_time 과 "현재 시각"만으로 계산한다.
    /// JSON 의 status 문자열과는 독립적이다.
    /// </summary>
    public enum TimelinePhase
    {
        /// <summary>현재 시각이 start_time 이전.</summary>
        Scheduled,

        /// <summary>현재 시각이 start_time 이상, end_time 미만.</summary>
        Active,

        /// <summary>현재 시각이 end_time 이상.</summary>
        Completed,
    }

    public static class TimelinePhaseCalculator
    {
        public static TimelinePhase Evaluate(
            DateTimeOffset now, DateTimeOffset startTime, DateTimeOffset endTime)
        {
            if (now < startTime)
            {
                return TimelinePhase.Scheduled;
            }

            if (now < endTime)
            {
                return TimelinePhase.Active;
            }

            return TimelinePhase.Completed;
        }
    }
}
