using System.ComponentModel;
using System.Runtime.InteropServices;
using Microsoft.Win32;
using MousePointer.Core.Infrastructure;
using MousePointer.Core.Models;

namespace MousePointer.Core.Services;

public sealed class WindowsCursorService
{
    private const string CursorRegistryPath = @"Control Panel\Cursors";
    private const int SpiSetCursors = 0x0057;
    private const int SpiSetCursorBaseSize = 0x2029;
    private const int SpifUpdateIniFile = 0x01;
    private const int SpifSendChange = 0x02;
    private const int HwndBroadcast = 0xFFFF;
    private const int WmSettingChange = 0x001A;
    private const int SmtoAbortIfHung = 0x0002;

    private readonly AppPaths _paths;
    private readonly SettingsService _settings;

    public WindowsCursorService(AppPaths paths, SettingsService settings)
    {
        _paths = paths;
        _settings = settings;
    }

    public Dictionary<string, string> DefaultCursorSchemeFiles()
    {
        var windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
        var cursors = Path.Combine(windows, "Cursors");
        return CursorRoles.DefaultCursorFiles
            .Select(pair => new KeyValuePair<string, string>(pair.Key, Path.Combine(cursors, pair.Value)))
            .Where(pair => File.Exists(pair.Value))
            .ToDictionary(pair => pair.Key, pair => pair.Value, StringComparer.OrdinalIgnoreCase);
    }

    public int GetCurrentCursorSize()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(CursorRegistryPath);
            return Convert.ToInt32(key?.GetValue("CursorBaseSize") ?? 48);
        }
        catch
        {
            return 48;
        }
    }

    public static int SizeLevelToPixels(int level) => Math.Clamp(level, 1, 15) switch
    {
        1 => 32,
        var value => 32 + (value - 1) * 16
    };

    public static int PixelsToSizeLevel(int pixels)
    {
        if (pixels <= 32)
        {
            return 1;
        }

        if (pixels >= 256)
        {
            return 15;
        }

        return Math.Clamp((int)Math.Round((pixels - 32) / 16.0) + 1, 1, 15);
    }

    public void SetSystemCursorSize(int pixels)
    {
        pixels = Math.Clamp(pixels, 1, 256);
        var level = PixelsToSizeLevel(pixels);
        using (var key = Registry.CurrentUser.CreateSubKey(CursorRegistryPath, true))
        {
            key.SetValue("CursorBaseSize", pixels, RegistryValueKind.DWord);
        }

        using (var key = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Accessibility", true))
        {
            key.SetValue("CursorSize", level, RegistryValueKind.DWord);
        }

        if (!SystemParametersInfo(SpiSetCursorBaseSize, 0, new IntPtr(pixels), SpifUpdateIniFile | SpifSendChange))
        {
            throw new Win32Exception(Marshal.GetLastWin32Error());
        }

        BroadcastChange(CursorRegistryPath);
        BroadcastChange(@"SOFTWARE\Microsoft\Accessibility");
    }

    public void BackupCurrentScheme()
    {
        var values = new Dictionary<string, CursorRegistryValue>(StringComparer.OrdinalIgnoreCase);
        using var key = Registry.CurrentUser.OpenSubKey(CursorRegistryPath);
        if (key is null)
        {
            return;
        }

        foreach (var name in key.GetValueNames())
        {
            values[name] = new CursorRegistryValue
            {
                Value = Convert.ToString(key.GetValue(name)) ?? "",
                Kind = key.GetValueKind(name).ToString()
            };
        }

        JsonFiles.Write(_paths.CursorBackupFile, new CursorBackup
        {
            SavedAt = DateTimeOffset.Now,
            Values = values
        });
    }

    public void RestoreBackup()
    {
        var backup = JsonFiles.Read<CursorBackup>(_paths.CursorBackupFile)
            ?? throw new InvalidOperationException("还没有可恢复的鼠标方案备份。");
        using var key = Registry.CurrentUser.CreateSubKey(CursorRegistryPath, true);
        foreach (var (name, value) in backup.Values)
        {
            var kind = Enum.TryParse<RegistryValueKind>(value.Kind, out var parsed)
                ? parsed
                : RegistryValueKind.ExpandString;
            key.SetValue(name, value.Value, kind);
        }

        RefreshMouseParameters();
    }

    public void ResetToDefaultScheme()
    {
        var defaults = DefaultCursorSchemeFiles();
        if (defaults.Count == 0)
        {
            throw new InvalidOperationException("未找到 Windows 默认鼠标指针文件。");
        }

        ApplyScheme("Windows 默认", defaults, backup: false, cursorSizePixels: null);
    }

    public void ApplyScheme(string themeName, IReadOnlyDictionary<string, string> cursorFiles, bool backup = true, int? cursorSizePixels = null)
    {
        if (backup)
        {
            BackupCurrentScheme();
        }

        if (cursorSizePixels is { } pixels)
        {
            SetSystemCursorSize(pixels);
        }

        var size = cursorSizePixels ?? GetCurrentCursorSize();
        using (var key = Registry.CurrentUser.CreateSubKey(CursorRegistryPath, true))
        {
            key.SetValue("", themeName, RegistryValueKind.String);
            key.SetValue("Scheme Source", 2, RegistryValueKind.DWord);
            key.SetValue("CursorBaseSize", size, RegistryValueKind.DWord);
            foreach (var (registryName, filePath) in cursorFiles)
            {
                if (CursorRoles.ByRegistryName.ContainsKey(registryName) && File.Exists(filePath))
                {
                    key.SetValue(registryName, filePath, RegistryValueKind.ExpandString);
                }
            }
        }

        RefreshMouseParameters();
        _settings.Set("current_scheme", themeName);
    }

    public void RefreshMouseParameters()
    {
        SystemParametersInfo(SpiSetCursors, 0, IntPtr.Zero, SpifUpdateIniFile | SpifSendChange);
        BroadcastChange(CursorRegistryPath);
    }

    private static void BroadcastChange(string area)
    {
        SendMessageTimeout(new IntPtr(HwndBroadcast), WmSettingChange, UIntPtr.Zero, area, SmtoAbortIfHung, 250, out _);
    }

    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool SystemParametersInfo(int action, int parameter, IntPtr value, int flags);

    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern IntPtr SendMessageTimeout(
        IntPtr window,
        int message,
        UIntPtr wParam,
        string lParam,
        int flags,
        int timeout,
        out UIntPtr result);
}

public sealed class CursorBackup
{
    public DateTimeOffset SavedAt { get; set; }
    public Dictionary<string, CursorRegistryValue> Values { get; set; } = new(StringComparer.OrdinalIgnoreCase);
}

public sealed class CursorRegistryValue
{
    public string Value { get; set; } = "";
    public string Kind { get; set; } = RegistryValueKind.ExpandString.ToString();
}

