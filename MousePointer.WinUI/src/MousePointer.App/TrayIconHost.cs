using System.Runtime.InteropServices;

namespace MousePointer.App;

public sealed class TrayIconHost : IDisposable
{
    private const int WindowMessageTray = 0x8000 + 42;
    private const int WmCommand = 0x0111;
    private const int WmLButtonDoubleClick = 0x0203;
    private const int WmRButtonUp = 0x0205;
    private const int NimAdd = 0x00000000;
    private const int NimDelete = 0x00000002;
    private const int NifMessage = 0x00000001;
    private const int NifIcon = 0x00000002;
    private const int NifTip = 0x00000004;
    private const int MfString = 0x00000000;
    private const int TpmRightButton = 0x0002;
    private const int TpmBottomAlign = 0x0020;
    private const int IdOpen = 1001;
    private const int IdExit = 1002;

    private readonly WndProcDelegate _wndProc;
    private readonly string _className = $"MousePointerTray_{Guid.NewGuid():N}";
    private IntPtr _windowHandle;
    private bool _disposed;

    public TrayIconHost()
    {
        _wndProc = WndProc;
        RegisterWindowClass();
        _windowHandle = CreateWindowEx(0, _className, _className, 0, 0, 0, 0, 0, IntPtr.Zero, IntPtr.Zero, GetModuleHandle(null), IntPtr.Zero);
        if (_windowHandle == IntPtr.Zero)
        {
            throw new InvalidOperationException("无法创建托盘消息窗口。");
        }

        AddIcon();
    }

    public event Action? OpenRequested;
    public event Action? ExitRequested;

    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        RemoveIcon();
        if (_windowHandle != IntPtr.Zero)
        {
            DestroyWindow(_windowHandle);
            _windowHandle = IntPtr.Zero;
        }

        _disposed = true;
    }

    private void RegisterWindowClass()
    {
        var wndClass = new WndClassEx
        {
            CbSize = (uint)Marshal.SizeOf<WndClassEx>(),
            LpfnWndProc = _wndProc,
            HInstance = GetModuleHandle(null),
            LpszClassName = _className
        };
        RegisterClassEx(ref wndClass);
    }

    private void AddIcon()
    {
        var data = NotifyIconData.Create(_windowHandle, "鼠标指针配置管理器");
        data.HIcon = LoadIcon(IntPtr.Zero, new IntPtr(32512));
        ShellNotifyIcon(NimAdd, ref data);
    }

    private void RemoveIcon()
    {
        if (_windowHandle == IntPtr.Zero)
        {
            return;
        }

        var data = NotifyIconData.Create(_windowHandle, "鼠标指针配置管理器");
        ShellNotifyIcon(NimDelete, ref data);
    }

    private IntPtr WndProc(IntPtr hwnd, uint message, UIntPtr wParam, IntPtr lParam)
    {
        if (message == WindowMessageTray)
        {
            var mouseMessage = lParam.ToInt32();
            if (mouseMessage == WmLButtonDoubleClick)
            {
                OpenRequested?.Invoke();
                return IntPtr.Zero;
            }

            if (mouseMessage == WmRButtonUp)
            {
                ShowMenu();
                return IntPtr.Zero;
            }
        }

        if (message == WmCommand)
        {
            var command = unchecked((int)wParam.ToUInt32() & 0xFFFF);
            if (command == IdOpen)
            {
                OpenRequested?.Invoke();
                return IntPtr.Zero;
            }

            if (command == IdExit)
            {
                ExitRequested?.Invoke();
                return IntPtr.Zero;
            }
        }

        return DefWindowProc(hwnd, message, wParam, lParam);
    }

    private void ShowMenu()
    {
        var menu = CreatePopupMenu();
        AppendMenu(menu, MfString, new UIntPtr(IdOpen), "打开");
        AppendMenu(menu, MfString, new UIntPtr(IdExit), "退出");
        GetCursorPos(out var point);
        SetForegroundWindow(_windowHandle);
        TrackPopupMenu(menu, TpmRightButton | TpmBottomAlign, point.X, point.Y, 0, _windowHandle, IntPtr.Zero);
        DestroyMenu(menu);
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct NotifyIconData
    {
        public uint CbSize;
        public IntPtr HWnd;
        public uint UId;
        public uint UFlags;
        public uint UCallbackMessage;
        public IntPtr HIcon;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
        public string SzTip;

        public static NotifyIconData Create(IntPtr windowHandle, string tip)
        {
            return new NotifyIconData
            {
                CbSize = (uint)Marshal.SizeOf<NotifyIconData>(),
                HWnd = windowHandle,
                UId = 1,
                UFlags = NifMessage | NifIcon | NifTip,
                UCallbackMessage = WindowMessageTray,
                SzTip = tip
            };
        }
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct WndClassEx
    {
        public uint CbSize;
        public uint Style;
        public WndProcDelegate LpfnWndProc;
        public int CbClsExtra;
        public int CbWndExtra;
        public IntPtr HInstance;
        public IntPtr HIcon;
        public IntPtr HCursor;
        public IntPtr HbrBackground;
        public string? LpszMenuName;
        public string LpszClassName;
        public IntPtr HIconSm;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct Point
    {
        public int X;
        public int Y;
    }

    private delegate IntPtr WndProcDelegate(IntPtr hwnd, uint message, UIntPtr wParam, IntPtr lParam);

    [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
    private static extern bool ShellNotifyIcon(int message, ref NotifyIconData data);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern ushort RegisterClassEx(ref WndClassEx wndClass);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr CreateWindowEx(int exStyle, string className, string windowName, int style, int x, int y, int width, int height, IntPtr parent, IntPtr menu, IntPtr instance, IntPtr param);

    [DllImport("user32.dll")]
    private static extern bool DestroyWindow(IntPtr hwnd);

    [DllImport("user32.dll")]
    private static extern IntPtr DefWindowProc(IntPtr hwnd, uint message, UIntPtr wParam, IntPtr lParam);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr GetModuleHandle(string? moduleName);

    [DllImport("user32.dll")]
    private static extern IntPtr LoadIcon(IntPtr instance, IntPtr iconName);

    [DllImport("user32.dll")]
    private static extern IntPtr CreatePopupMenu();

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern bool AppendMenu(IntPtr menu, int flags, UIntPtr idNewItem, string newItem);

    [DllImport("user32.dll")]
    private static extern bool DestroyMenu(IntPtr menu);

    [DllImport("user32.dll")]
    private static extern bool GetCursorPos(out Point point);

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr hwnd);

    [DllImport("user32.dll")]
    private static extern bool TrackPopupMenu(IntPtr menu, int flags, int x, int y, int reserved, IntPtr hwnd, IntPtr rectangle);
}

