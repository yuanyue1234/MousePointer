using System.Collections.ObjectModel;
using System.Diagnostics;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using MousePointer.App.ViewModels;
using MousePointer.Core.Infrastructure;
using MousePointer.Core.Models;
using MousePointer.Core.Services;
using Windows.ApplicationModel.DataTransfer;
using Windows.Storage.Pickers;
using WinRT.Interop;

namespace MousePointer.App;

public sealed partial class MainPage : Page
{
    private readonly AppServices _services = new();
    private readonly ObservableCollection<CursorRoleRowViewModel> _rows = [];
    private readonly ObservableCollection<SchemeItemViewModel> _resources = [];
    private readonly Dictionary<string, CursorRoleRowViewModel> _rowsByRegistryName = new(StringComparer.OrdinalIgnoreCase);
    private int _sizeLevel;
    private bool _loadingScheme;

    public MainPage()
    {
        InitializeComponent();
        RoleList.ItemsSource = _rows;
        ResourceList.ItemsSource = _resources;
        Loaded += MainPage_Loaded;
    }

    private void MainPage_Loaded(object sender, RoutedEventArgs e)
    {
        InitializeRows();
        LoadSettingsToUi();
        RefreshSchemes();
        _sizeLevel = WindowsCursorService.PixelsToSizeLevel(_services.Cursors.GetCurrentCursorSize());
        UpdateSizeUi();
        RefreshStatus();
        StatusText.Text = "选择或拖入素材。未选择的鼠标状态不会被修改。";
    }

    private void InitializeRows()
    {
        _rows.Clear();
        _rowsByRegistryName.Clear();
        foreach (var role in CursorRoles.All)
        {
            var row = new CursorRoleRowViewModel(role);
            _rows.Add(row);
            _rowsByRegistryName[role.RegistryName] = row;
        }
    }

    private void LoadSettingsToUi()
    {
        var settings = _services.Settings.Load();
        StoragePathBox.Text = _services.Settings.StorageRoot;
        OutputPathBox.Text = _services.Settings.OutputRoot;
        GithubUrlBox.Text = _services.Settings.GithubUrl;
        AutoStartSwitch.IsOn = _services.Startup.IsAutoStartEnabled();
        HideTaskbarSwitch.IsOn = settings.TryGetValue("hide_taskbar_icon", out var hide) && hide == "1";
        FileAssociationSwitch.IsOn = _services.Settings.IsEnabled(FileAssociationService.SettingKey);
        RefreshDiagnostics();
    }

    private void RefreshSchemes()
    {
        Directory.CreateDirectory(_services.Schemes.SchemeLibrary);
        var names = _services.Schemes.GetSchemeNames().ToList();
        SchemeCombo.ItemsSource = names;
        FixedSchemeBox.ItemsSource = names;
        TimerSchemeList.ItemsSource = names;
        foreach (var box in WeekBoxes())
        {
            box.ItemsSource = new[] { "" }.Concat(names).ToList();
        }

        if (SchemeCombo.SelectedItem is null && names.Count > 0)
        {
            SchemeCombo.SelectedIndex = 0;
        }

        RefreshResources();
    }

    private void RefreshResources()
    {
        _resources.Clear();
        foreach (var name in _services.Schemes.GetSchemeNames())
        {
            try
            {
                _resources.Add(new SchemeItemViewModel(name, _services.Schemes.Load(name).Files.Count));
            }
            catch (Exception exc)
            {
                _services.Logger.Log("加载资源卡片失败", exc);
            }
        }
    }

