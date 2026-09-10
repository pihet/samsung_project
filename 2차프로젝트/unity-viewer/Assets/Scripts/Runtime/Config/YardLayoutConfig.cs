using UnityEngine;

namespace ShipyardTwin.Runtime.Config
{
    /// <summary>
    /// 정적 에디터 설정: 실제 정반/블록 데이터에는 야드 좌표가 전혀 없다.
    /// Mock JSON 은 position 을 직접 부여하므로 스폰 시 그 값을 우선 쓴다.
    /// 이 설정은 position 이 없는 확장 데이터(REST/CSV 66개 정반)를 위한
    /// 격자 배치 폴백 규칙이다.
    /// </summary>
    [CreateAssetMenu(
        fileName = "YardLayoutConfig",
        menuName = "Shipyard Twin/Yard Layout Config",
        order = 1)]
    public sealed class YardLayoutConfig : ScriptableObject
    {
        [Min(1)]
        [Tooltip("한 행에 배치할 정반 수. 나머지는 다음 행으로 넘어간다.")]
        public int platensPerRow = 8;

        [Tooltip("정반 원점 간 X 간격(m). 정반 최대 length + 통로.")]
        public float columnSpacing = 45f;

        [Tooltip("정반 원점 간 Z 간격(m). 정반 최대 width + 통로.")]
        public float rowSpacing = 35f;

        [Tooltip("격자 전체의 월드 원점(m).")]
        public Vector3 gridOrigin = Vector3.zero;

        /// <summary>platen_idx 로 격자 위치를 계산한다(폴백 전용).</summary>
        public Vector3 ResolveOrigin(int platenIdx)
        {
            var safeIdx = Mathf.Max(0, platenIdx);
            var perRow = Mathf.Max(1, platensPerRow);
            var col = safeIdx % perRow;
            var row = safeIdx / perRow;
            return gridOrigin + new Vector3(col * columnSpacing, 0f, row * rowSpacing);
        }
    }
}
