using System.Diagnostics;
using Microsoft.Win32;
using MousePointer.Core.Infrastructure;

namespace MousePointer.Core.Services;

public sealed class StartupService
{
    private const string RunPath = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private readonly string _valueName = AppPaths.AppName;

    public bool IsAutoStartEnabled()
    {
        using var key = Registry.CurrentUser.OpenSubKey(RunPath);
        return !string.IsNullOrWhiteSpace(Convert.ToString(key?.GetValue(_valueName)));
    }

    public void SetAutoStart(bool enabled, string executablePath, string arguments = "--background")
    {
        using var key = Registry.CurrentUser.CreateSubKey(RunPath, true);
        if (!enabled)
        {
            key.DeleteValue(_valueName, throwOnMissingValue: false);
            return;
        }

        key.SetValue(_valueName, $"\"{executablePath}\" {arguments}", RegistryValueKind.String);
    }

    public string StartupStatusText()
    {
        using var key = Registry.CurrentUser.OpenSubKey(RunPath);
        var run = Convert.ToString(key?.GetValue(_valueName)) ?? "";
        return string.IsNullOrWhiteSpace(run)
            ? "自启动：未开启"
            : $"自启动：已开启（Run 项：{run}）";
    }

    public void StartDetached(string executablePath, string arguments)
    {
        Process.Start(new ProcessStartInfo
        {
            FileName = executablePath,
            Arguments = arguments,
            UseShellExecute = false,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden
        });
    }
}

