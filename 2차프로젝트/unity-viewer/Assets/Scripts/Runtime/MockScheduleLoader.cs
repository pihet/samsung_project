using System;
using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;
using ShipyardTwin.Data;

namespace ShipyardTwin.Runtime
{
    /// <summary>스케줄 페이로드를 어디서 가져올지.</summary>
    public enum ScheduleSource
    {
        /// <summary>StreamingAssets 의 로컬 JSON(정반 8 / 블록 40 Mock).</summary>
        StreamingAssetsFile = 0,

        /// <summary>백엔드 REST 어댑터(정반 66 / 블록 872 실데이터).</summary>
        RestApi = 1,
    }

    /// <summary>
    /// 책임: 스케줄 JSON 바이트를 확보해 파서 -> 매퍼를 거쳐
    /// ScheduleDataset 을 만들고 이벤트로 알린다.
    ///
    /// 소스는 두 가지다. 둘 다 같은 전송 계약(schema_version 1.x)을 따르므로
    /// 파싱·검증·매핑·스폰·색상 갱신은 소스와 무관하게 그대로 재사용된다.
    ///  - StreamingAssetsFile: 로컬 Mock. 백엔드 없이 동작한다.
    ///  - RestApi: GET {apiBaseUrl}/api/viewer/schedule/{algorithm}.
    ///    백엔드가 경과일 -> ISO 시각 변환, seq_id 조인, 정반 중앙 배치까지 끝내고
    ///    이 계약 형태로 내보낸다. 원시 /api/schedule/{algorithm} 이 아니다.
    /// </summary>
    public sealed class MockScheduleLoader : MonoBehaviour
    {
        [Tooltip("페이로드를 가져올 소스.")]
        [SerializeField] private ScheduleSource source = ScheduleSource.StreamingAssetsFile;

        [Header("StreamingAssetsFile 모드")]
        [Tooltip("StreamingAssets 기준 상대 경로.")]
        [SerializeField] private string fileName = "mock_schedule.json";

        [Header("RestApi 모드")]
        [Tooltip("백엔드 주소. 끝의 슬래시는 있어도 없어도 된다.")]
        [SerializeField] private string apiBaseUrl = "http://localhost:8000";

        [Tooltip("알고리즘 키: ortools, ppo, dqn, est, spt, lpt, rtb, rub.")]
        [SerializeField] private string algorithm = "ortools";

        [Min(1)]
        [Tooltip("REST 요청 타임아웃(초). 872개 블록 응답은 수 MB 다.")]
        [SerializeField] private int requestTimeoutSeconds = 30;

        [Header("공통")]
        [Tooltip("Start() 에서 자동으로 로드한다.")]
        [SerializeField] private bool loadOnStart = true;

        /// <summary>RestApi 모드에서 쓰는 백엔드 주소. 스트림 클라이언트가 같은 주소를 재사용한다.</summary>
        public string ApiBaseUrl => apiBaseUrl;

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
            if (!TryBuildUri(out var uri, out var uriError))
            {
                Fail(uriError);
                yield break;
            }

            string json = null;
            using (var request = UnityWebRequest.Get(uri))
            {
                if (source == ScheduleSource.RestApi)
                {
                    request.timeout = Mathf.Max(1, requestTimeoutSeconds);
                }

                yield return request.SendWebRequest();

                if (request.result != UnityWebRequest.Result.Success)
                {
                    Fail($"스케줄 로드 실패 ({uri}): {request.error}");
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
                Fail($"스케줄 JSON 파싱 실패: {ex.Message}");
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

        /// <summary>소스에 맞는 요청 URI 를 만든다. 실패 사유는 문자열로 돌려준다.</summary>
        private bool TryBuildUri(out string uri, out string error)
        {
            uri = null;
            error = null;

            if (source == ScheduleSource.RestApi)
            {
                if (string.IsNullOrWhiteSpace(apiBaseUrl))
                {
                    error = "apiBaseUrl 이 비어 있습니다. RestApi 모드에는 백엔드 주소가 필요합니다.";
                    return false;
                }

                if (string.IsNullOrWhiteSpace(algorithm))
                {
                    error = "algorithm 이 비어 있습니다. 예: ortools, ppo, est.";
                    return false;
                }

                uri = $"{apiBaseUrl.TrimEnd('/')}/api/viewer/schedule/{algorithm.Trim()}";
                return true;
            }

            if (string.IsNullOrWhiteSpace(fileName))
            {
                error = "fileName 이 비어 있습니다.";
                return false;
            }

            var path = Path.Combine(Application.streamingAssetsPath, fileName);

            // Android 등에서는 이미 jar:file://... 형태라 그대로 쓴다.
            // 그 외에는 new Uri(...).AbsoluteUri 로 플랫폼별 구분자·드라이브 문자를
            // 올바른 file:/// 형태로 만든다("file://" 문자열 접합은 Windows 에서 깨진다).
            uri = path.Contains("://") ? path : new Uri(path).AbsoluteUri;
            return true;
        }

        private void Fail(string message)
        {
            Debug.LogError($"[MockScheduleLoader] {message}");
            LoadFailed?.Invoke(message);
        }
    }
}
