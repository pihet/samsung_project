using System.Collections.Generic;
using UnityEngine;
using ShipyardTwin.Runtime.Config;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 책임: ScheduleDataset -> 씬 GameObject.
    /// 색상은 건드리지 않는다(BlockStatusColorizer 담당).
    ///
    /// 계층 구조 (스케일 오염을 피하기 위한 핵심):
    ///   Platen_&lt;id&gt;      : 빈 GameObject, **스케일 1**, 위치 = 정반 바닥 최소 코너
    ///   ├─ Slab           : platenPrefab, 스케일 = (length, thickness, width)
    ///   └─ Block_&lt;id&gt;   : blockPrefab,  스케일 = (length, height, width)
    /// 정반 루트를 스케일하지 않으므로 자식 블록의 localPosition/localScale 이
    /// 정반 크기만큼 곱해지는 문제가 생기지 않는다.
    ///
    /// 좌표 규약: 정반 로컬에서 판은 x∈[0,length], z∈[0,width], y∈[0,thickness] 를 차지한다.
    /// 블록 position 은 **발자국 최소 코너**이고 y 는 판 상면 기준 추가 높이다.
    /// 프리팹은 중심 피벗 단위 큐브를 가정하므로 스폰 시 크기의 절반을 더해 중심을 맞춘다.
    /// </summary>
    public sealed class YardBlockSpawner : MonoBehaviour
    {
        [SerializeField] private MockScheduleLoader loader;
        [SerializeField] private ViewerSceneBindings bindings;

        [Tooltip("생성된 오브젝트가 담길 부모. 비우면 이 GameObject 아래에 전용 루트를 만든다.")]
        [SerializeField] private Transform container;

        private readonly Dictionary<string, Transform> _platenRoots = new Dictionary<string, Transform>();
        private readonly List<BlockView> _blockViews = new List<BlockView>();

        /// <summary>이 스포너가 만든 루트만 추적한다. Clear 는 이것만 파괴한다.</summary>
        private readonly List<GameObject> _spawnedRoots = new List<GameObject>();

        public IReadOnlyList<BlockView> BlockViews => _blockViews;

        private void Awake()
        {
            if (container == null)
            {
                container = transform;
            }
        }

        private void OnEnable()
        {
            if (loader == null)
            {
                Debug.LogError("[YardBlockSpawner] loader 참조가 없습니다.");
                return;
            }

            loader.Loaded += Spawn;

            // 이미 로드가 끝난 뒤에 활성화된 경우에도 씬이 비지 않도록 재생한다.
            if (loader.IsLoaded && _spawnedRoots.Count == 0)
            {
                Spawn(loader.Dataset);
            }
        }

        private void OnDisable()
        {
            if (loader != null)
            {
                loader.Loaded -= Spawn;
            }
        }

        public void Spawn(ScheduleDataset dataset)
        {
            if (dataset == null)
            {
                Debug.LogError("[YardBlockSpawner] dataset 이 null 입니다.");
                return;
            }

            if (bindings == null || bindings.platenPrefab == null || bindings.blockPrefab == null)
            {
                Debug.LogError("[YardBlockSpawner] ViewerSceneBindings 의 프리팹이 비어 있습니다. " +
                               "인스펙터에서 platenPrefab / blockPrefab 을 연결하세요.");
                return;
            }

            if (container == null)
            {
                container = transform;
            }

            Clear();

            foreach (var platen in dataset.Platens)
            {
                SpawnPlaten(platen);
            }

            var missing = 0;
            foreach (var block in dataset.Blocks)
            {
                if (!_platenRoots.TryGetValue(block.PlatformId, out var platenRoot))
                {
                    // 매퍼가 걸러내므로 정상 경로에서는 도달하지 않는다.
                    missing++;
                    continue;
                }

                SpawnBlock(block, platenRoot);
            }

            if (missing > 0)
            {
                Debug.LogWarning($"[YardBlockSpawner] 정반을 못 찾은 블록 {missing}개를 건너뛰었습니다.");
            }

            Debug.Log($"[YardBlockSpawner] 정반 {_platenRoots.Count}개, 블록 {_blockViews.Count}개 스폰 완료.");
        }

        /// <summary>이 스포너가 생성한 오브젝트만 제거한다(사용자가 둔 다른 자식은 건드리지 않음).</summary>
        public void Clear()
        {
            foreach (var root in _spawnedRoots)
            {
                if (root == null)
                {
                    continue;
                }

                if (Application.isPlaying)
                {
                    Destroy(root);
                }
                else
                {
                    DestroyImmediate(root);
                }
            }

            _spawnedRoots.Clear();
            _platenRoots.Clear();
            _blockViews.Clear();
        }

        private void SpawnPlaten(PlatenModel platen)
        {
            var origin = platen.YardOrigin;
            if (!platen.HasExplicitOrigin && bindings.yardLayout != null)
            {
                origin = bindings.yardLayout.ResolveOrigin(platen.PlatenIdx);
            }

            // 1) 스케일 1인 빈 루트. 자식 좌표가 왜곡되지 않는 기준점이 된다.
            var root = new GameObject($"Platen_{platen.PlatenId}_{platen.PlatenName}");
            root.transform.SetParent(container, false);
            root.transform.localPosition = origin;

            // 2) 판 메시는 자식으로. 여기에만 스케일을 준다.
            var slab = Instantiate(bindings.platenPrefab, root.transform);
            slab.name = "Slab";

            var thickness = Mathf.Max(0.05f, bindings.platenSlabThickness);
            if (bindings.scalePrefabToSize)
            {
                slab.transform.localScale = new Vector3(
                    Mathf.Max(0.01f, platen.Size.x),
                    thickness,
                    Mathf.Max(0.01f, platen.Size.z));
            }

            // 중심 피벗 큐브를 x∈[0,L], z∈[0,W], y∈[0,t] 에 맞춘다.
            slab.transform.localPosition = new Vector3(
                platen.Size.x * 0.5f,
                thickness * 0.5f,
                platen.Size.z * 0.5f);

            _platenRoots[platen.PlatenId] = root.transform;
            _spawnedRoots.Add(root);
        }

        private void SpawnBlock(BlockModel block, Transform platenRoot)
        {
            var go = Instantiate(bindings.blockPrefab, platenRoot);
            go.name = $"Block_{block.BlockId}_{block.ShipId}";

            if (bindings.scalePrefabToSize)
            {
                go.transform.localScale = new Vector3(
                    Mathf.Max(0.01f, block.Size.x),
                    Mathf.Max(0.01f, block.Size.y),
                    Mathf.Max(0.01f, block.Size.z));
            }

            // position 은 발자국 최소 코너 → 중심 피벗에 맞게 절반을 더한다.
            // Y 는 판 상면(thickness) 위에 얹는다.
            var thickness = Mathf.Max(0.05f, bindings.platenSlabThickness);
            go.transform.localPosition = new Vector3(
                block.LocalPosition.x + block.Size.x * 0.5f,
                thickness + block.LocalPosition.y + block.Size.y * 0.5f,
                block.LocalPosition.z + block.Size.z * 0.5f);

            var blockRenderer = go.GetComponentInChildren<Renderer>();
            if (blockRenderer == null)
            {
                Debug.LogWarning($"[YardBlockSpawner] blockPrefab 에 Renderer 가 없습니다: {go.name}");
            }

            var view = go.GetComponent<BlockView>();
            if (view == null)
            {
                view = go.AddComponent<BlockView>();
            }

            view.Bind(block, blockRenderer);
            _blockViews.Add(view);
        }
    }
}
