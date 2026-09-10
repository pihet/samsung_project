using UnityEngine;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 책임: 씬의 조각들을 이어 붙이는 최소 배선점.
    ///  - 로드 성공 시 TimelineClock 을 데이터 시작 시각으로 초기화
    ///  - 로드 실패 시 원인을 한 곳에서 로그
    /// 스폰/색상은 각 컴포넌트가 loader 이벤트를 직접 구독하므로 여기서 다루지 않는다.
    /// </summary>
    public sealed class ViewerBootstrap : MonoBehaviour
    {
        [SerializeField] private MockScheduleLoader loader;
        [SerializeField] private TimelineClock clock;

        [Tooltip("클럭 시작 지점을 데이터의 가장 이른 start_time 보다 이만큼 앞당긴다(시간).")]
        [SerializeField] private double leadInHours = 24.0;

        private void OnEnable()
        {
            if (loader == null)
            {
                Debug.LogError("[ViewerBootstrap] loader 참조가 없습니다.");
                return;
            }

            loader.Loaded += OnLoaded;
            loader.LoadFailed += OnLoadFailed;
        }

        private void OnDisable()
        {
            if (loader == null)
            {
                return;
            }

            loader.Loaded -= OnLoaded;
            loader.LoadFailed -= OnLoadFailed;
        }

        private void OnLoaded(ScheduleDataset dataset)
        {
            if (clock != null)
            {
                clock.Initialize(dataset.EarliestStart.AddHours(-leadInHours));
            }
        }

        private void OnLoadFailed(string reason)
        {
            Debug.LogError($"[ViewerBootstrap] 스케줄 로드 실패로 시각화를 시작할 수 없습니다.\n{reason}");
        }
    }
}
