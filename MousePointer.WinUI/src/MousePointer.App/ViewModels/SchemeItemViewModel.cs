namespace MousePointer.App.ViewModels;

public sealed class SchemeItemViewModel(string name, int fileCount)
{
    public string Name { get; } = name;
    public int FileCount { get; } = fileCount;
    public string Summary => $"{FileCount} 个鼠标状态";
}

