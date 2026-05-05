using MousePointer.Core.Infrastructure;
using MousePointer.Core.Models;

namespace MousePointer.Core.Services;

public sealed class ScheduleService
{
    private readonly AppPaths _paths;
    private readonly SettingsService _settings;
    private readonly CursorSchemeStore _schemes;
    private readonly Random _random = new();

    public ScheduleService(AppPaths paths, SettingsService settings, CursorSchemeStore schemes)
    {
        _paths = paths;
        _settings = settings;
        _schemes = schemes;
    }

    public List<ScheduleItem> LoadSchedule()
    {
        return JsonFiles.Read<List<ScheduleItem>>(_paths.ScheduleFile) ?? [];
    }

    public Dictionary<string, string> LoadWeekSchedule()
    {
        return JsonFiles.Read<Dictionary<string, string>>(_paths.WeekScheduleFile)
            ?? new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
    }

    public void SaveSchedule(IReadOnlyList<ScheduleItem> items) => JsonFiles.Write(_paths.ScheduleFile, items);

    public void SaveWeekSchedule(Dictionary<string, string> items) => JsonFiles.Write(_paths.WeekScheduleFile, items);

    public string PickScheduledScheme(ScheduleItem item)
    {
        var all = _schemes.GetSchemeNames().ToList();
        var selected = item.SelectedSchemes.Where(all.Contains).ToList();
        var names = selected.Count > 0 ? selected : all;
        if (names.Count == 0)
        {
            return "";
        }

        if (item.Scheme == CursorRoles.RandomSchemeValue || item.Order == "随机")
        {
            return names[_random.Next(names.Count)];
        }

        if (item.Scheme == "顺序" || item.Order == "顺序")
        {
            item.SequentialIndex = (item.SequentialIndex + 1) % names.Count;
            SaveSchedule(LoadSchedule().Select(existing =>
            {
                if (existing.Mode == item.Mode && existing.IntervalSeconds == item.IntervalSeconds)
                {
                    existing.SequentialIndex = item.SequentialIndex;
                }

                return existing;
            }).ToList());
            return names[item.SequentialIndex];
        }

        return names.Contains(item.Scheme) ? item.Scheme : "";
    }

    public string NextSwitchText()
    {
        var now = DateTimeOffset.Now;
        var candidates = new List<(DateTimeOffset Time, string Scheme)>();
        foreach (var item in LoadSchedule())
        {
            if (item.Mode == "timer")
            {
                if (item.IntervalSeconds > 0)
                {
                    var scheme = item.SelectedSchemes.Count > 0
                        ? $"{item.Order} {item.SelectedSchemes.Count} 个方案"
                        : item.Scheme;
                    candidates.Add((now.AddSeconds(item.IntervalSeconds), scheme));
                }

                continue;
            }

            if (TimeOnly.TryParse(item.Time, out var time) && !string.IsNullOrWhiteSpace(item.Scheme))
            {
                var target = new DateTimeOffset(now.Year, now.Month, now.Day, time.Hour, time.Minute, 0, now.Offset);
                if (target <= now)
                {
                    target = target.AddDays(1);
                }

                candidates.Add((target, item.Scheme));
            }
        }

        var week = LoadWeekSchedule();
        for (var offset = 0; offset < 7; offset++)
        {
            var day = ((int)DateTimeOffset.Now.DayOfWeek + 6 + offset) % 7;
            if (!week.TryGetValue(day.ToString(), out var scheme) || string.IsNullOrWhiteSpace(scheme))
            {
                continue;
            }

            var target = now.Date.AddDays(offset);
            if (target <= now)
            {
                target = target.AddDays(7);
            }

            candidates.Add((target, scheme));
        }

        if (candidates.Count == 0)
        {
            return "";
        }

        var next = candidates.MinBy(item => item.Time);
        return $"{next.Time:MM-dd HH:mm} {next.Scheme}";
    }

    public SwitchStatus GetStatus() => new(_settings.CurrentScheme, NextSwitchText());
}

