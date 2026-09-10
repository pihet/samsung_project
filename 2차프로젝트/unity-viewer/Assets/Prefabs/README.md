# `Assets/Prefabs/` — 에디터에서 만들 프리팹

이 폴더에는 **코드로 위조하지 않은** 프리팹 `.prefab` 자산이 들어간다.
아래 2개를 Unity 에디터에서 직접 생성한 뒤 `ViewerSceneBindings` 에셋에 연결한다.

## 1. `Platen.prefab`

- `GameObject > 3D Object > Cube` 로 생성 → 이름 `Platen`.
- Transform Scale 은 `(1, 1, 1)` 로 둔다. 스폰 시 `YardBlockSpawner` 가
  `(length, platenSlabThickness, width)` 로 덮어쓴다.
- 큐브의 로컬 피벗은 중심이다. 스포너는 정반 상면 기준으로 블록을 올리므로 피벗을 바꾸지 않는다.
- 머티리얼: 바닥 판용 URP 머티리얼 1개(예: 어두운 회색 `Platen_Mat`). 색 갱신 대상 아님.
- `Assets/Prefabs/Platen.prefab` 로 저장.

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
