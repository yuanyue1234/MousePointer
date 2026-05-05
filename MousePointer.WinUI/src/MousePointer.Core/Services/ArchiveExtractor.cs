using System.Diagnostics;
using System.IO.Compression;
using MousePointer.Core.Infrastructure;

namespace MousePointer.Core.Services;

public sealed class ArchiveExtractor
{
    private readonly AppPaths _paths;

    public ArchiveExtractor(AppPaths paths)
    {
        _paths = paths;
    }

    public string Extract(string source)
    {
        source = Path.GetFullPath(source);
        if (Directory.Exists(source))
        {
            return source;
        }

        var target = Path.Combine(_paths.AppDataRoot, "imports", $"{NameSanitizer.Sanitize(Path.GetFileNameWithoutExtension(source))}_{DateTimeOffset.Now:yyyyMMddHHmmssfff}");
        if (Directory.Exists(target))
        {
            Directory.Delete(target, recursive: true);
        }

        Directory.CreateDirectory(target);
        var extension = Path.GetExtension(source).ToLowerInvariant();
        switch (extension)
        {
            case ".zip":
                ZipFile.ExtractToDirectory(source, target, overwriteFiles: true);
                return target;
            case ".rar":
                ExtractRar(source, target);
                return target;
            case ".7z":
            case ".exe":
                ExtractWithExternalTool(source, target, extension);
                return target;
            default:
                throw new InvalidOperationException($"不支持的导入文件：{Path.GetFileName(source)}");
        }
    }

    private void ExtractRar(string source, string target)
    {
        var errors = new List<string>();
        foreach (var tool in FindArchiveTools())
        {
            try
            {
                RunTool(tool, ["x", "-y", source, target + Path.DirectorySeparatorChar]);
                return;
            }
            catch (Exception exc)
            {
                errors.Add($"{Path.GetFileName(tool)}: {exc.Message}");
            }
        }

        try
        {
            RunTool("tar", ["-xf", source, "-C", target]);
            return;
        }
        catch (Exception exc)
        {
            errors.Add($"tar: {exc.Message}");
        }

        var text = string.Join(Environment.NewLine, errors);
        if (text.Contains("password", StringComparison.OrdinalIgnoreCase)
            || text.Contains("encrypted", StringComparison.OrdinalIgnoreCase)
            || text.Contains("加密", StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException("暂不支持加密 RAR 压缩包。");
        }

        throw new InvalidOperationException("无法解压 RAR。请确认压缩包未损坏，或把 7z.exe 放入 runtime\\7zip。");
    }

    private void ExtractWithExternalTool(string source, string target, string extension)
    {
        var errors = new List<string>();
        foreach (var tool in FindArchiveTools())
        {
            try
            {
                RunTool(tool, ["x", "-y", source, target + Path.DirectorySeparatorChar]);
                return;
            }
            catch (Exception exc)
            {
                errors.Add($"{Path.GetFileName(tool)}: {exc.Message}");
            }
        }

        try
        {
            RunTool("tar", ["-xf", source, "-C", target]);
            return;
        }
        catch (Exception exc)
        {
            errors.Add($"tar: {exc.Message}");
        }

        throw new InvalidOperationException(extension == ".exe"
            ? "无法解压 EXE。该文件可能不是自解压鼠标包。"
            : $"无法解压 {extension} 压缩包。{string.Join("；", errors)}");
    }

    private IEnumerable<string> FindArchiveTools()
    {
        var local7z = Path.Combine(_paths.AppBaseDirectory, "runtime", "7zip", "7z.exe");
        if (File.Exists(local7z))
        {
            yield return local7z;
        }

        var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
        foreach (var path in new[]
        {
            Path.Combine(programFiles, "7-Zip", "7z.exe"),
            Path.Combine(programFiles, "WinRAR", "WinRAR.exe")
        })
        {
            if (File.Exists(path))
            {
                yield return path;
            }
        }
    }

    private static void RunTool(string fileName, IReadOnlyList<string> arguments)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = fileName,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardError = true,
            RedirectStandardOutput = true
        };
        foreach (var argument in arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        using var process = Process.Start(startInfo) ?? throw new InvalidOperationException($"无法启动 {fileName}");
        process.WaitForExit();
        if (process.ExitCode != 0)
        {
            var output = process.StandardOutput.ReadToEnd();
            var error = process.StandardError.ReadToEnd();
            throw new InvalidOperationException(string.Join(Environment.NewLine, output, error).Trim());
        }
    }
}

