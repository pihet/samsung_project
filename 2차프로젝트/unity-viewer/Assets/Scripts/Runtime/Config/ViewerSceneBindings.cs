using UnityEngine;

namespace ShipyardTwin.Runtime.Config
{
    /// <summary>
    /// 정적 에디터 설정: 스폰에 쓸 프리팹·팔레트·레이아웃 참조 묶음.
    /// 에디터에서 Prefabs/ 의 프리팹과 ScriptableObjects/ 의 팔레트·레이아웃을 드래그해 채운다.
    /// </summary>
    [CreateAssetMenu(
        fileName = "ViewerSceneBindings",
        menuName = "Shipyard Twin/Viewer Scene Bindings",
        order = 2)]
    public sealed class ViewerSceneBindings : ScriptableObject
    {
        [Header("프리팹 (에디터에서 생성)")]
        [Tooltip("정반 판(slab)을 표현하는 프리팹. 중심 피벗 단위 큐브 기준. " +
                 "스포너가 스케일 1인 빈 루트의 자식으로 넣고 여기에만 스케일을 준다.")]
        public GameObject platenPrefab;

        [Tooltip("블록 1개를 표현하는 프리팹. 중심 피벗 단위 큐브 기준. Renderer 를 최소 1개 포함해야 한다.")]
        public GameObject blockPrefab;

        [Header("설정 에셋")]
        public StatusColorPalette colorPalette;

        [Tooltip("정반 position 이 JSON 에 없을 때만 쓰이는 격자 폴백.")]
        public YardLayoutConfig yardLayout;

        [Header("스폰 옵션")]
        [Tooltip("프리팹이 단위 큐브(1m)라고 가정하고 치수(m) 로 로컬 스케일을 맞춘다.")]
        public bool scalePrefabToSize = true;

        [Min(0.05f)]
        [Tooltip("정반은 판(slab)으로 표현한다. height(높이 한계)는 메타로만 쓰고 시각 두께는 이 값.")]
        public float platenSlabThickness = 0.5f;

        [Header("타임라인 표시")]
        [Tooltip("켜면 작업 기간 밖(착수 전/완료)의 블록을 숨긴다. " +
                 "실제로는 정반 하나에 동시에 한 블록만 올라가므로 물리적으로 정직한 표시.")]
        public bool hideOutsideTimeWindow = false;
    }
}
