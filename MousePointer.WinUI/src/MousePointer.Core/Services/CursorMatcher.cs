using System.Text.RegularExpressions;
using MousePointer.Core.Models;

namespace MousePointer.Core.Services;

public sealed partial class CursorMatcher
{
    private static readonly IReadOnlyList<(string RegistryName, string[] Keywords)> Rules =
    [
        ("Hand", ["hand", "link", "pointer_hand", "pointerhand", "pointing_hand", "pointinghand", "手指", "链接", "链接选择"]),
        ("NWPen", ["pen", "nwpen", "handwriting", "ink", "hand_write", "手写"]),
        ("Crosshair", ["cross", "crosshair", "precision", "precise", "precision_select", "precisionselect", "十字", "精确选择"]),
        ("Pin", ["pin", "location", "locate", "position", "geo", "地图", "位置", "位置选择"]),
        ("Person", ["person", "people", "user", "contact", "individual", "个人", "个人选择"]),
        ("Arrow", ["arrow", "normal", "default", "left_ptr", "leftptr", "pointer_default", "正常选择"]),
        ("Help", ["help", "question", "help_select", "helpsel", "帮助选择"]),
        ("AppStarting", ["appstarting", "app_starting", "working", "starting", "后台运行"]),
        ("Wait", ["busy", "wait", "waiting", "忙", "等待"]),
        ("IBeam", ["beam", "ibeam", "text", "text_select", "textselect", "文本", "文本选择"]),
        ("No", ["no", "unavailable", "forbidden", "blocked", "禁用", "不可用"]),
        ("SizeNS", ["sizens", "size_ns", "vert", "vertical", "上下"]),
        ("SizeWE", ["sizewe", "size_we", "horiz", "horizontal", "左右"]),
        ("SizeNWSE", ["nwse", "size_nwse"]),
        ("SizeNESW", ["nesw", "size_nesw"]),
        ("SizeAll", ["all", "move", "sizeall", "move_cursor", "移动"]),
        ("UpArrow", ["up", "uparrow", "alternate", "up_arrow", "向上"])
    ];

    public Dictionary<string, string> MapFilesToRoles(IEnumerable<string> files)
    {
        var candidates = files
            .Where(CursorRoles.IsCursorFile)
            .Select(Path.GetFullPath)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();

        var mapping = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var used = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var (registryName, keywords) in Rules)
        {
            var match = candidates.FirstOrDefault(path => !used.Contains(path) && NameMatches(path, keywords));
            if (match is null)
            {
                continue;
            }

            mapping[registryName] = match;
            used.Add(match);
        }

        var numbered = candidates
            .Where(path => DigitsOnly().IsMatch(Path.GetFileNameWithoutExtension(path)))
            .ToDictionary(path => Path.GetFileNameWithoutExtension(path), path => path, StringComparer.OrdinalIgnoreCase);

        for (var index = 0; index < CursorRoles.All.Count; index++)
        {
            var key = $"{index + 1:00}";
            var role = CursorRoles.All[index];
            if (!mapping.ContainsKey(role.RegistryName) && numbered.TryGetValue(key, out var path) && !used.Contains(path))
            {
                mapping[role.RegistryName] = path;
                used.Add(path);
            }
        }

        return mapping;
    }

    private static bool NameMatches(string path, IReadOnlyCollection<string> keywords)
    {
        var name = Normalize(Path.GetFileNameWithoutExtension(path));
        var full = Normalize(Path.GetFileName(path));
        return keywords.Any(keyword =>
        {
            var normalized = Normalize(keyword);
            return name == normalized
                || full == normalized
                || Tokens(name).Contains(normalized)
                || name.Contains($"_{normalized}", StringComparison.Ordinal)
                || name.Contains($"{normalized}_", StringComparison.Ordinal)
                || name.Contains($"-{normalized}", StringComparison.Ordinal)
                || name.Contains($"{normalized}-", StringComparison.Ordinal)
                || (ContainsNonAscii(normalized) && name.Contains(normalized, StringComparison.Ordinal))
                || (normalized.Length >= 5 && name.Contains(normalized, StringComparison.Ordinal));
        });
    }

    private static string Normalize(string value)
    {
        return value
            .Trim()
            .Replace(' ', '_')
            .Replace('-', '_')
            .ToLowerInvariant();
    }

    private static HashSet<string> Tokens(string value)
    {
        return value.Split(['_', '-', '.', ' '], StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .ToHashSet(StringComparer.Ordinal);
    }

    private static bool ContainsNonAscii(string value) => value.Any(ch => ch > 127);

    [GeneratedRegex(@"^\d+$")]
    private static partial Regex DigitsOnly();
}