    private void SchemeCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_loadingScheme || SchemeCombo.SelectedItem is not string name)
        {
            return;
        }

        LoadScheme(name);
    }

    private void LoadScheme(string name)
    {
        try
        {
            _loadingScheme = true;
            foreach (var row in _rows)
            {
                row.FilePath = "";
            }

            var files = _services.Schemes.ResolveFiles(name);
            foreach (var (registryName, path) in files)
            {
                if (_rowsByRegistryName.TryGetValue(registryName, out var row))
                {
                    row.FilePath = path;
                }
            }

            StatusText.Text = $"已载入方案：{name}";
        }
        catch (Exception exc)
        {
            _services.Logger.Log("载入方案失败", exc);
            StatusText.Text = exc.Message;
        }
        finally
        {
            _loadingScheme = false;
        }
    }

    private async void PickRole_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string registryName } && _rowsByRegistryName.TryGetValue(registryName, out var row))
        {
            var path = await PickCursorOrImageAsync();
            if (!string.IsNullOrWhiteSpace(path))
            {
                row.FilePath = path;
                UpdatePreview(row);
            }
        }
    }

    private void ClearRole_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string registryName } && _rowsByRegistryName.TryGetValue(registryName, out var row))
        {
            row.FilePath = "";
            UpdatePreview(row);
        }
    }

    private void RoleList_ItemClick(object sender, ItemClickEventArgs e)
    {
        if (e.ClickedItem is CursorRoleRowViewModel row)
        {
            UpdatePreview(row);
        }
    }

    private void UpdatePreview(CursorRoleRowViewModel row)
    {
        PreviewRoleText.Text = row.Label;
        PreviewPathText.Text = string.IsNullOrWhiteSpace(row.FilePath) ? "未选择" : row.FilePath;
    }

    private async void ImportPackage_Click(object sender, RoutedEventArgs e)
    {
        var path = await PickImportPackageAsync();
        if (string.IsNullOrWhiteSpace(path))
        {
            return;
        }

        await RunUiTaskAsync("导入资源包", () =>
        {
            var results = _services.Schemes.ImportPackage(path);
            return string.Join("，", results.Select(result => $"{result.SchemeName}（{result.RoleCount}项）"));
        }, result =>
        {
            RefreshSchemes();
            StatusText.Text = $"已导入：{result}";
        });
    }

    private async void ImportFolder_Click(object sender, RoutedEventArgs e)
    {
        var folder = await PickFolderAsync();
        if (string.IsNullOrWhiteSpace(folder))
        {
            return;
        }

        await RunUiTaskAsync("导入文件夹", () =>
        {
            var parsed = _services.Parser.ParseAll(folder);
            foreach (var scheme in parsed)
            {
                _services.Schemes.Save(_services.Schemes.UniqueSchemeName(scheme.Name), scheme.Files);
            }

            return $"{parsed.Count} 个方案";
        }, result =>
        {
            RefreshSchemes();
            StatusText.Text = $"已导入：{result}";
        });
    }

    private async void NewScheme_Click(object sender, RoutedEventArgs e)
    {
        var name = await AskTextAsync("新建方案", "方案名称", "新方案");
        if (string.IsNullOrWhiteSpace(name))
        {
            return;
        }

        var unique = _services.Schemes.UniqueSchemeName(name);
        _services.Schemes.Save(unique, new Dictionary<string, string>());
        RefreshSchemes();
        SchemeCombo.SelectedItem = unique;
    }

    private async void RenameScheme_Click(object sender, RoutedEventArgs e)
    {
        if (SchemeCombo.SelectedItem is not string oldName)
        {
            return;
        }

        var name = await AskTextAsync("重命名方案", "新名称", oldName);
        if (string.IsNullOrWhiteSpace(name) || name == oldName)
        {
            return;
        }

        try
        {
            _services.Schemes.Rename(oldName, name);
            RefreshSchemes();
            SchemeCombo.SelectedItem = NameSanitizer.Sanitize(name);
        }
        catch (Exception exc)
        {
            await ShowErrorAsync("重命名失败", exc);
        }
    }

    private async void DeleteScheme_Click(object sender, RoutedEventArgs e)
    {
        if (SchemeCombo.SelectedItem is not string name)
        {
            return;
        }

        var dialog = new ContentDialog
        {
            XamlRoot = XamlRoot,
            Title = "删除方案",
            Content = $"确定删除“{name}”吗？",
            PrimaryButtonText = "删除",
            CloseButtonText = "取消"
        };
        if (await dialog.ShowAsync() == ContentDialogResult.Primary)
        {
            _services.Schemes.Delete(name);
            RefreshSchemes();
            InitializeRows();
        }
    }

    private async void ApplyScheme_Click(object sender, RoutedEventArgs e)
    {
        await RunUiTaskAsync("应用方案", () =>
        {
            var theme = CurrentThemeName();
            var prepared = PrepareSelectedFiles(theme);
            if (prepared.Count == 0)
            {
                throw new InvalidOperationException("请至少选择一个鼠标素材。");
            }

            _services.Schemes.Save(theme, prepared, CurrentCursorPixels());
            var resolved = _services.Schemes.ResolveFiles(theme);
            _services.Cursors.ApplyScheme(theme, resolved, backup: true, CurrentCursorPixels());
            return theme;
        }, theme =>
        {
            RefreshSchemes();
            RefreshStatus();
            StatusText.Text = $"已应用：{theme}";
        });
    }

    private async void BuildInstaller_Click(object sender, RoutedEventArgs e)
    {
        await RunUiTaskAsync("生成安装包", () =>
        {
            var theme = CurrentThemeName();
            var prepared = PrepareSelectedFiles(theme);
            if (prepared.Count == 0)
            {
                throw new InvalidOperationException("请至少选择一个鼠标素材。");
            }

            _services.Schemes.Save(theme, prepared, CurrentCursorPixels());
            var resolved = _services.Schemes.ResolveFiles(theme);
            return _services.InstallerBuilder.BuildAsync(theme, resolved, CurrentCursorPixels(), _services.Settings.OutputRoot).GetAwaiter().GetResult();
        }, path =>
        {
            StatusText.Text = $"已生成安装包：{path}";
            OpenFolder(Path.GetDirectoryName(path)!);
        });
    }

    private async void ExportPreview_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var files = _rows
                .Where(row => !string.IsNullOrWhiteSpace(row.FilePath))
                .ToDictionary(row => row.Role, row => row.FilePath);
            if (files.Count == 0)
            {
                StatusText.Text = "没有可导出的鼠标素材。";
                return;
            }

            var output = PreviewExporter.ExportContactSheet(_services.Settings.OutputRoot, CurrentThemeName(), files);
            StatusText.Text = $"已导出预览：{output}";
            OpenFolder(Path.GetDirectoryName(output)!);
        }
        catch (Exception exc)
        {
            await ShowErrorAsync("截图导出失败", exc);
        }
    }

    private void ClearAll_Click(object sender, RoutedEventArgs e)
    {
        foreach (var row in _rows)
        {
            row.FilePath = "";
        }

        StatusText.Text = "已清空选择。";
    }

    private async void AddReplacement_Click(object sender, RoutedEventArgs e)
    {
        var row = RoleList.SelectedItem as CursorRoleRowViewModel ?? _rows.FirstOrDefault();
        if (row is null)
        {
            return;
        }

        var path = await PickCursorOrImageAsync();
        if (!string.IsNullOrWhiteSpace(path))
        {
            row.FilePath = path;
            UpdatePreview(row);
        }
    }

    private void MoveSelectedBack_Click(object sender, RoutedEventArgs e)
    {
        if (RoleList.SelectedItem is CursorRoleRowViewModel row)
        {
            row.FilePath = "";
            UpdatePreview(row);
            StatusText.Text = $"已移回：{row.Label}";
        }
    }

    private void SizeMinus_Click(object sender, RoutedEventArgs e)
    {
        _sizeLevel = Math.Max(1, _sizeLevel - 1);
        UpdateSizeUi(applyLive: LiveSizeSwitch.IsOn);
    }

    private void SizePlus_Click(object sender, RoutedEventArgs e)
    {
        _sizeLevel = Math.Min(15, _sizeLevel + 1);
        UpdateSizeUi(applyLive: LiveSizeSwitch.IsOn);
    }

    private void LiveSizeSwitch_Toggled(object sender, RoutedEventArgs e)
    {
        if (LiveSizeSwitch.IsOn)
        {
            TryApplyCursorSize();
        }
    }

    private void UpdateSizeUi(bool applyLive = false)
    {
        var pixels = CurrentCursorPixels();
        SizeProgress.Value = _sizeLevel;
        SizeText.Text = $"{_sizeLevel} / {pixels}px";
        if (applyLive)
        {
            TryApplyCursorSize();
        }
    }

    private void TryApplyCursorSize()
    {
        try
        {
            _services.Cursors.SetSystemCursorSize(CurrentCursorPixels());
        }
        catch (Exception exc)
        {
            _services.Logger.Log("实时调整鼠标大小失败", exc);
            StatusText.Text = exc.Message;
        }
    }

    private int CurrentCursorPixels() => WindowsCursorService.SizeLevelToPixels(_sizeLevel);

    private async void RestoreBackup_Click(object sender, RoutedEventArgs e)
    {
        await RunUiTaskAsync("恢复鼠标方案", () =>
        {
            _services.Cursors.RestoreBackup();
            return "已恢复上一份鼠标方案";
        }, result =>
        {
            StatusText.Text = result;
            RefreshStatus();
        });
    }

    private void OpenPointerSettings_Click(object sender, RoutedEventArgs e)
    {
        Process.Start(new ProcessStartInfo("ms-settings:easeofaccess-mousepointer") { UseShellExecute = true });
    }

    private void RefreshResources_Click(object sender, RoutedEventArgs e) => RefreshResources();

    private async void ApplyResource_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string name })
        {
            SchemeCombo.SelectedItem = name;
            LoadScheme(name);
            ApplyScheme_Click(sender, e);
        }

        await Task.CompletedTask;
    }

    private void EditResource_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string name })
        {
            SchemeCombo.SelectedItem = name;
            RootNavigation.SelectedItem = RootNavigation.MenuItems.OfType<NavigationViewItem>().First(item => Convert.ToString(item.Tag) == "scheme");
            ShowPanel("scheme");
            LoadScheme(name);
        }
    }

    private async void DeleteResource_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: string name })
        {
            return;
        }

        var dialog = new ContentDialog
        {
            XamlRoot = XamlRoot,
            Title = "删除资源",
            Content = $"确定删除“{name}”吗？",
            PrimaryButtonText = "删除",
            CloseButtonText = "取消"
        };
        if (await dialog.ShowAsync() == ContentDialogResult.Primary)
        {
            _services.Schemes.Delete(name);
            RefreshSchemes();
        }
    }

    private void OpenResourceWeb_Click(object sender, RoutedEventArgs e)
    {
        Process.Start(new ProcessStartInfo(AppPaths.ResourceUrl) { UseShellExecute = true });
    }

    private void SaveTimerSwitch_Click(object sender, RoutedEventArgs e)
    {
        var unit = (TimerUnitBox.SelectedItem as ComboBoxItem)?.Content?.ToString() == "分钟" ? 60 : 1;
        var selected = TimerSchemeList.SelectedItems.Cast<string>().ToList();
        var order = (TimerOrderBox.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "顺序";
        var item = new ScheduleItem
        {
            Mode = "timer",
            IntervalSeconds = (int)Math.Max(1, TimerIntervalBox.Value) * unit,
            Order = order,
            Scheme = order,
            SelectedSchemes = selected
        };
        var items = _services.Schedule.LoadSchedule().Where(existing => existing.Mode != "timer").ToList();
        items.Add(item);
        _services.Schedule.SaveSchedule(items);
        _services.Startup.SetAutoStart(true, Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule?.FileName ?? "", HideTaskbarSwitch.IsOn ? "--background" : "--tray");
        AutoStartSwitch.IsOn = true;
        RefreshStatus();
        StatusText.Text = "计时切换已保存并开启后台自启动。";
    }

    private void AddFixedTime_Click(object sender, RoutedEventArgs e)
    {
        if (!TimeOnly.TryParse(FixedTimeBox.Text, out _) || FixedSchemeBox.SelectedItem is not string scheme)
        {
            StatusText.Text = "请输入 HH:mm 时间并选择方案。";
            return;
        }

        var items = _services.Schedule.LoadSchedule();
        items.Add(new ScheduleItem { Mode = "time", Time = FixedTimeBox.Text, Scheme = scheme });
        _services.Schedule.SaveSchedule(items);
        ScheduleList.ItemsSource = items.Select(item => $"{item.Time} -> {item.Scheme}").ToList();
        RefreshStatus();
    }

    private void SaveWeekSwitch_Click(object sender, RoutedEventArgs e)
    {
        var week = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var (box, index) in WeekBoxes().Select((box, index) => (box, index)))
        {
            if (box.SelectedItem is string scheme && !string.IsNullOrWhiteSpace(scheme))
            {
                week[index.ToString()] = scheme;
            }
        }

        _services.Schedule.SaveWeekSchedule(week);
        RefreshStatus();
        StatusText.Text = "星期切换已保存。";
    }

    private void SaveSettings_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var settings = _services.Settings.Load();
            settings["storage_root"] = StoragePathBox.Text;
            settings["output_root"] = OutputPathBox.Text;
            settings["github_url"] = GithubUrlBox.Text;
            settings["hide_taskbar_icon"] = HideTaskbarSwitch.IsOn ? "1" : "0";
            settings[FileAssociationService.SettingKey] = FileAssociationSwitch.IsOn ? "1" : "0";
            _services.Settings.Save(settings);
            Directory.CreateDirectory(StoragePathBox.Text);
            Directory.CreateDirectory(OutputPathBox.Text);
            _services.Startup.SetAutoStart(AutoStartSwitch.IsOn, Environment.ProcessPath ?? "", HideTaskbarSwitch.IsOn ? "--background" : "--tray");
            _services.FileAssociations.Apply(FileAssociationSwitch.IsOn, Environment.ProcessPath ?? "");
            RefreshDiagnostics();
            StatusText.Text = "设置已保存。";
        }
        catch (Exception exc)
        {
            _services.Logger.Log("保存设置失败", exc);
            StatusText.Text = exc.Message;
        }
    }

    private void OpenStorageFolder_Click(object sender, RoutedEventArgs e)
    {
        Directory.CreateDirectory(StoragePathBox.Text);
        OpenFolder(StoragePathBox.Text);
    }

    private void CreateDesktopShortcut_Click(object sender, RoutedEventArgs e)
    {
        var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
        var shortcut = Path.Combine(desktop, "鼠标指针配置管理器.url");
        var exe = (Environment.ProcessPath ?? "").Replace("\\", "/");
        File.WriteAllText(shortcut, $"[InternetShortcut]{Environment.NewLine}URL=file:///{exe}{Environment.NewLine}IconFile={Environment.ProcessPath}{Environment.NewLine}");
        StatusText.Text = $"快捷方式已创建：{shortcut}";
    }

    private async void CheckUpdates_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var release = await _services.Updates.FetchLatestReleaseAsync(GithubUrlBox.Text);
            StatusText.Text = release is null
                ? "没有找到可用的 GitHub Release。"
                : $"最新版本：{release.TagName} {release.Url}";
        }
        catch (Exception exc)
        {
            await ShowErrorAsync("检测更新失败", exc);
        }
    }

    private void CopyDiagnostics_Click(object sender, RoutedEventArgs e)
    {
        RefreshDiagnostics();
        var package = new DataPackage();
        package.SetText(DiagnosticsBox.Text);
        Clipboard.SetContent(package);
        StatusText.Text = "诊断信息已复制。";
    }

    private void RootNavigation_SelectionChanged(NavigationView sender, NavigationViewSelectionChangedEventArgs args)
    {
        if (args.SelectedItem is NavigationViewItem item)
        {
            ShowPanel(Convert.ToString(item.Tag) ?? "scheme");
        }
    }

    private void ShowPanel(string tag)
    {
        SchemePanel.Visibility = tag == "scheme" ? Visibility.Visible : Visibility.Collapsed;
        ResourcePanel.Visibility = tag == "resources" ? Visibility.Visible : Visibility.Collapsed;
        SwitchPanel.Visibility = tag == "switch" ? Visibility.Visible : Visibility.Collapsed;
        SettingsPanel.Visibility = tag == "settings" ? Visibility.Visible : Visibility.Collapsed;
        if (tag == "resources")
        {
            RefreshResources();
        }
    }

    private string CurrentThemeName()
    {
        return SchemeCombo.SelectedItem as string
            ?? _services.Schemes.UniqueSchemeName("新方案");
    }

    private Dictionary<string, string> PrepareSelectedFiles(string theme)
    {
        var prepared = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var temp = Path.Combine(_services.Paths.AppDataRoot, "current_theme", NameSanitizer.Sanitize(theme));
        if (Directory.Exists(temp))
        {
            Directory.Delete(temp, recursive: true);
        }

        Directory.CreateDirectory(temp);
        foreach (var row in _rows.Where(row => !string.IsNullOrWhiteSpace(row.FilePath)))
        {
            prepared[row.RegistryName] = CursorAssetConverter.PrepareCursorAsset(row.FilePath, temp, row.Role, CurrentCursorPixels());
        }

        return prepared;
    }

    private void RefreshStatus()
    {
        var status = _services.Schedule.GetStatus();
        CurrentSchemeText.Text = string.IsNullOrWhiteSpace(status.CurrentScheme)
            ? "当前方案：未记录"
            : $"当前方案：{status.CurrentScheme}";
        NextSwitchText.Text = string.IsNullOrWhiteSpace(status.NextSwitchText)
            ? "下次切换：未设置"
            : $"下次切换：{status.NextSwitchText}";
    }

    private void RefreshDiagnostics()
    {
        DiagnosticsBox.Text = string.Join(Environment.NewLine, new[]
        {
            $"{AppPaths.AppName} {AppPaths.AppVersion}",
            $"Base: {_services.Paths.AppBaseDirectory}",
            $"Storage: {_services.Settings.StorageRoot}",
            $"Output: {_services.Settings.OutputRoot}",
            _services.Startup.StartupStatusText(),
            $"File association: {_services.Settings.IsEnabled(FileAssociationService.SettingKey)}",
            $"Current scheme: {_services.Settings.CurrentScheme}",
            $"Next switch: {_services.Schedule.NextSwitchText()}",
            $"Process: {Environment.ProcessPath}"
        });
    }

    private IEnumerable<ComboBox> WeekBoxes()
    {
        yield return Week0;
        yield return Week1;
        yield return Week2;
        yield return Week3;
        yield return Week4;
        yield return Week5;
        yield return Week6;
    }

    private async Task<string?> PickCursorOrImageAsync()
    {
        var picker = new FileOpenPicker();
        InitializeWithWindow.Initialize(picker, WindowHandle);
        foreach (var extension in new[] { ".cur", ".ani", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico" })
        {
            picker.FileTypeFilter.Add(extension);
        }

        var file = await picker.PickSingleFileAsync();
        return file?.Path;
    }

    private async Task<string?> PickImportPackageAsync()
    {
        var picker = new FileOpenPicker();
        InitializeWithWindow.Initialize(picker, WindowHandle);
        foreach (var extension in new[] { ".zip", ".rar", ".7z", ".exe" })
        {
            picker.FileTypeFilter.Add(extension);
        }

        var file = await picker.PickSingleFileAsync();
        return file?.Path;
    }

    private async Task<string?> PickFolderAsync()
    {
        var picker = new FolderPicker();
        InitializeWithWindow.Initialize(picker, WindowHandle);
        picker.FileTypeFilter.Add("*");
        var folder = await picker.PickSingleFolderAsync();
        return folder?.Path;
    }

    private IntPtr WindowHandle => WindowNative.GetWindowHandle(App.MainAppWindow);

    private async Task<string?> AskTextAsync(string title, string label, string defaultValue)
    {
        var textBox = new TextBox { Header = label, Text = defaultValue };
        var dialog = new ContentDialog
        {
            XamlRoot = XamlRoot,
            Title = title,
            Content = textBox,
            PrimaryButtonText = "确定",
            CloseButtonText = "取消"
        };
        return await dialog.ShowAsync() == ContentDialogResult.Primary ? textBox.Text : null;
    }

    private async Task RunUiTaskAsync<T>(string title, Func<T> work, Action<T> done)
    {
        try
        {
            StatusText.Text = $"{title}中...";
            var result = await Task.Run(work);
            done(result);
        }
        catch (Exception exc)
        {
            _services.Logger.Log(title, exc);
            await ShowErrorAsync(title, exc);
        }
    }

    private async Task ShowErrorAsync(string title, Exception exception)
    {
        var dialog = new ContentDialog
        {
            XamlRoot = XamlRoot,
            Title = title,
            Content = exception.Message,
            CloseButtonText = "知道了"
        };
        await dialog.ShowAsync();
    }

    private static void OpenFolder(string folder)
    {
        Process.Start(new ProcessStartInfo(folder) { UseShellExecute = true });
    }
}
