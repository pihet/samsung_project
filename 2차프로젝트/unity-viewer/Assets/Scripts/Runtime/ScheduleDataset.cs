using System;
using System.Collections.Generic;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 검증을 통과한 정반·블록 런타임 모델의 집합. id 조회 맵과 시간 범위를 제공한다.
    /// 스폰·색상 갱신·타임라인 클럭이 공통으로 참조하는 읽기 전용 뷰.
    /// </summary>
    public sealed class ScheduleDataset
    {
        public string Algorithm { get; }

        /// <summary>정수 경과일(planned_start_day 등)을 절대 시각으로 되돌릴 기준일.</summary>
        public DateTimeOffset ProjectEpoch { get; }

        public IReadOnlyList<PlatenModel> Platens { get; }
        public IReadOnlyList<BlockModel> Blocks { get; }

        private readonly Dictionary<string, PlatenModel> _platensById;
        private readonly Dictionary<string, BlockModel> _blocksById;

        /// <summary>전체 블록 중 가장 이른 start_time. 블록이 없으면 ProjectEpoch.</summary>
        public DateTimeOffset EarliestStart { get; }

        /// <summary>전체 블록 중 가장 늦은 end_time. 블록이 없으면 ProjectEpoch.</summary>
        public DateTimeOffset LatestEnd { get; }

        public ScheduleDataset(
            string algorithm,
            DateTimeOffset projectEpoch,
            IReadOnlyList<PlatenModel> platens,
            IReadOnlyList<BlockModel> blocks)
        {
            Algorithm = algorithm;
            ProjectEpoch = projectEpoch;
            Platens = platens ?? Array.Empty<PlatenModel>();
            Blocks = blocks ?? Array.Empty<BlockModel>();

            _platensById = new Dictionary<string, PlatenModel>(Platens.Count);
            foreach (var p in Platens)
            {
                _platensById[p.PlatenId] = p;
            }

            _blocksById = new Dictionary<string, BlockModel>(Blocks.Count);
            var earliest = DateTimeOffset.MaxValue;
            var latest = DateTimeOffset.MinValue;
            foreach (var b in Blocks)
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

            EarliestStart = Blocks.Count > 0 ? earliest : projectEpoch;
            LatestEnd = Blocks.Count > 0 ? latest : projectEpoch;
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
