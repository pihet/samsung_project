using UnityEngine;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 정반의 실행 중 모델. DTO 가 아닌 일반 C# 객체이며 이미 검증된 값만 담는다.
    /// 좌표는 meter, YardOrigin 은 정반 바닥면 **최소 코너**의 Unity 월드 좌표
    /// (XZ 지면, Y 높이). 판은 로컬 x∈[0,length], z∈[0,width] 를 차지한다.
    /// </summary>
    public sealed class PlatenModel
    {
        public string PlatenId { get; }
        public int PlatenIdx { get; }
        public string PlatenName { get; }
        public string PrimaryArea { get; }
        public string SecondaryArea { get; }

        /// <summary>X: length, Y: height, Z: width (m).</summary>
        public Vector3 Size { get; }

        /// <summary>야드 내 정반 바닥면 최소 코너(월드, m).</summary>
        public Vector3 YardOrigin { get; }

        /// <summary>
        /// JSON 이 position 을 명시했으면 true. false 면 YardOrigin 은 격자 폴백으로 채운 값이다.
        /// (0,0,0) 을 "좌표 없음"으로 오해하지 않기 위한 구분.
        /// </summary>
        public bool HasExplicitOrigin { get; }

        public float CraneCapacityTon { get; }

        /// <summary>"FLAT" | "CURVED" | "ANY".</summary>
        public string AcceptsBlockType { get; }

        public PlatenModel(
            string platenId,
            int platenIdx,
            string platenName,
            string primaryArea,
            string secondaryArea,
            Vector3 size,
            Vector3 yardOrigin,
            bool hasExplicitOrigin,
            float craneCapacityTon,
            string acceptsBlockType)
        {
            PlatenId = platenId;
            PlatenIdx = platenIdx;
            PlatenName = platenName;
            PrimaryArea = primaryArea;
            SecondaryArea = secondaryArea;
            Size = size;
            YardOrigin = yardOrigin;
            HasExplicitOrigin = hasExplicitOrigin;
            CraneCapacityTon = craneCapacityTon;
            AcceptsBlockType = acceptsBlockType;
        }
    }
}
