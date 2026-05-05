using System.Drawing;
using System.Drawing.Imaging;
using MousePointer.Core.Models;

namespace MousePointer.Core.Services;

public static class PreviewExporter
{
    public static string ExportContactSheet(string outputDirectory, string themeName, IReadOnlyDictionary<CursorRole, string> files)
    {
        Directory.CreateDirectory(outputDirectory);
        var width = 980;
        var rowHeight = 64;
        var height = Math.Max(160, 64 + files.Count * rowHeight);
        using var bitmap = new Bitmap(width, height, PixelFormat.Format32bppArgb);
        using var graphics = Graphics.FromImage(bitmap);
        graphics.Clear(Color.White);
        using var titleFont = new Font("Microsoft YaHei UI", 18, FontStyle.Bold);
        using var bodyFont = new Font("Microsoft YaHei UI", 10, FontStyle.Regular);
        using var subtleBrush = new SolidBrush(Color.FromArgb(90, 100, 116));
        using var textBrush = new SolidBrush(Color.FromArgb(17, 24, 39));
        graphics.DrawString(themeName, titleFont, textBrush, 24, 18);
        graphics.DrawString($"导出时间：{DateTime.Now:yyyy-MM-dd HH:mm:ss}", bodyFont, subtleBrush, 24, 46);

        var y = 82;
        foreach (var (role, path) in files)
        {
            graphics.DrawRectangle(Pens.LightGray, 24, y, width - 48, rowHeight - 10);
            graphics.DrawString(role.Label, bodyFont, textBrush, 42, y + 10);
            graphics.DrawString(Path.GetFileName(path), bodyFont, subtleBrush, 210, y + 10);
            graphics.DrawString(Path.GetExtension(path).Equals(".ani", StringComparison.OrdinalIgnoreCase) ? "动" : "静", bodyFont, subtleBrush, width - 80, y + 10);
            y += rowHeight;
        }

        var output = Path.Combine(outputDirectory, $"{SanitizeForFile(themeName)}_预览.gif");
        bitmap.Save(output, ImageFormat.Gif);
        return output;
    }

    private static string SanitizeForFile(string name)
    {
        foreach (var ch in Path.GetInvalidFileNameChars())
        {
            name = name.Replace(ch, '_');
        }

        return string.IsNullOrWhiteSpace(name) ? "鼠标方案" : name;
    }
}

