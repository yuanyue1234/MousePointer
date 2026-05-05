namespace MousePointer.Core.Infrastructure;

public sealed class AppPaths
{
    public const string AppName = "鼠标指针配置管理器";
    public const string AppVersion = "3.0.0-winui";
    public const string ResourceUrl = "http://8.135.33.2:5002/";
    public const string DefaultGithubUrl = "https://github.com/yuanyue1234/MousePointer";
    public const string Mission = "让新手小白也能用，让鼠标指针制作者能方便编辑和生成。";

    public AppPaths(string appBaseDirectory)
    {
        AppBaseDirectory = appBaseDirectory;
        AppDataRoot = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "MouseCursorThemeBuilder");
        DefaultStorageRoot = Path.Combine(AppDataRoot, "mouse_files");
        DefaultOutputRoot = Path.Combine(AppDataRoot, "installers");
        SettingsFile = Path.Combine(AppDataRoot, "settings.json");
        ScheduleFile = Path.Combine(AppDataRoot, "schedule.json");
        WeekScheduleFile = Path.Combine(AppDataRoot, "week_schedule.json");
        CursorBackupFile = Path.Combine(AppDataRoot, "cursor_backup.json");
        ErrorLogFile = Path.Combine(AppBaseDirectory, "错误记录.txt");
    }

    public string AppBaseDirectory { get; }
    public string AppDataRoot { get; }
    public string DefaultStorageRoot { get; }
    public string DefaultOutputRoot { get; }
    public string SettingsFile { get; }
    public string ScheduleFile { get; }
    public string WeekScheduleFile { get; }
    public string CursorBackupFile { get; }
    public string ErrorLogFile { get; }

    public static AppPaths CreateDefault()
    {
        var baseDirectory = AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        return new AppPaths(baseDirectory);
    }
}

