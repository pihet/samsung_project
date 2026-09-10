using System;
using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;
using ShipyardTwin.Data;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 책임: StreamingAssets 의 Mock JSON 을 읽어 파서 -> 매퍼를 거쳐
    /// ScheduleDataset 을 만들고 이벤트로 알린다.
    ///
    /// 확장 지점: 이후 REST(GET /api/schedule/{algorithm}) 나 WebSocket 소스로 교체하려면
    /// LoadRoutine 의 본문(바이트 획득 부분)만 바꾸면 된다. 파싱·검증·매핑은 그대로 재사용.
    /// </summary>
    public sealed class MockScheduleLoader : MonoBehaviour
    {
        [Tooltip("StreamingAssets 기준 상대 경로.")]
        [SerializeField] private string fileName = "mock_schedule.json";

        [Tooltip("Start() 에서 자동으로 로드한다.")]
        [SerializeField] private bool loadOnStart = true;

        /// <summary>로드·검증 성공 시 1회 호출.</summary>
        public event Action<ScheduleDataset> Loaded;

        /// <summary>로드 또는 검증 실패 시 호출. 문자열은 사람이 읽을 수 있는 원인.</summary>
        public event Action<string> LoadFailed;

        public ScheduleDataset Dataset { get; private set; }
        public bool IsLoaded => Dataset != null;

        private void Start()
        {
            if (loadOnStart)
            {
                Load();
            }
        }

        public void Load()
        {
            StopAllCoroutines();
            StartCoroutine(LoadRoutine());
        }

        private IEnumerator LoadRoutine()
        {
            var path = Path.Combine(Application.streamingAssetsPath, fileName);

            // Android 등에서는 이미 jar:file://... 형태라 그대로 쓴다.
            // 그 외에는 new Uri(...).AbsoluteUri 로 플랫폼별 구분자·드라이브 문자를
            // 올바른 file:/// 형태로 만든다("file://" 문자열 접합은 Windows 에서 깨진다).
            var uri = path.Contains("://") ? path : new Uri(path).AbsoluteUri;

            string json = null;
            using (var request = UnityWebRequest.Get(uri))
            {
                yield return request.SendWebRequest();

                if (request.result != UnityWebRequest.Result.Success)
                {
                    Fail($"Mock JSON 로드 실패 ({uri}): {request.error}");
                    yield break;
                }

                json = request.downloadHandler.text;
            }

            ScheduleDataset dataset;
            try
            {
                var dto = SchedulePayloadParser.Parse(json);
                dataset = SchedulePayloadMapper.Map(dto);
            }
            catch (SchedulePayloadParseException ex)
            {
                Fail($"Mock JSON 파싱 실패: {ex.Message}");
                yield break;
            }
            catch (SchedulePayloadValidationException ex)
            {
                Fail(ex.Message);
                yield break;
            }

            Dataset = dataset;
            Debug.Log(
                $"[MockScheduleLoader] 로드 완료: 정반 {dataset.Platens.Count}개, " +
                $"블록 {dataset.Blocks.Count}개, 알고리즘 '{dataset.Algorithm}', " +
                $"기간 {dataset.EarliestStart:o} ~ {dataset.LatestEnd:o}");
            Loaded?.Invoke(dataset);
        }

        private void Fail(string message)
        {
            Debug.LogError($"[MockScheduleLoader] {message}");
            LoadFailed?.Invoke(message);
        }
    }
}
