using UnityEngine;

namespace ShipyardTwin.Runtime.Config
{
    /// <summary>
    /// 정적 에디터 설정: TimelinePhase 별 색상과 "지연" 강조 색.
    /// 실행 중 상태가 아니므로 ScriptableObject 로 둔다.
    /// 에디터에서 Assets/ScriptableObjects/ 아래에 .asset 으로 생성한다.
    /// </summary>
    [CreateAssetMenu(
        fileName = "StatusColorPalette",
        menuName = "Shipyard Twin/Status Color Palette",
        order = 0)]
    public sealed class StatusColorPalette : ScriptableObject
    {
        [Header("타임라인 페이즈 색상")]
        public Color scheduled = new Color(0.55f, 0.60f, 0.66f); // 회색: 착수 전
        public Color active = new Color(0.20f, 0.68f, 1.00f);    // 파랑: 작업 중
        public Color completed = new Color(0.30f, 0.78f, 0.42f); // 초록: 완료

        [Header("강조")]
        [Tooltip("end_time 이 due_time 을 넘긴 블록에 곱해질 색조.")]
        public Color delayedTint = new Color(1.00f, 0.42f, 0.34f); // 빨강: 납기 지연

        [Range(0f, 1f)]
        [Tooltip("delayedTint 를 페이즈 색과 섞는 비율.")]
        public float delayedBlend = 0.6f;

        public Color Resolve(TimelinePhase phase, bool isDelayed)
        {
            var baseColor = phase switch
            {
                TimelinePhase.Scheduled => scheduled,
                TimelinePhase.Active => active,
                TimelinePhase.Completed => completed,
                _ => scheduled,
            };

            if (!isDelayed)
            {
                return baseColor;
            }

            return Color.Lerp(baseColor, delayedTint, Mathf.Clamp01(delayedBlend));
        }
    }
}
