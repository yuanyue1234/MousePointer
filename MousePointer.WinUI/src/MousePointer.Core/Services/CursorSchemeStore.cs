using MousePointer.Core.Infrastructure;
using MousePointer.Core.Models;

namespace MousePointer.Core.Services;

public sealed class CursorSchemeStore
{
    private readonly SettingsService _settings;
    private readonly ArchiveExtractor _extractor;
    private readonly InfSchemeParser _parser;

    public CursorSchemeStore(SettingsService settings, ArchiveExtractor extractor, InfSchemeParser parser)
    {
        _settings = settings;
        _extractor = extractor;
        _parser = parser;
    }

    public string StorageRoot => _settings.StorageRoot;
    public string SchemeLibrary => Path.Combine(StorageRoot, "schemes");
    public string ResourceLibrary => Path.Combine(StorageRoot, "resources");
    public string InstalledLibrary => Path.Combine(StorageRoot, "installed");

    public IReadOnlyList<string> GetSchemeNames()
    {
        if (!Directory.Exists(SchemeLibrary))
        {
            return [];
        }

        return Directory.EnumerateDirectories(SchemeLibrary)
            .Where(path => File.Exists(Path.Combine(path, "scheme.json")))
            .OrderBy(path => Directory.GetLastWriteTimeUtc(path))
            .Select(Path.GetFileName)
            .Where(name => !string.IsNullOrWhiteSpace(name))
            .Cast<string>()
            .ToList();
    }

    public CursorSchemeManifest Load(string name)
    {
        var path = ManifestPath(name);
        return JsonFiles.Read<CursorSchemeManifest>(path)
            ?? throw new FileNotFoundException($"方案不存在：{name}", path);
    }

    public string SchemeDirectory(string name) => Path.Combine(SchemeLibrary, NameSanitizer.Sanitize(name));

    public string ManifestPath(string name) => Path.Combine(SchemeDirectory(name), "scheme.json");

    public Dictionary<string, string> ResolveFiles(string name)
    {
        var manifest = Load(name);
        var schemeDirectory = SchemeDirectory(name);
        return manifest.Files.ToDictionary(
            pair => pair.Key,
            pair => Path.GetFullPath(Path.Combine(schemeDirectory, pair.Value)),
            StringComparer.OrdinalIgnoreCase);
    }

    public CursorSchemeManifest Save(string name, IReadOnlyDictionary<string, string> files, int? cursorSizePixels = null)
    {
        name = NameSanitizer.Sanitize(name);
        var schemeDirectory = SchemeDirectory(name);
        Directory.CreateDirectory(schemeDirectory);

        var stored = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var (registryName, source) in files)
        {
            if (!CursorRoles.ByRegistryName.TryGetValue(registryName, out var role) || !File.Exists(source))
            {
                continue;
            }

            var extension = Path.GetExtension(source).ToLowerInvariant();
            var outputName = $"{role.FileStem}{extension}";
            var output = Path.Combine(schemeDirectory, outputName);
            File.Copy(source, output, overwrite: true);
            stored[registryName] = outputName;
        }

        var manifest = new CursorSchemeManifest
        {
            Name = name,
            SavedAt = DateTimeOffset.Now,
            Files = stored,
            CursorSizePixels = cursorSizePixels
        };
        JsonFiles.Write(ManifestPath(name), manifest);
        return manifest;
    }

    public IReadOnlyList<ImportResult> ImportPackage(string source)
    {
        var extracted = _extractor.Extract(source);
        var parsed = _parser.ParseAll(extracted);
        var results = new List<ImportResult>();
        var baseName = NameSanitizer.Sanitize(Path.GetFileNameWithoutExtension(source));

        foreach (var scheme in parsed)
        {
            var name = parsed.Count == 1
                ? baseName
                : $"{baseName}_{scheme.Name}";
            name = UniqueSchemeName(name);
            Save(name, scheme.Files);
            results.Add(new ImportResult(name, scheme.Files.Count));
        }

        return results;
    }

    public void Rename(string oldName, string newName)
    {
        oldName = NameSanitizer.Sanitize(oldName);
        newName = UniqueSchemeName(newName);
        Directory.Move(SchemeDirectory(oldName), SchemeDirectory(newName));
        var manifest = Load(newName);
        manifest.Name = newName;
        JsonFiles.Write(ManifestPath(newName), manifest);
    }

    public void Delete(string name)
    {
        var directory = SchemeDirectory(name);
        if (Directory.Exists(directory))
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    public string UniqueSchemeName(string requested)
    {
        var name = NameSanitizer.Sanitize(requested);
        if (!Directory.Exists(SchemeDirectory(name)))
        {
            return name;
        }

        for (var index = 2; index < 1000; index++)
        {
            var candidate = $"{name}_{index}";
            if (!Directory.Exists(SchemeDirectory(candidate)))
            {
                return candidate;
            }
        }

        return $"{name}_{Guid.NewGuid():N}";
    }
}

public sealed record ImportResult(string SchemeName, int RoleCount);

