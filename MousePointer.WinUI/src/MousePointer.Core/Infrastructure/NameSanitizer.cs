using System.Text.RegularExpressions;

namespace MousePointer.Core.Infrastructure;

public static partial class NameSanitizer
{
    public static string Sanitize(string name)
    {
        var trimmed = (name ?? string.Empty).Trim();
        trimmed = InvalidFileNameChars().Replace(trimmed, "_");
        trimmed = Whitespace().Replace(trimmed, " ");
        return string.IsNullOrWhiteSpace(trimmed) ? "未命名方案" : trimmed;
    }

    [GeneratedRegex(@"[<>:""/\\|?*\x00-\x1F]")]
    private static partial Regex InvalidFileNameChars();

    [GeneratedRegex(@"\s+")]
    private static partial Regex Whitespace();
}

