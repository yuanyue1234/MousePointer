using System.Text;
using System.Text.RegularExpressions;
using MousePointer.Core.Infrastructure;
using MousePointer.Core.Models;

namespace MousePointer.Core.Services;

public sealed partial class InfSchemeParser
{
    private readonly CursorMatcher _matcher;

    private static readonly IReadOnlyDictionary<string, string> AliasToRegistryName =
        new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["arrow"] = "Arrow",
            ["normal"] = "Arrow",
            ["default"] = "Arrow",
            ["left_ptr"] = "Arrow",
            ["help"] = "Help",
            ["helpsel"] = "Help",
            ["work"] = "AppStarting",
            ["appstarting"] = "AppStarting",
            ["app_starting"] = "AppStarting",
            ["busy"] = "Wait",
            ["wait"] = "Wait",
            ["cross"] = "Crosshair",
            ["crosshair"] = "Crosshair",
            ["precision"] = "Crosshair",
            ["text"] = "IBeam",
            ["ibeam"] = "IBeam",
            ["beam"] = "IBeam",
            ["hand"] = "Hand",
            ["link"] = "Hand",
            ["pointerhand"] = "Hand",
            ["pointer_hand"] = "Hand",
            ["pen"] = "NWPen",
            ["nwpen"] = "NWPen",
            ["handwriting"] = "NWPen",
            ["ink"] = "NWPen",
            ["unavailable"] = "No",
            ["unavailiable"] = "No",
            ["no"] = "No",
            ["vert"] = "SizeNS",
            ["sizens"] = "SizeNS",
            ["horz"] = "SizeWE",
            ["horiz"] = "SizeWE",
            ["sizewe"] = "SizeWE",
            ["dgn1"] = "SizeNWSE",
            ["dgn2"] = "SizeNESW",
            ["move"] = "SizeAll",
            ["alternate"] = "UpArrow",
            ["up"] = "UpArrow",
            ["pin"] = "Pin",
            ["location"] = "Pin",
            ["position"] = "Pin",
            ["person"] = "Person",
            ["user"] = "Person"
        };

    public InfSchemeParser(CursorMatcher matcher)
    {
        _matcher = matcher;
    }

    public IReadOnlyList<ParsedCursorScheme> ParseAll(string rootDirectory)
    {
        var files = Directory.EnumerateFiles(rootDirectory, "*", SearchOption.AllDirectories)
            .Where(CursorRoles.IsCursorFile)
            .ToList();

        var infs = Directory.EnumerateFiles(rootDirectory, "*.inf", SearchOption.AllDirectories).ToList();
        if (infs.Count == 0)
        {
            var mapping = _matcher.MapFilesToRoles(files);
            return mapping.Count == 0
                ? []
                : [new ParsedCursorScheme(NameSanitizer.Sanitize(new DirectoryInfo(rootDirectory).Name), mapping)];
        }

        var parsed = new List<ParsedCursorScheme>();
        foreach (var inf in infs)
        {
            var mapping = ParseInf(inf, files);
            if (mapping.Count > 0)
            {
                parsed.Add(new ParsedCursorScheme(NameSanitizer.Sanitize(Path.GetFileNameWithoutExtension(inf)), mapping));
            }
        }

        if (parsed.Count == 0)
        {
            var mapping = _matcher.MapFilesToRoles(files);
            if (mapping.Count > 0)
            {
                parsed.Add(new ParsedCursorScheme(NameSanitizer.Sanitize(new DirectoryInfo(rootDirectory).Name), mapping));
            }
        }

        return parsed;
    }

    private Dictionary<string, string> ParseInf(string infPath, IReadOnlyCollection<string> files)
    {
        var text = DecodeInf(infPath);
        var byName = files.ToDictionary(path => Path.GetFileName(path)!, path => path, StringComparer.OrdinalIgnoreCase);
        var mapping = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        foreach (var (alias, registryName) in AliasToRegistryName)
        {
            var match = Regex.Match(text, $@"^\s*{Regex.Escape(alias)}\s*=\s*""?([^""\r\n]+)""?", RegexOptions.IgnoreCase | RegexOptions.Multiline);
            if (match.Success && byName.TryGetValue(Path.GetFileName(match.Groups[1].Value.Trim()), out var path))
            {
                mapping[registryName] = path;
            }
        }

        foreach (var role in CursorRoles.All)
        {
            var match = Regex.Match(
                text,
                $@"HKCU,\s*""Control Panel\\Cursors"",\s*{Regex.Escape(role.RegistryName)}\s*,[^,]*,\s*""?([^""\r\n]+)""?",
                RegexOptions.IgnoreCase);
            if (!match.Success)
            {
                continue;
            }

            var raw = ResolveInfValue(text, match.Groups[1].Value.Trim());
            if (byName.TryGetValue(Path.GetFileName(raw), out var path))
            {
                mapping[role.RegistryName] = path;
            }
        }

        foreach (var (registryName, path) in _matcher.MapFilesToRoles(files))
        {
            mapping.TryAdd(registryName, path);
        }

        return mapping;
    }

    private static string ResolveInfValue(string text, string value)
    {
        var variable = Regex.Match(value, @".*%([^%]+)%");
        if (!variable.Success)
        {
            return value;
        }

        var match = Regex.Match(text, $@"^\s*{Regex.Escape(variable.Groups[1].Value)}\s*=\s*""?([^""\r\n]+)""?", RegexOptions.IgnoreCase | RegexOptions.Multiline);
        return match.Success ? match.Groups[1].Value.Trim() : value;
    }

    private static string DecodeInf(string path)
    {
        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
        var bytes = File.ReadAllBytes(path);
        foreach (var encoding in new[] { Encoding.Unicode, new UTF8Encoding(true), Encoding.GetEncoding("gbk"), Encoding.GetEncoding(936), Encoding.Latin1 })
        {
            try
            {
                var text = encoding.GetString(bytes);
                if (text.Contains("Cursors", StringComparison.OrdinalIgnoreCase)
                    || text.Contains("Control Panel", StringComparison.OrdinalIgnoreCase)
                    || text.Contains("[Strings]", StringComparison.OrdinalIgnoreCase))
                {
                    return text;
                }
            }
            catch (DecoderFallbackException)
            {
            }
        }

        return Encoding.UTF8.GetString(bytes);
    }
}

public sealed record ParsedCursorScheme(string Name, Dictionary<string, string> Files);
