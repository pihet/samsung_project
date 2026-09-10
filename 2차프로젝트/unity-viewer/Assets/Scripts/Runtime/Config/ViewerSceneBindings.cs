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
        [Tooltip("정반 1개를 표현하는 프리팹. 루트 스케일 1,1,1 권장. 스폰 시 Size 로 스케일된다.")]
        public GameObject platenPrefab;

        [Tooltip("블록 1개를 표현하는 프리팹. Renderer 를 최소 1개 포함해야 한다.")]
        public GameObject blockPrefab;

        [Header("설정 에셋")]
        public StatusColorPalette colorPalette;
        public YardLayoutConfig yardLayout;

        [Header("스폰 옵션")]
        [Tooltip("프리팹이 단위 큐브(1m)라고 가정하고 Size(m) 로 로컬 스케일을 맞춘다.")]
        public bool scalePrefabToSize = true;

        [Tooltip("블록을 정반의 자식으로 부모화한다.")]
        public bool parentBlocksToPlaten = true;

        [Min(0.05f)]
        [Tooltip("정반은 판(slab)으로 표현한다. height(높이 한계)는 메타로만 쓰고 시각 두께는 이 값.")]
        public float platenSlabThickness = 0.5f;

        [Tooltip("정반 원점 좌표가 (0,0,0) 이고 YardLayoutConfig 가 있으면 격자 폴백을 쓴다.")]
        public bool useLayoutFallbackForZeroOrigin = true;
    }
}
