using System.Collections;
using UnityEngine;
using ShipyardTwin.Runtime.Config;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 책임: TimelineClock.Now 를 기준으로 각 블록의 TimelinePhase 를 계산해
    /// StatusColorPalette 색을 BlockView 에 적용한다.
    ///
    /// 첫 구현은 DOTween 없이 Coroutine 폴링. 색은 즉시 스냅(보간 없음).
    /// </summary>
    public sealed class BlockStatusColorizer : MonoBehaviour
    {
        [SerializeField] private YardBlockSpawner spawner;
        [SerializeField] private TimelineClock clock;
        [SerializeField] private ViewerSceneBindings bindings;

        [Tooltip("색을 다시 계산하는 주기(초). 0 이면 매 프레임.")]
        [SerializeField] private float refreshIntervalSeconds = 0.25f;

        private Coroutine _loop;

        private void OnEnable()
        {
            _loop = StartCoroutine(RefreshLoop());
        }

        private void OnDisable()
        {
            if (_loop != null)
            {
                StopCoroutine(_loop);
                _loop = null;
            }
        }

        private IEnumerator RefreshLoop()
        {
            var wait = refreshIntervalSeconds > 0f
                ? new WaitForSeconds(refreshIntervalSeconds)
                : null;

            while (true)
            {
                ApplyOnce();
                yield return wait;
            }
        }

        /// <summary>외부(슬라이더 스크럽 등)에서 즉시 반영하고 싶을 때 호출.</summary>
        public void ApplyOnce()
        {
            if (spawner == null || clock == null || bindings == null
                || bindings.colorPalette == null)
            {
                return;
            }

            var now = clock.Now;
            var palette = bindings.colorPalette;

            var views = spawner.BlockViews;
            for (var i = 0; i < views.Count; i++)
            {
                var view = views[i];
                if (view == null || view.Model == null)
                {
                    continue;
                }

                var phase = view.Model.EvaluatePhase(now);

                // 실제로는 정반 하나에 동시에 한 블록만 올라간다. 옵션을 켜면
                // 작업 기간 밖 블록을 숨겨 물리적으로 정직한 화면을 만든다.
                view.SetVisible(!bindings.hideOutsideTimeWindow || phase == TimelinePhase.Active);
                view.SetColor(palette.Resolve(phase, view.Model.IsDelayed));
            }
        }
    }
}
