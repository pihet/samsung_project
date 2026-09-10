using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text.RegularExpressions;
using UnityEngine;
using ShipyardTwin.Data;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 책임: 검증된 DTO -> 런타임 모델(ScheduleDataset) 변환 한 단계.
    /// 모든 계약 위반을 문맥 있는 문자열로 누적한 뒤, 하나라도 있으면
    /// SchedulePayloadValidationException 으로 한 번에 던진다.
    ///
    /// 검증 항목:
    ///  - platen_id / block_id: 비어 있지 않음, 중복 없음
    ///  - block.platform_id: 존재하는 정반을 가리킴
    ///  - position: 길이 3, 모든 성분이 유한값
    ///  - status: waiting | in_progress | completed
    ///  - start_time / end_time: 오프셋 명시, 파싱 가능, start &lt; end
    ///  - length / width / height: 0 보다 큼
    /// </summary>
    public static class SchedulePayloadMapper
    {
        // "Z" 또는 "+09:00" / "-05:30" 형태의 오프셋이 문자열 끝에 있어야 한다.
        private static readonly Regex OffsetSuffix =
            new Regex(@"(Z|[+-]\d{2}:\d{2})$", RegexOptions.CultureInvariant);

        public static ScheduleDataset Map(SchedulePayloadDto dto)
        {
            if (dto == null)
            {
                throw new ArgumentNullException(nameof(dto));
            }

            var errors = new List<string>();

            var epoch = ParseTimestamp(dto.ProjectEpoch, "payload.project_epoch", errors)
                        ?? new DateTimeOffset(2018, 1, 1, 0, 0, 0, TimeSpan.FromHours(9));

            var platens = MapPlatens(dto.Platens, errors, out var platenIds);
            var blocks = MapBlocks(dto.Blocks, platenIds, errors);

            if (errors.Count > 0)
            {
                throw new SchedulePayloadValidationException(errors);
            }

            return new ScheduleDataset(dto.Algorithm ?? "unknown", epoch, platens, blocks);
        }

        private static List<PlatenModel> MapPlatens(
            PlatenDto[] dtos, List<string> errors, out HashSet<string> platenIds)
        {
            platenIds = new HashSet<string>();
            var result = new List<PlatenModel>();

            if (dtos == null || dtos.Length == 0)
            {
                errors.Add("platens 배열이 비어 있습니다. 최소 1개의 정반이 필요합니다.");
                return result;
            }

            for (var i = 0; i < dtos.Length; i++)
            {
                var d = dtos[i];
                var ctx = $"platens[{i}]";

                if (d == null)
                {
                    errors.Add($"{ctx}: 항목이 null 입니다.");
                    continue;
                }

                if (string.IsNullOrWhiteSpace(d.PlatenId))
                {
                    errors.Add($"{ctx}: platen_id 가 비어 있습니다.");
                    continue;
                }

                ctx = $"platen '{d.PlatenId}'";

                if (!platenIds.Add(d.PlatenId))
                {
                    errors.Add($"{ctx}: platen_id 가 중복됩니다.");
                    continue;
                }

                var size = ReadSize(d.Length, d.Height, d.Width, ctx, errors);
                var origin = ReadPosition(d.Position, $"{ctx}.position", errors);

                result.Add(new PlatenModel(
                    d.PlatenId,
                    d.PlatenIdx,
                    string.IsNullOrWhiteSpace(d.PlatenName) ? d.PlatenId : d.PlatenName,
                    d.PrimaryArea ?? string.Empty,
                    d.SecondaryArea ?? string.Empty,
                    size,
                    origin,
                    (float)d.CraneCapacityTon,
                    NormalizeBlockType(d.AcceptsBlockType, allowAny: true)));
            }

            return result;
        }

        private static List<BlockModel> MapBlocks(
            BlockDto[] dtos, HashSet<string> platenIds, List<string> errors)
        {
            var result = new List<BlockModel>();
            var blockIds = new HashSet<string>();

            if (dtos == null || dtos.Length == 0)
            {
                errors.Add("blocks 배열이 비어 있습니다. 최소 1개의 블록이 필요합니다.");
                return result;
            }

            for (var i = 0; i < dtos.Length; i++)
            {
                var d = dtos[i];
                var ctx = $"blocks[{i}]";

                if (d == null)
                {
                    errors.Add($"{ctx}: 항목이 null 입니다.");
                    continue;
                }

                if (string.IsNullOrWhiteSpace(d.BlockId))
                {
                    errors.Add($"{ctx}: block_id 가 비어 있습니다.");
                    continue;
                }

                ctx = $"block '{d.BlockId}'";

                if (!blockIds.Add(d.BlockId))
                {
                    errors.Add($"{ctx}: block_id 가 중복됩니다.");
                    continue;
                }

                if (string.IsNullOrWhiteSpace(d.PlatformId))
                {
                    errors.Add($"{ctx}: platform_id 가 비어 있습니다.");
                }
                else if (!platenIds.Contains(d.PlatformId))
                {
                    errors.Add($"{ctx}: platform_id '{d.PlatformId}' 에 해당하는 정반이 없습니다.");
                }

                if (!BlockLifecycleStatusParser.TryParse(d.Status, out var status))
                {
                    errors.Add($"{ctx}: status '{d.Status}' 는 허용되지 않습니다. " +
                               $"허용값: {BlockLifecycleStatusParser.AllowedValues}.");
                }

                var size = ReadSize(d.Length, d.Height, d.Width, ctx, errors);
                var localPos = ReadPosition(d.Position, $"{ctx}.position", errors);

                var start = ParseTimestamp(d.StartTime, $"{ctx}.start_time", errors);
                var end = ParseTimestamp(d.EndTime, $"{ctx}.end_time", errors);
                DateTimeOffset? due = null;
                if (!string.IsNullOrWhiteSpace(d.DueTime))
                {
                    due = ParseTimestamp(d.DueTime, $"{ctx}.due_time", errors);
                }

                if (start.HasValue && end.HasValue && start.Value >= end.Value)
                {
                    errors.Add($"{ctx}: start_time({d.StartTime}) 이 end_time({d.EndTime}) 보다 " +
                               "빠르지 않습니다.");
                }

                // 위에서 이미 오류가 누적된 경우 모델 생성은 건너뛴다(값이 불완전).
                if (start.HasValue && end.HasValue && !string.IsNullOrWhiteSpace(d.PlatformId))
                {
                    result.Add(new BlockModel(
                        d.BlockId,
                        d.SeqId,
                        d.ShipId ?? string.Empty,
                        d.PlatformId,
                        NormalizeBlockType(d.BlockType, allowAny: false),
                        size,
                        localPos,
                        status,
                        start.Value,
                        end.Value,
                        due));
                }
            }

            return result;
        }

        private static Vector3 ReadSize(
            double length, double height, double width, string ctx, List<string> errors)
        {
            if (length <= 0 || width <= 0 || height <= 0)
            {
                errors.Add($"{ctx}: length/width/height 는 모두 0 보다 커야 합니다 " +
                           $"(l={length}, w={width}, h={height}).");
            }

            // X: length, Y: height, Z: width
            return new Vector3((float)length, (float)height, (float)width);
        }

        private static Vector3 ReadPosition(double[] position, string ctx, List<string> errors)
        {
            if (position == null)
            {
                errors.Add($"{ctx}: position 배열이 없습니다. [x, y, z] 3개 값이 필요합니다.");
                return Vector3.zero;
            }

            if (position.Length != 3)
            {
                errors.Add($"{ctx}: position 길이가 {position.Length} 입니다. 정확히 3이어야 합니다.");
                return Vector3.zero;
            }

            for (var i = 0; i < 3; i++)
            {
                if (double.IsNaN(position[i]) || double.IsInfinity(position[i]))
                {
                    errors.Add($"{ctx}[{i}]: 유한한 숫자가 아닙니다 ({position[i]}).");
                    return Vector3.zero;
                }
            }

            return new Vector3((float)position[0], (float)position[1], (float)position[2]);
        }

        private static DateTimeOffset? ParseTimestamp(string raw, string ctx, List<string> errors)
        {
            if (string.IsNullOrWhiteSpace(raw))
            {
                errors.Add($"{ctx}: 시각 문자열이 비어 있습니다.");
                return null;
            }

            if (!OffsetSuffix.IsMatch(raw.Trim()))
            {
                errors.Add($"{ctx}: 타임존 오프셋이 없습니다 ('{raw}'). " +
                           "'Z' 또는 '+09:00' 같은 오프셋을 명시하세요.");
                return null;
            }

            if (!DateTimeOffset.TryParse(
                    raw,
                    CultureInfo.InvariantCulture,
                    DateTimeStyles.RoundtripKind,
                    out var value))
            {
                errors.Add($"{ctx}: ISO-8601 시각으로 파싱할 수 없습니다 ('{raw}').");
                return null;
            }

            return value;
        }

        private static string NormalizeBlockType(string raw, bool allowAny)
        {
            var v = (raw ?? string.Empty).Trim().ToUpperInvariant();
            switch (v)
            {
                case "FLAT":
                case "CURVED":
                    return v;
                case "ANY":
                case "":
                    return allowAny ? "ANY" : "FLAT";
                default:
                    return v; // 알 수 없는 값은 보존한다(색상/필터에서 처리).
            }
        }
    }
}
