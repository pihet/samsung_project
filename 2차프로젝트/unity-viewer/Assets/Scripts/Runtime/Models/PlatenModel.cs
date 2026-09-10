using UnityEngine;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 정반의 실행 중 모델. DTO 가 아닌 일반 C# 객체이며 이미 검증된 값만 담는다.
    /// 좌표는 meter, YardOrigin 은 Unity 월드 좌표(XZ 지면, Y 높이).
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

        /// <summary>야드 내 정반 원점(월드, m).</summary>
        public Vector3 YardOrigin { get; }

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
            CraneCapacityTon = craneCapacityTon;
            AcceptsBlockType = acceptsBlockType;
        }
    }
}
