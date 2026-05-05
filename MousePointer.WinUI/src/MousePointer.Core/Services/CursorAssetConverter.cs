using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using MousePointer.Core.Models;

namespace MousePointer.Core.Services;

public static class CursorAssetConverter
{
    public static string PrepareCursorAsset(string source, string targetDirectory, CursorRole role, int sizePixels)
    {
        Directory.CreateDirectory(targetDirectory);
        var extension = Path.GetExtension(source).ToLowerInvariant();
        if (extension is ".cur" or ".ani")
        {
            var output = Path.Combine(targetDirectory, $"{role.FileStem}{extension}");
            File.Copy(source, output, overwrite: true);
            return output;
        }

        if (!CursorRoles.IsImageFile(source))
        {
            throw new InvalidOperationException($"不支持的鼠标素材：{Path.GetFileName(source)}");
        }

        var cursorPath = Path.Combine(targetDirectory, $"{role.FileStem}.cur");
        WritePngCursor(source, cursorPath, role, sizePixels);
        return cursorPath;
    }

    public static void WritePngCursor(string sourceImage, string outputCursor, CursorRole role, int sizePixels)
    {
        sizePixels = Math.Clamp(sizePixels, 16, 256);
        using var image = Image.FromFile(sourceImage);
        using var canvas = new Bitmap(sizePixels, sizePixels, PixelFormat.Format32bppArgb);
        using (var graphics = Graphics.FromImage(canvas))
        {
            graphics.Clear(Color.Transparent);
            graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
            graphics.SmoothingMode = SmoothingMode.HighQuality;
            graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;

            var scale = Math.Min((double)sizePixels / image.Width, (double)sizePixels / image.Height);
            var width = Math.Max(1, (int)Math.Round(image.Width * scale));
            var height = Math.Max(1, (int)Math.Round(image.Height * scale));
            var x = (sizePixels - width) / 2;
            var y = (sizePixels - height) / 2;
            graphics.DrawImage(image, x, y, width, height);
        }

        using var png = new MemoryStream();
        canvas.Save(png, ImageFormat.Png);
        var pngBytes = png.ToArray();

        using var file = File.Create(outputCursor);
        using var writer = new BinaryWriter(file);
        writer.Write((ushort)0); // reserved
        writer.Write((ushort)2); // cursor
        writer.Write((ushort)1);
        writer.Write((byte)(sizePixels >= 256 ? 0 : sizePixels));
        writer.Write((byte)(sizePixels >= 256 ? 0 : sizePixels));
        writer.Write((byte)0);
        writer.Write((byte)0);
        writer.Write((ushort)Math.Clamp((int)Math.Round(sizePixels * role.HotspotXRatio), 0, sizePixels - 1));
        writer.Write((ushort)Math.Clamp((int)Math.Round(sizePixels * role.HotspotYRatio), 0, sizePixels - 1));
        writer.Write((uint)pngBytes.Length);
        writer.Write((uint)22);
        writer.Write(pngBytes);
    }
}

