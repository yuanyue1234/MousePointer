namespace MousePointer.Core.Models;

public sealed class CursorSchemeManifest
{
    public string Name { get; set; } = "";
    public DateTimeOffset SavedAt { get; set; } = DateTimeOffset.Now;
    public Dictionary<string, string> Files { get; set; } = new(StringComparer.OrdinalIgnoreCase);
    public int? CursorSizePixels { get; set; }
}

