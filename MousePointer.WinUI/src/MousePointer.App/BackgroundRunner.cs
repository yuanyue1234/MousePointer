using Microsoft.UI.Dispatching;
using Microsoft.UI.Xaml;
using MousePointer.Core.Models;
using MousePointer.Core.Services;

namespace MousePointer.App;

public sealed class BackgroundRunner : IDisposable
{
    private readonly AppServices _services = new();
    private readonly DispatcherQueue _dispatcher;
    private readonly CancellationTokenSource _cancellation = new();
    private TrayIconHost? _trayIcon;
    private string _lastKey = "";

    public BackgroundRunner(DispatcherQueue dispatcher)
    {
        _dispatcher = dispatcher;
    }

    public void Start(bool tray)
    {
        if (tray)
        {
            CreateTrayIcon();
        }

        _ = Task.Run(() => RunLoopAsync(_cancellation.Token));
    }

    public void Dispose()
    {
        _cancellation.Cancel();
        _trayIcon?.Dispose();
        _cancellation.Dispose();
    }

    private async Task RunLoopAsync(CancellationToken cancellationToken)
    {
        while (!cancellationToken.IsCancellationRequested)
        {
            var fast = false;
            try
            {
                fast = Tick();
            }
            catch (Exception exc)
            {
                _services.Logger.Log("后台切换失败", exc);
            }

            await Task.Delay(fast ? TimeSpan.FromSeconds(1) : TimeSpan.FromSeconds(30), cancellationToken).ConfigureAwait(false);
        }
    }

    private bool Tick()
    {
        var now = DateTimeOffset.Now;
        var schedule = _services.Schedule.LoadSchedule();
        var hasTimer = false;
        foreach (var item in schedule)
        {
            if (item.Mode == "timer")
            {
                hasTimer = true;
                if (item.IntervalSeconds <= 0)
                {
                    continue;
                }

                if (item.LastRunAt is null || now - item.LastRunAt >= TimeSpan.FromSeconds(item.IntervalSeconds))
                {
                    var scheme = _services.Schedule.PickScheduledScheme(item);
                    item.LastRunAt = now;
                    if (!string.IsNullOrWhiteSpace(scheme))
                    {
                        ApplyLibraryScheme(scheme);
                    }
                }

                continue;
            }

            var key = $"{now:yyyy-MM-dd}|{item.Time}|{item.Scheme}";
            if (item.Time == now.ToString("HH:mm") && key != _lastKey)
            {
                var scheme = item.Scheme == CursorRoles.RandomSchemeValue ? _services.Schedule.PickScheduledScheme(item) : item.Scheme;
                if (!string.IsNullOrWhiteSpace(scheme))
                {
                    ApplyLibraryScheme(scheme);
                    _lastKey = key;
                }
            }
        }

        _services.Schedule.SaveSchedule(schedule);

        var week = _services.Schedule.LoadWeekSchedule();
        var day = ((int)now.DayOfWeek + 6) % 7;
        if (week.TryGetValue(day.ToString(), out var weekScheme) && !string.IsNullOrWhiteSpace(weekScheme))
        {
            var key = $"{now:yyyy-MM-dd}|week|{weekScheme}";
            if (key != _lastKey)
            {
                ApplyLibraryScheme(weekScheme);
                _lastKey = key;
            }
        }

        return hasTimer;
    }

    private void ApplyLibraryScheme(string scheme)
    {
        var files = _services.Schemes.ResolveFiles(scheme);
        _services.Cursors.ApplyScheme(scheme, files, backup: true, cursorSizePixels: null);
    }

    private void CreateTrayIcon()
    {
        _trayIcon = new TrayIconHost();
        _trayIcon.OpenRequested += () => _dispatcher.TryEnqueue(OpenWindow);
        _trayIcon.ExitRequested += () => _dispatcher.TryEnqueue(() =>
        {
            Dispose();
            Application.Current.Exit();
        });
    }

    private static void OpenWindow()
    {
        if (App.MainAppWindow is null)
        {
            App.MainAppWindow = new MainWindow();
        }

        App.MainAppWindow.Activate();
    }
}
