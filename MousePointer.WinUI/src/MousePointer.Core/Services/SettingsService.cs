using MousePointer.Core.Infrastructure;

namespace MousePointer.Core.Services;

public sealed class SettingsService
{
    private readonly AppPaths _paths;

    public SettingsService(AppPaths paths)
    {
        _paths = paths;
    }

    public Dictionary<string, string> Load()
    {
        return JsonFiles.Read<Dictionary<string, string>>(_paths.SettingsFile)
            ?? new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
    }

    public void Save(Dictionary<string, string> settings) => JsonFiles.Write(_paths.SettingsFile, settings);

    public string StorageRoot
    {
        get
        {
            var settings = Load();
            return settings.TryGetValue("storage_root", out var root) && !string.IsNullOrWhiteSpace(root)
                ? root
                : _paths.DefaultStorageRoot;
        }
    }

    public string OutputRoot
    {
        get
        {
            var settings = Load();
            return settings.TryGetValue("output_root", out var root) && !string.IsNullOrWhiteSpace(root)
                ? root
                : _paths.DefaultOutputRoot;
        }
    }

    public string GithubUrl
    {
        get
        {
            var settings = Load();
            return settings.TryGetValue("github_url", out var url) && !string.IsNullOrWhiteSpace(url)
                ? url
                : AppPaths.DefaultGithubUrl;
        }
    }

    public string CurrentScheme
    {
        get
        {
            var settings = Load();
            return settings.TryGetValue("current_scheme", out var value) ? value : "";
        }
    }

    public bool IsEnabled(string key, bool defaultValue = false)
    {
        var settings = Load();
        return settings.TryGetValue(key, out var value)
            ? value is "1" || value.Equals("true", StringComparison.OrdinalIgnoreCase)
            : defaultValue;
    }

    public void Set(string key, string value)
    {
        var settings = Load();
        settings[key] = value;
        Save(settings);
    }

    public void SetEnabled(string key, bool enabled) => Set(key, enabled ? "1" : "0");
}

