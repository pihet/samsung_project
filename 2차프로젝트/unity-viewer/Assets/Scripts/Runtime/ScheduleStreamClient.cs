using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;
using ShipyardTwin.Data;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 책임: `/api/viewer/stream` WebSocket 에 붙어 증분 메시지를 받아
    /// 이미 스폰된 야드에 블록을 얹는다.
    ///
    /// 최초 스냅샷은 <see cref="MockScheduleLoader"/> 가 REST 로 가져온다. 이 클래스는
    /// 그 위에 추가되는 긴급 블록만 처리한다. 전체 스케줄 CSV 는 변하지 않으므로
    /// 재수신할 것이 없다.
    ///
    /// 스레드 규약: 수신은 백그라운드 Task 에서 돌고, 받은 문자열은 큐에만 넣는다.
    /// 파싱·검증·스폰은 전부 Update() 의 메인 스레드에서 한다. Unity API 는 메인 스레드
    /// 전용이라 이 경계를 넘으면 안 된다.
    ///
    /// 플랫폼: System.Net.WebSockets.ClientWebSocket 은 에디터·스탠드얼론에서 동작한다.
    /// WebGL 빌드에서는 쓸 수 없고 브라우저 소켓 API 로 교체해야 한다.
    /// </summary>
    public sealed class ScheduleStreamClient : MonoBehaviour
    {
        [Tooltip("스냅샷을 가져온 로더. 백엔드 주소와 데이터셋을 여기서 얻는다.")]
        [SerializeField] private MockScheduleLoader loader;

        [Tooltip("블록을 얹을 스포너.")]
        [SerializeField] private YardBlockSpawner spawner;

        [Tooltip("비우면 로더의 Api Base Url 을 그대로 쓴다. http 는 ws 로 자동 변환된다.")]
        [SerializeField] private string overrideBaseUrl = "";

        [Tooltip("스트림 경로.")]
        [SerializeField] private string streamPath = "/api/viewer/stream";

        [Tooltip("스냅샷 로드가 끝나면 자동으로 접속한다.")]
        [SerializeField] private bool connectOnLoad = true;

        [Min(1f)]
        [Tooltip("끊겼을 때 재접속까지 기다리는 시간(초).")]
        [SerializeField] private float reconnectDelaySeconds = 5f;

        [Min(1)]
        [Tooltip("한 프레임에 처리할 최대 메시지 수. 폭주 시 프레임 드랍을 막는다.")]
        [SerializeField] private int maxMessagesPerFrame = 16;

        /// <summary>블록이 실제로 씬에 추가됐을 때 호출.</summary>
        public event Action<BlockModel> BlockAdded;

        /// <summary>서버가 표시 불가로 돌려보냈을 때 호출. 문자열은 사유.</summary>
        public event Action<string> BlockRejected;

        public bool IsConnected { get; private set; }

        private const string LocalNoticePrefix = "notice:";

        private readonly ConcurrentQueue<string> _inbox = new ConcurrentQueue<string>();
        private CancellationTokenSource _cts;
        private ClientWebSocket _socket;
        private bool _running;

        private void OnEnable()
        {
            if (loader == null)
            {
                Debug.LogError("[ScheduleStreamClient] loader 참조가 없습니다.");
                return;
            }

            loader.Loaded += OnDatasetLoaded;

            // 이 컴포넌트가 늦게 켜져도 이미 로드가 끝났으면 바로 붙는다.
            if (connectOnLoad && loader.IsLoaded)
            {
                StartClient();
            }
        }

        private void OnDisable()
        {
            if (loader != null)
            {
                loader.Loaded -= OnDatasetLoaded;
            }

            StopClient();
        }

        private void OnDatasetLoaded(ScheduleDataset dataset)
        {
            if (connectOnLoad)
            {
                StartClient();
            }
        }

        /// <summary>수동 접속. 이미 돌고 있으면 아무것도 하지 않는다.</summary>
        public void StartClient()
        {
            if (_running)
            {
                return;
            }

            if (!TryBuildStreamUri(out var uri, out var error))
            {
                Debug.LogError($"[ScheduleStreamClient] {error}");
                return;
            }

            _running = true;
            _cts = new CancellationTokenSource();
            _ = RunAsync(uri, _cts.Token);
        }

        public void StopClient()
        {
            _running = false;
            IsConnected = false;

            if (_cts != null)
            {
                _cts.Cancel();
                _cts.Dispose();
                _cts = null;
            }

            // Abort 는 블로킹하지 않는다. 종료 경로에서 Close 핸드셰이크는 생략한다.
            _socket?.Abort();
            _socket?.Dispose();
            _socket = null;
        }

        /// <summary>백그라운드 수신 루프. 끊기면 지연 후 재접속한다.</summary>
        private async Task RunAsync(Uri uri, CancellationToken token)
        {
            var buffer = new byte[8192];

            while (_running && !token.IsCancellationRequested)
            {
                try
                {
                    _socket = new ClientWebSocket();
                    await _socket.ConnectAsync(uri, token);
                    IsConnected = true;
                    _inbox.Enqueue(LocalNoticePrefix + $"연결됨: {uri}");

                    var chunks = new List<byte>();
                    while (_running && _socket.State == WebSocketState.Open
                           && !token.IsCancellationRequested)
                    {
                        var result = await _socket.ReceiveAsync(
                            new ArraySegment<byte>(buffer), token);

                        if (result.MessageType == WebSocketMessageType.Close)
                        {
                            break;
                        }

                        for (var i = 0; i < result.Count; i++)
                        {
                            chunks.Add(buffer[i]);
                        }

                        if (!result.EndOfMessage)
                        {
                            continue;
                        }

                        _inbox.Enqueue(Encoding.UTF8.GetString(chunks.ToArray()));
                        chunks.Clear();
                    }
                }
                catch (OperationCanceledException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    // 여기서 Unity API 를 부르면 안 되므로 큐로 메인 스레드에 넘긴다.
                    _inbox.Enqueue(LocalNoticePrefix + $"연결 오류: {ex.Message}");
                }

                IsConnected = false;
                _socket?.Dispose();
                _socket = null;

                if (!_running || token.IsCancellationRequested)
                {
                    break;
                }

                try
                {
                    await Task.Delay(
                        TimeSpan.FromSeconds(Mathf.Max(1f, reconnectDelaySeconds)), token);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
            }

            IsConnected = false;
        }

        private void Update()
        {
            var processed = 0;
            while (processed < maxMessagesPerFrame && _inbox.TryDequeue(out var raw))
            {
                processed++;
                HandleMessage(raw);
            }
        }

        private void HandleMessage(string raw)
        {
            if (raw.StartsWith(LocalNoticePrefix, StringComparison.Ordinal))
            {
                Debug.Log($"[ScheduleStreamClient] {raw.Substring(LocalNoticePrefix.Length)}");
                return;
            }

            ScheduleStreamMessageDto message;
            try
            {
                message = SchedulePayloadParser.ParseStreamMessage(raw);
            }
            catch (SchedulePayloadParseException ex)
            {
                Debug.LogError($"[ScheduleStreamClient] 스트림 메시지 파싱 실패: {ex.Message}");
                return;
            }

            switch ((message.Type ?? string.Empty).Trim())
            {
                case "hello":
                    Debug.Log("[ScheduleStreamClient] hello 수신. " +
                              $"서버 project_epoch={message.ProjectEpoch}, " +
                              $"연결 수={message.ConnectedClients}");
                    break;

                case "block_added":
                    ApplyBlockAdded(message);
                    break;

                case "block_rejected":
                    Debug.LogWarning($"[ScheduleStreamClient] 블록 '{message.BlockId}' 표시 불가: " +
                                     $"{message.Reason}");
                    BlockRejected?.Invoke(message.Reason ?? string.Empty);
                    break;

                default:
                    Debug.Log($"[ScheduleStreamClient] 모르는 메시지 type '{message.Type}' 무시.");
                    break;
            }
        }

        private void ApplyBlockAdded(ScheduleStreamMessageDto message)
        {
            if (loader == null || !loader.IsLoaded)
            {
                Debug.LogWarning("[ScheduleStreamClient] 스냅샷이 아직 없어 증분 블록을 버립니다.");
                return;
            }

            if (spawner == null)
            {
                Debug.LogError("[ScheduleStreamClient] spawner 참조가 없습니다.");
                return;
            }

            var dataset = loader.Dataset;

            // 스냅샷과 같은 검증 경로를 탄다. 계약 위반이면 씬을 건드리지 않는다.
            var platenIds = new HashSet<string>();
            foreach (var platen in dataset.Platens)
            {
                platenIds.Add(platen.PlatenId);
            }

            var errors = new List<string>();
            var model = SchedulePayloadMapper.MapBlock(message.Block, platenIds, errors);

            if (errors.Count > 0 || model == null)
            {
                Debug.LogError($"[ScheduleStreamClient] 증분 블록 검증 실패 {errors.Count}건: " +
                               string.Join(" / ", errors));
                return;
            }

            if (!dataset.TryAddBlock(model))
            {
                Debug.LogWarning($"[ScheduleStreamClient] block_id '{model.BlockId}' 가 이미 " +
                                 "있어 무시합니다.");
                return;
            }

            if (!spawner.AddBlock(model))
            {
                Debug.LogWarning($"[ScheduleStreamClient] 블록 '{model.BlockId}' 스폰에 " +
                                 "실패했습니다.");
                return;
            }

            Debug.Log($"[ScheduleStreamClient] 긴급 블록 추가: '{model.BlockId}' -> 정반 " +
                      $"'{model.PlatformId}', {model.StartTime:yyyy-MM-dd} ~ " +
                      $"{model.EndTime:yyyy-MM-dd}");
            BlockAdded?.Invoke(model);
        }

        /// <summary>로더의 http 주소를 ws 주소로 바꾼다.</summary>
        private bool TryBuildStreamUri(out Uri uri, out string error)
        {
            uri = null;
            error = null;

            var baseUrl = string.IsNullOrWhiteSpace(overrideBaseUrl)
                ? (loader != null ? loader.ApiBaseUrl : null)
                : overrideBaseUrl;

            if (string.IsNullOrWhiteSpace(baseUrl))
            {
                error = "백엔드 주소가 비어 있습니다. 로더의 Api Base Url 을 채우거나 " +
                        "Override Base Url 을 지정하세요.";
                return false;
            }

            baseUrl = baseUrl.Trim().TrimEnd('/');

            if (baseUrl.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            {
                baseUrl = "wss://" + baseUrl.Substring("https://".Length);
            }
            else if (baseUrl.StartsWith("http://", StringComparison.OrdinalIgnoreCase))
            {
                baseUrl = "ws://" + baseUrl.Substring("http://".Length);
            }
            else if (!baseUrl.StartsWith("ws://", StringComparison.OrdinalIgnoreCase)
                     && !baseUrl.StartsWith("wss://", StringComparison.OrdinalIgnoreCase))
            {
                error = $"주소 '{baseUrl}' 의 스킴을 알 수 없습니다. " +
                        "http, https, ws, wss 중 하나여야 합니다.";
                return false;
            }

            var path = string.IsNullOrWhiteSpace(streamPath)
                ? "/api/viewer/stream"
                : streamPath.Trim();

            if (!path.StartsWith("/", StringComparison.Ordinal))
            {
                path = "/" + path;
            }

            if (!Uri.TryCreate(baseUrl + path, UriKind.Absolute, out uri))
            {
                error = $"스트림 URI 를 만들 수 없습니다: {baseUrl}{path}";
                return false;
            }

            return true;
        }
    }
}
