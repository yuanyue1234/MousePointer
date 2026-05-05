namespace MousePointer.Core.Models;

public sealed record CursorRole(
    string Label,
    string RegistryName,
    string FileStem,
    double HotspotXRatio,
    double HotspotYRatio,
    string Tip);

