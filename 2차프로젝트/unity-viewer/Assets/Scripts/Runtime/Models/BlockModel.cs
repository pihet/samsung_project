using System;
using UnityEngine;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 블록의 실행 중 모델. 검증을 통과한 값만 담는다.
    /// LocalPosition 은 배정 정반 원점 기준 로컬 오프셋(m).
    /// 시간은 오프셋을 보존한 DateTimeOffset.
    /// </summary>
    public sealed class BlockModel
    {
        public string BlockId { get; }
        public int SeqId { get; }
        public string ShipId { get; }
        public string PlatformId { get; }

        /// <summary>"FLAT" | "CURVED".</summary>
        public string BlockType { get; }

        /// <summary>X: length, Y: height, Z: width (m).</summary>
        public Vector3 Size { get; }

        /// <summary>배정 정반 원점 기준 로컬 오프셋(m).</summary>
        public Vector3 LocalPosition { get; }

        public BlockLifecycleStatus DeclaredStatus { get; }

        public DateTimeOffset StartTime { get; }
        public DateTimeOffset EndTime { get; }

        /// <summary>납기. 없으면 null.</summary>
        public DateTimeOffset? DueTime { get; }

        /// <summary>end_time 이 due_time 보다 뒤면 지연.</summary>
        public bool IsDelayed => DueTime.HasValue && EndTime > DueTime.Value;

        public BlockModel(
            string blockId,
            int seqId,
            string shipId,
            string platformId,
            string blockType,
            Vector3 size,
            Vector3 localPosition,
            BlockLifecycleStatus declaredStatus,
            DateTimeOffset startTime,
            DateTimeOffset endTime,
            DateTimeOffset? dueTime)
        {
            BlockId = blockId;
            SeqId = seqId;
            ShipId = shipId;
            PlatformId = platformId;
            BlockType = blockType;
            Size = size;
            LocalPosition = localPosition;
            DeclaredStatus = declaredStatus;
            StartTime = startTime;
            EndTime = endTime;
            DueTime = dueTime;
        }

        public TimelinePhase EvaluatePhase(DateTimeOffset now)
        {
            return TimelinePhaseCalculator.Evaluate(now, StartTime, EndTime);
        }
    }
}
