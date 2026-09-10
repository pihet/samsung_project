# `Assets/ScriptableObjects/` — 에디터에서 만들 설정 자산

ScriptableObject **클래스 정의는 코드**(`Assets/Scripts/Runtime/Config/`)에 있고,
그 **인스턴스 `.asset` 는 에디터에서 생성**한다. 여기엔 정적 편집 설정만 둔다
(정반 배치 규칙, 색상, 프리팹 참조). 실행 중 상태는 담지 않는다.

프로젝트 창에서 `Create > Shipyard Twin > ...` 메뉴로 아래 3개를 만든다.

## 1. `StatusColorPalette.asset`

- 메뉴: `Create > Shipyard Twin > Status Color Palette`
- 필드: `scheduled`(회색), `active`(파랑), `completed`(초록),
  `delayedTint`(빨강), `delayedBlend`(0~1).
- `TimelinePhase` × 지연여부 → 색을 결정한다.

## 2. `YardLayoutConfig.asset`

- 메뉴: `Create > Shipyard Twin > Yard Layout Config`
- 필드: `platensPerRow`, `columnSpacing`(m), `rowSpacing`(m), `gridOrigin`.
- **폴백 전용**: Mock JSON 은 정반 `position` 을 직접 주므로 사용되지 않는다.
  좌표 없는 확장 데이터(REST 66정반)에서 `platen_idx` 로 격자 배치할 때 쓴다.

## 3. `ViewerSceneBindings.asset`

- 메뉴: `Create > Shipyard Twin > Viewer Scene Bindings`
- 슬롯:
  - `platenPrefab` ← `Assets/Prefabs/Platen.prefab`
  - `blockPrefab` ← `Assets/Prefabs/Block.prefab`
  - `colorPalette` ← `StatusColorPalette.asset`
  - `yardLayout` ← `YardLayoutConfig.asset`
  - `scalePrefabToSize` = true, `parentBlocksToPlaten` = true,
    `platenSlabThickness` = 0.5, `useLayoutFallbackForZeroOrigin` = true

이 3개를 만든 뒤 씬 배선은 상위 `../../README.md` 의 "씬 구성" 절을 따른다.
