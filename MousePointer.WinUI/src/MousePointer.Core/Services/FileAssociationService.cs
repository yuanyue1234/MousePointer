using Microsoft.Win32;

namespace MousePointer.Core.Services;

public sealed class FileAssociationService
{
    public const string SettingKey = "cursor_file_association_enabled";
    private const string CurProgId = "MousePointer.CursorFile";
    private const string AniProgId = "MousePointer.AnimatedCursorFile";

    public void Apply(bool enabled, string executablePath)
    {
        if (enabled)
        {
            Register(".cur", CurProgId, "Windows 光标文件", executablePath);
            Register(".ani", AniProgId, "Windows 动态光标文件", executablePath);
        }
        else
        {
            Unregister(".cur", CurProgId);
            Unregister(".ani", AniProgId);
        }
    }

    private static void Register(string extension, string progId, string description, string executablePath)
    {
        using (var ext = Registry.CurrentUser.CreateSubKey($@"Software\Classes\{extension}", true))
        {
            var current = Convert.ToString(ext.GetValue(""));
            if (!string.IsNullOrWhiteSpace(current) && !current.Equals(progId, StringComparison.OrdinalIgnoreCase))
            {
                ext.SetValue("MousePointer.Backup", current);
            }

            ext.SetValue("", progId);
        }

        using var command = Registry.CurrentUser.CreateSubKey($@"Software\Classes\{progId}\shell\open\command", true);
        command.SetValue("", $"\"{executablePath}\" --preview \"%1\"");
        using var root = Registry.CurrentUser.CreateSubKey($@"Software\Classes\{progId}", true);
        root.SetValue("", description);
    }

    private static void Unregister(string extension, string progId)
    {
        using (var ext = Registry.CurrentUser.CreateSubKey($@"Software\Classes\{extension}", true))
        {
            var current = Convert.ToString(ext.GetValue(""));
            if (current?.Equals(progId, StringComparison.OrdinalIgnoreCase) == true)
            {
                var backup = Convert.ToString(ext.GetValue("MousePointer.Backup"));
                if (!string.IsNullOrWhiteSpace(backup))
                {
                    ext.SetValue("", backup);
                    ext.DeleteValue("MousePointer.Backup", throwOnMissingValue: false);
                }
                else
                {
                    ext.DeleteValue("", throwOnMissingValue: false);
                }
            }
        }

        Registry.CurrentUser.DeleteSubKeyTree($@"Software\Classes\{progId}", throwOnMissingSubKey: false);
    }
}

