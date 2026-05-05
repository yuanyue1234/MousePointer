namespace MousePointer.Core.Models;

public static class CursorRoles
{
    public const string RandomSchemeValue = "__random__";

    public static readonly IReadOnlyList<CursorRole> All =
    [
        new("正常选择", "Arrow", "arrow", 0.02, 0.02, "普通箭头"),
        new("帮助选择", "Help", "help", 0.02, 0.02, "帮助提示"),
        new("后台运行", "AppStarting", "app_starting", 0.02, 0.02, "后台运行"),
        new("忙", "Wait", "wait", 0.50, 0.50, "系统忙碌"),
        new("精确选择", "Crosshair", "crosshair", 0.50, 0.50, "准星"),
        new("文本选择", "IBeam", "ibeam", 0.50, 0.50, "文本输入"),
        new("手写", "NWPen", "nw_pen", 0.05, 0.95, "手写笔"),
        new("不可用", "No", "no", 0.50, 0.50, "禁止"),
        new("垂直调整大小", "SizeNS", "size_ns", 0.50, 0.50, "上下拖动"),
        new("水平调整大小", "SizeWE", "size_we", 0.50, 0.50, "左右拖动"),
        new("沿对角线调整大小 1", "SizeNWSE", "size_nwse", 0.50, 0.50, "左上右下"),
        new("沿对角线调整大小 2", "SizeNESW", "size_nesw", 0.50, 0.50, "右上左下"),
        new("移动", "SizeAll", "size_all", 0.50, 0.50, "四向移动"),
        new("候选", "UpArrow", "up_arrow", 0.50, 0.02, "候选选择"),
        new("链接选择", "Hand", "hand", 0.25, 0.02, "链接"),
        new("位置选择", "Pin", "pin", 0.50, 0.50, "位置"),
        new("个人选择", "Person", "person", 0.50, 0.50, "个人")
    ];

    public static readonly IReadOnlyDictionary<string, CursorRole> ByRegistryName =
        All.ToDictionary(role => role.RegistryName, StringComparer.OrdinalIgnoreCase);

    public static readonly IReadOnlyDictionary<string, string> DefaultCursorFiles =
        new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["Arrow"] = "aero_arrow.cur",
            ["Help"] = "aero_helpsel.cur",
            ["AppStarting"] = "aero_working.ani",
            ["Wait"] = "aero_busy.ani",
            ["Crosshair"] = "cross_r.cur",
            ["IBeam"] = "beam_r.cur",
            ["NWPen"] = "aero_pen.cur",
            ["No"] = "aero_unavail.cur",
            ["SizeNS"] = "aero_ns.cur",
            ["SizeWE"] = "aero_ew.cur",
            ["SizeNWSE"] = "aero_nwse.cur",
            ["SizeNESW"] = "aero_nesw.cur",
            ["SizeAll"] = "aero_move.cur",
            ["UpArrow"] = "aero_up.cur",
            ["Hand"] = "aero_link.cur",
            ["Person"] = "aero_person.cur",
            ["Pin"] = "aero_pin.cur"
        };

    public static bool IsCursorFile(string path)
    {
        var extension = Path.GetExtension(path);
        return extension.Equals(".cur", StringComparison.OrdinalIgnoreCase)
            || extension.Equals(".ani", StringComparison.OrdinalIgnoreCase);
    }

    public static bool IsImageFile(string path)
    {
        var extension = Path.GetExtension(path);
        return extension.Equals(".png", StringComparison.OrdinalIgnoreCase)
            || extension.Equals(".jpg", StringComparison.OrdinalIgnoreCase)
            || extension.Equals(".jpeg", StringComparison.OrdinalIgnoreCase)
            || extension.Equals(".bmp", StringComparison.OrdinalIgnoreCase)
            || extension.Equals(".gif", StringComparison.OrdinalIgnoreCase)
            || extension.Equals(".webp", StringComparison.OrdinalIgnoreCase)
            || extension.Equals(".ico", StringComparison.OrdinalIgnoreCase);
    }

    public static bool IsImportPackage(string path)
    {
        var extension = Path.GetExtension(path);
        return extension.Equals(".zip", StringComparison.OrdinalIgnoreCase)
            || extension.Equals(".rar", StringComparison.OrdinalIgnoreCase)
            || extension.Equals(".7z", StringComparison.OrdinalIgnoreCase)
            || extension.Equals(".exe", StringComparison.OrdinalIgnoreCase);
    }
}

