using System.Diagnostics;
using System.Text;
using MousePointer.Core.Infrastructure;

namespace MousePointer.Core.Services;

public sealed class InstallerPackageBuilder
{
    private readonly AppPaths _paths;

    public InstallerPackageBuilder(AppPaths paths)
    {
        _paths = paths;
    }

    public async Task<string> BuildAsync(string themeName, IReadOnlyDictionary<string, string> cursorFiles, int cursorSizePixels, string outputDirectory, CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(outputDirectory);
        var work = Path.Combine(_paths.AppDataRoot, "installer_build", $"{NameSanitizer.Sanitize(themeName)}_{DateTimeOffset.Now:yyyyMMddHHmmss}");
        Directory.CreateDirectory(work);

        var project = Path.Combine(work, "MouseThemeInstaller.csproj");
        var program = Path.Combine(work, "Program.cs");
        await File.WriteAllTextAsync(project, ProjectSource(), cancellationToken).ConfigureAwait(false);
        await File.WriteAllTextAsync(program, ProgramSource(themeName, cursorFiles, cursorSizePixels), Encoding.UTF8, cancellationToken).ConfigureAwait(false);

        var result = await RunDotnetAsync(
            "publish",
            project,
            "-c",
            "Release",
            "-r",
            "win-x64",
            "-o",
            outputDirectory,
            "-p:PublishSingleFile=true",
            "-p:SelfContained=false",
            cancellationToken).ConfigureAwait(false);

        if (result.ExitCode != 0)
        {
            var log = Path.Combine(outputDirectory, "installer_build_error.log");
            await File.WriteAllTextAsync(log, result.Output, Encoding.UTF8, cancellationToken).ConfigureAwait(false);
            throw new InvalidOperationException($"安装包生成失败，详情见：{log}");
        }

        var exe = Directory.EnumerateFiles(outputDirectory, "MouseThemeInstaller.exe").FirstOrDefault();
        if (exe is null)
        {
            throw new FileNotFoundException("安装包生成完成，但没有找到输出 exe。");
        }

        var finalPath = Path.Combine(outputDirectory, $"{NameSanitizer.Sanitize(themeName)}_鼠标样式安装器.exe");
        File.Move(exe, finalPath, overwrite: true);
        return finalPath;
    }

    private static string ProjectSource()
    {
        return """
               <Project Sdk="Microsoft.NET.Sdk">
                 <PropertyGroup>
                   <OutputType>WinExe</OutputType>
                   <TargetFramework>net9.0-windows10.0.19041.0</TargetFramework>
                   <UseWindowsForms>false</UseWindowsForms>
                   <ImplicitUsings>enable</ImplicitUsings>
                   <Nullable>enable</Nullable>
                   <AssemblyName>MouseThemeInstaller</AssemblyName>
                 </PropertyGroup>
               </Project>
               """;
    }

    private static string ProgramSource(string themeName, IReadOnlyDictionary<string, string> cursorFiles, int cursorSizePixels)
    {
        var assets = cursorFiles.ToDictionary(
            pair => pair.Key,
            pair => new EmbeddedAsset(Path.GetFileName(pair.Value), Convert.ToBase64String(File.ReadAllBytes(pair.Value))));

        var assetSource = string.Join("," + Environment.NewLine, assets.Select(pair =>
            $"""            ["{Escape(pair.Key)}"] = new EmbeddedAsset("{Escape(pair.Value.FileName)}", "{pair.Value.Base64}")"""));

        return $$"""
                 using Microsoft.Win32;
                 using System.Runtime.InteropServices;

                 const string themeName = "{{Escape(themeName)}}";
                 const int cursorSizePixels = {{cursorSizePixels}};
                 var assets = new Dictionary<string, EmbeddedAsset>(StringComparer.OrdinalIgnoreCase)
                 {
                 {{assetSource}}
                 };

                 var target = Path.Combine(
                     Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                     "MouseCursorThemeBuilder",
                     "mouse_files",
                     "installed",
                     themeName);
                 Directory.CreateDirectory(target);
                 var files = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                 foreach (var (registryName, asset) in assets)
                 {
                     var path = Path.Combine(target, asset.FileName);
                     File.WriteAllBytes(path, Convert.FromBase64String(asset.Base64));
                     files[registryName] = path;
                 }

                 using (var key = Registry.CurrentUser.CreateSubKey(@"Control Panel\Cursors", true))
                 {
                     key.SetValue("", themeName, RegistryValueKind.String);
                     key.SetValue("Scheme Source", 2, RegistryValueKind.DWord);
                     key.SetValue("CursorBaseSize", cursorSizePixels, RegistryValueKind.DWord);
                     foreach (var (registryName, path) in files)
                     {
                         key.SetValue(registryName, path, RegistryValueKind.ExpandString);
                     }
                 }

                 SystemParametersInfo(0x2029, 0, new IntPtr(cursorSizePixels), 0x01 | 0x02);
                 SystemParametersInfo(0x0057, 0, IntPtr.Zero, 0x01 | 0x02);
                 SendMessageTimeout(new IntPtr(0xFFFF), 0x001A, UIntPtr.Zero, @"Control Panel\Cursors", 0x0002, 1000, out _);

                 [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
                 static extern bool SystemParametersInfo(int action, int parameter, IntPtr value, int flags);

                 [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
                 static extern IntPtr SendMessageTimeout(IntPtr window, int message, UIntPtr wParam, string lParam, int flags, int timeout, out UIntPtr result);

                 sealed record EmbeddedAsset(string FileName, string Base64);
                 """;
    }

    private static async Task<(int ExitCode, string Output)> RunDotnetAsync(params object[] values)
    {
        var cancellationToken = values.OfType<CancellationToken>().FirstOrDefault();
        var arguments = values.Where(value => value is not CancellationToken).Select(Convert.ToString).Where(value => value is not null).Cast<string>().ToArray();
        var startInfo = new ProcessStartInfo
        {
            FileName = "dotnet",
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardError = true,
            RedirectStandardOutput = true
        };
        foreach (var argument in arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        using var process = Process.Start(startInfo) ?? throw new InvalidOperationException("无法启动 dotnet。");
        var outputTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var errorTask = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        var output = await outputTask.ConfigureAwait(false) + Environment.NewLine + await errorTask.ConfigureAwait(false);
        return (process.ExitCode, output);
    }

    private static string Escape(string value) => value.Replace("\\", "\\\\").Replace("\"", "\\\"");

    private sealed record EmbeddedAsset(string FileName, string Base64);
}

