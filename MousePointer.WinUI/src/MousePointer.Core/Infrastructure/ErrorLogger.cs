using System.Text;

namespace MousePointer.Core.Infrastructure;

public sealed class ErrorLogger
{
    private const long MaxBytes = 2 * 1024 * 1024;
    private readonly string _path;

    public ErrorLogger(AppPaths paths)
    {
        _path = paths.ErrorLogFile;
    }

    public void Log(string title, Exception exception) => Log(title, exception.ToString());

    public void Log(string title, string detail)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(_path)!);
        RotateIfNeeded();
        var builder = new StringBuilder()
            .AppendLine()
            .Append("## ")
            .Append(DateTimeOffset.Now.ToString("yyyy-MM-dd HH:mm:ss"))
            .Append(' ')
            .AppendLine(title)
            .AppendLine()
            .AppendLine("```text")
            .AppendLine(detail)
            .AppendLine("```");
        File.AppendAllText(_path, builder.ToString(), Encoding.UTF8);
    }

    private void RotateIfNeeded()
    {
        var file = new FileInfo(_path);
        if (!file.Exists || file.Length < MaxBytes)
        {
            return;
        }

        var archive = Path.Combine(file.DirectoryName!, $"错误记录_{DateTimeOffset.Now:yyyyMMdd_HHmmss}.txt");
        File.Move(_path, archive, overwrite: true);
        foreach (var old in Directory.EnumerateFiles(file.DirectoryName!, "错误记录_*.txt")
                     .Select(path => new FileInfo(path))
                     .OrderByDescending(info => info.LastWriteTimeUtc)
                     .Skip(5))
        {
            old.Delete();
        }
    }
}

