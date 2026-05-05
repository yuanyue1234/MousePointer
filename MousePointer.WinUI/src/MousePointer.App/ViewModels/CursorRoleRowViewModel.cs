using MousePointer.Core.Models;

namespace MousePointer.App.ViewModels;

public sealed class CursorRoleRowViewModel : ObservableObject
{
    private string _filePath = "";
    private string _fileName = "未选择";
    private string _badge = "";

    public CursorRoleRowViewModel(CursorRole role)
    {
        Role = role;
    }

    public CursorRole Role { get; }
    public string Label => Role.Label;
    public string RegistryName => Role.RegistryName;
    public string Tip => Role.Tip;

    public string FilePath
    {
        get => _filePath;
        set
        {
            if (SetProperty(ref _filePath, value))
            {
                FileName = string.IsNullOrWhiteSpace(value) ? "未选择" : Path.GetFileName(value);
                Badge = Path.GetExtension(value).ToLowerInvariant() switch
                {
                    ".ani" => "动",
                    ".cur" => "静",
                    _ => ""
                };
            }
        }
    }

    public string FileName
    {
        get => _fileName;
        private set => SetProperty(ref _fileName, value);
    }

    public string Badge
    {
        get => _badge;
        private set => SetProperty(ref _badge, value);
    }
}

