using System.Collections.Generic;
using UnityEngine;
using ShipyardTwin.Runtime.Config;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 책임: ScheduleDataset -> 씬 GameObject.
    /// 정반 프리팹을 야드 좌표에 놓고, 블록 프리팹을 배정 정반의 로컬 오프셋에 놓는다.
    /// 색상은 건드리지 않는다(BlockStatusColorizer 담당).
    /// </summary>
    public sealed class YardBlockSpawner : MonoBehaviour
    {
        [SerializeField] private MockScheduleLoader loader;
        [SerializeField] private ViewerSceneBindings bindings;

        [Tooltip("생성된 오브젝트가 담길 부모. 비우면 이 GameObject.")]
        [SerializeField] private Transform container;

        private readonly Dictionary<string, Transform> _platenRoots = new Dictionary<string, Transform>();
        private readonly List<BlockView> _blockViews = new List<BlockView>();

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
            if (loader != null)
            {
                loader.Loaded += Spawn;
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

        public void Clear()
        {
            for (var i = container.childCount - 1; i >= 0; i--)
            {
                var child = container.GetChild(i);
                if (Application.isPlaying)
                {
                    Destroy(child.gameObject);
                }
                else
                {
                    DestroyImmediate(child.gameObject);
                }
            }

            _platenRoots.Clear();
            _blockViews.Clear();
        }

        private void SpawnPlaten(PlatenModel platen)
        {
            var origin = platen.YardOrigin;
            if (bindings.useLayoutFallbackForZeroOrigin
                && bindings.yardLayout != null
                && origin == Vector3.zero)
            {
                origin = bindings.yardLayout.ResolveOrigin(platen.PlatenIdx);
            }

            var go = Instantiate(bindings.platenPrefab, container);
            go.name = $"Platen_{platen.PlatenId}_{platen.PlatenName}";
            go.transform.position = origin;

            if (bindings.scalePrefabToSize)
            {
                go.transform.localScale = new Vector3(
                    Mathf.Max(0.01f, platen.Size.x),
                    Mathf.Max(0.05f, bindings.platenSlabThickness),
                    Mathf.Max(0.01f, platen.Size.z));
            }

            _platenRoots[platen.PlatenId] = go.transform;
        }

        private void SpawnBlock(BlockModel block, Transform platenRoot)
        {
            var parent = bindings.parentBlocksToPlaten ? platenRoot : container;
            var go = Instantiate(bindings.blockPrefab, parent);
            go.name = $"Block_{block.BlockId}_{block.ShipId}";

            // 정반 상면에 얹히도록 높이의 절반만큼 들어 올린다.
            var lift = Vector3.up * (block.Size.y * 0.5f + bindings.platenSlabThickness * 0.5f);
            var localPos = block.LocalPosition + lift;

            if (bindings.parentBlocksToPlaten)
            {
                go.transform.localPosition = localPos;
            }
            else
            {
                go.transform.position = platenRoot.position + localPos;
            }

            if (bindings.scalePrefabToSize)
            {
                go.transform.localScale = new Vector3(
                    Mathf.Max(0.01f, block.Size.x),
                    Mathf.Max(0.01f, block.Size.y),
                    Mathf.Max(0.01f, block.Size.z));
            }

            var renderer = go.GetComponentInChildren<Renderer>();
            if (renderer == null)
            {
                Debug.LogWarning($"[YardBlockSpawner] blockPrefab 에 Renderer 가 없습니다: {go.name}");
            }

            var view = go.GetComponent<BlockView>();
            if (view == null)
            {
                view = go.AddComponent<BlockView>();
            }

            view.Bind(block, renderer);
            _blockViews.Add(view);
        }
    }
}
