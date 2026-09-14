using System;
using System.Collections.Generic;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 검증을 통과한 정반·블록 런타임 모델의 집합. id 조회 맵과 시간 범위를 제공한다.
    /// 스폰·색상 갱신·타임라인 클럭이 공통으로 참조한다.
    ///
    /// 정반 집합은 불변이다(야드는 런타임에 바뀌지 않는다).
    /// 블록만 <see cref="TryAddBlock"/> 로 증분 추가할 수 있다. WebSocket 으로 들어오는
    /// 긴급 배정 블록을 최초 스냅샷 위에 얹기 위한 경로이며, 메인 스레드에서만 호출해야 한다.
    /// </summary>
    public sealed class ScheduleDataset
    {
        public string Algorithm { get; }

        /// <summary>정수 경과일(planned_start_day 등)을 절대 시각으로 되돌릴 기준일.</summary>
        public DateTimeOffset ProjectEpoch { get; }

        public IReadOnlyList<PlatenModel> Platens { get; }
        public IReadOnlyList<BlockModel> Blocks => _blocks;

        private readonly List<BlockModel> _blocks;
        private readonly Dictionary<string, PlatenModel> _platensById;
        private readonly Dictionary<string, BlockModel> _blocksById;

        /// <summary>전체 블록 중 가장 이른 start_time. 블록이 없으면 ProjectEpoch.</summary>
        public DateTimeOffset EarliestStart { get; private set; }

        /// <summary>전체 블록 중 가장 늦은 end_time. 블록이 없으면 ProjectEpoch.</summary>
        public DateTimeOffset LatestEnd { get; private set; }

        public ScheduleDataset(
            string algorithm,
            DateTimeOffset projectEpoch,
            IReadOnlyList<PlatenModel> platens,
            IReadOnlyList<BlockModel> blocks)
        {
            Algorithm = algorithm;
            ProjectEpoch = projectEpoch;
            Platens = platens ?? Array.Empty<PlatenModel>();
            _blocks = blocks != null
                ? new List<BlockModel>(blocks)
                : new List<BlockModel>();

            _platensById = new Dictionary<string, PlatenModel>(Platens.Count);
            foreach (var p in Platens)
            {
                _platensById[p.PlatenId] = p;
            }

            _blocksById = new Dictionary<string, BlockModel>(_blocks.Count);
            var earliest = DateTimeOffset.MaxValue;
            var latest = DateTimeOffset.MinValue;
            foreach (var b in _blocks)
            {
                _blocksById[b.BlockId] = b;
                if (b.StartTime < earliest)
                {
                    earliest = b.StartTime;
                }

                if (b.EndTime > latest)
                {
                    latest = b.EndTime;
                }
            }

            EarliestStart = _blocks.Count > 0 ? earliest : projectEpoch;
            LatestEnd = _blocks.Count > 0 ? latest : projectEpoch;
        }

        /// <summary>
        /// 런타임 증분 추가. 같은 block_id 가 이미 있으면 아무것도 하지 않고 false 를 돌려준다
        /// (계약의 "block_id 중복 불가"를 증분 경로에서도 지킨다).
        /// 시간 범위는 추가된 블록까지 포함하도록 넓힌다.
        /// </summary>
        public bool TryAddBlock(BlockModel block)
        {
            if (block == null || _blocksById.ContainsKey(block.BlockId))
            {
                return false;
            }

            _blocks.Add(block);
            _blocksById[block.BlockId] = block;

            if (_blocks.Count == 1 || block.StartTime < EarliestStart)
            {
                EarliestStart = block.StartTime;
            }

            if (_blocks.Count == 1 || block.EndTime > LatestEnd)
            {
                LatestEnd = block.EndTime;
            }

            return true;
        }

        public bool TryGetPlaten(string platenId, out PlatenModel platen)
        {
            return _platensById.TryGetValue(platenId, out platen);
        }

        public bool TryGetBlock(string blockId, out BlockModel block)
        {
            return _blocksById.TryGetValue(blockId, out block);
        }
    }
}
