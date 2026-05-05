namespace MousePointer.Core.Tests;

internal sealed class TempDirectory : IDisposable
{
    public TempDirectory()
    {
        Path = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"MousePointerTests_{Guid.NewGuid():N}");
        Directory.CreateDirectory(Path);
    }

    public string Path { get; }

    public string File(string name)
    {
        var path = System.IO.Path.Combine(Path, name);
        System.IO.File.WriteAllBytes(path, [0, 0, 2, 0]);
        return path;
    }

    public void Dispose()
    {
        if (Directory.Exists(Path))
        {
            Directory.Delete(Path, recursive: true);
        }
    }
}

