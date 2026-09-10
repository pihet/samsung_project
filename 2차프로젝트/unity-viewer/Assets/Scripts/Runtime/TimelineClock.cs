using System;
using UnityEngine;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 책임: 시뮬레이션 "현재 시각"(DateTimeOffset) 하나만 관리한다.
    /// 색상 갱신·타임라인 UI 가 이 값을 읽는다. 스폰이나 로딩은 몰라도 된다.
    /// </summary>
    public sealed class TimelineClock : MonoBehaviour
    {
        [Tooltip("실시간 1초당 흐르게 할 시뮬레이션 시간(시간 단위). 예: 24 = 1초에 하루.")]
        [SerializeField] private double hoursPerRealSecond = 24.0;

        [SerializeField] private bool playing = true;

        public DateTimeOffset Now { get; private set; }
        public bool Playing { get => playing; set => playing = value; }

        /// <summary>Now 가 바뀔 때마다 호출(매 프레임).</summary>
        public event Action<DateTimeOffset> Ticked;

        private bool _initialized;

        /// <summary>보통 MockScheduleLoader.Loaded 에 연결해 데이터 범위 시작점으로 맞춘다.</summary>
        public void Initialize(DateTimeOffset start)
        {
            Now = start;
            _initialized = true;
            Ticked?.Invoke(Now);
        }

        public void SetNow(DateTimeOffset value)
        {
            Now = value;
            _initialized = true;
            Ticked?.Invoke(Now);
        }

        private void Update()
        {
            if (!_initialized || !playing)
            {
                return;
            }

            var deltaHours = hoursPerRealSecond * Time.deltaTime;
            Now = Now.AddHours(deltaHours);
            Ticked?.Invoke(Now);
        }
    }
}
