# `Assets/Prefabs/` — 에디터에서 만들 프리팹

이 폴더에는 **코드로 위조하지 않은** 프리팹 `.prefab` 자산이 들어간다.
아래 2개를 Unity 에디터에서 직접 생성한 뒤 `ViewerSceneBindings` 에셋에 연결한다.

## 1. `Platen.prefab` — 판(slab) 메시

- `GameObject > 3D Object > Cube` 로 생성 → 이름 `Platen`.
- Transform Scale 은 `(1, 1, 1)` 로 둔다. 스폰 시 `YardBlockSpawner` 가
  `(length, platenSlabThickness, width)` 로 덮어쓴다.
- 큐브의 로컬 피벗은 중심이다(기본값 그대로 두면 된다). 스포너가 크기의 절반을 더해
  판이 로컬 `x∈[0,length]`, `z∈[0,width]` 를 차지하도록 맞춘다.
- 머티리얼: 바닥 판용 URP 머티리얼 1개(예: 어두운 회색 `Platen_Mat`). 색 갱신 대상 아님.
- `Assets/Prefabs/Platen.prefab` 로 저장.

> **중요:** 이 프리팹은 스폰될 때 정반 루트 그 자체가 아니라 **루트의 자식 `Slab`** 이 된다.
> 스포너가 스케일 1인 빈 루트를 만들고 그 아래에 이 프리팹과 블록들을 나란히 넣는다.
> 정반 루트를 스케일하지 않아야 자식 블록의 위치·크기가 정반 크기만큼 곱해지지 않는다.
>
> ```
> Platen_PPT1000A_Bay10-N-1   (빈 GameObject, scale 1, 위치 = 정반 최소 코너)
> ├─ Slab                      (이 프리팹, scale = 28 × 0.5 × 18)
> ├─ Block_B0001_H1080         (Block.prefab, scale = 7.4 × 3 × 6.8)
> └─ ...
> ```

## 2. `Block.prefab`

- `GameObject > 3D Object > Cube` 로 생성 → 이름 `Block`.
- Transform Scale `(1, 1, 1)`. 스폰 시 `(length, height, width)` 로 덮어쓴다.
- **Renderer 가 반드시 1개 이상** 있어야 한다(큐브 기본 `MeshRenderer` 로 충족).
- 머티리얼: URP `Universal Render Pipeline/Lit` 또는 `Unlit` 기반 `Block_Mat` 1개.
  `BlockView` 가 `MaterialPropertyBlock` 으로 `_BaseColor`(URP)/`_Color`(폴백)만 바꾸므로
  머티리얼 자체는 공유해도 배칭이 깨지지 않는다.
- `BlockView` 컴포넌트는 붙이지 않아도 된다. 스포너가 없으면 `AddComponent` 한다.
  (원하면 미리 붙여도 무방하다.)
- `Assets/Prefabs/Block.prefab` 로 저장.

## 연결

`Assets/ScriptableObjects/ViewerSceneBindings.asset` 의
`platenPrefab`, `blockPrefab` 슬롯에 위 2개를 드래그한다.
