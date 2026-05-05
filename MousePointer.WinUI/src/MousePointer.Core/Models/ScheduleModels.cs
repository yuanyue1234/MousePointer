namespace MousePointer.Core.Models;

public sealed class ScheduleItem
{
    public string Mode { get; set; } = "timer";
    public string Time { get; set; } = "";
    public string Scheme { get; set; } = "";
    public int IntervalSeconds { get; set; }
    public string Order { get; set; } = "顺序";
    public int SequentialIndex { get; set; }
    public DateTimeOffset? LastRunAt { get; set; }
    public List<string> SelectedSchemes { get; set; } = [];
}

public sealed record SwitchStatus(string CurrentScheme, string NextSwitchText);

