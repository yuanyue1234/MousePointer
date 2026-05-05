using MousePointer.Core.Infrastructure;
using MousePointer.Core.Services;

namespace MousePointer.App;

public sealed class AppServices
{
    public AppServices()
    {
        Paths = AppPaths.CreateDefault();
        Logger = new ErrorLogger(Paths);
        Settings = new SettingsService(Paths);
        Matcher = new CursorMatcher();
        Parser = new InfSchemeParser(Matcher);
        Extractor = new ArchiveExtractor(Paths);
        Schemes = new CursorSchemeStore(Settings, Extractor, Parser);
        Cursors = new WindowsCursorService(Paths, Settings);
        Schedule = new ScheduleService(Paths, Settings, Schemes);
        Startup = new StartupService();
        FileAssociations = new FileAssociationService();
        Updates = new UpdateService();
        InstallerBuilder = new InstallerPackageBuilder(Paths);
    }

    public AppPaths Paths { get; }
    public ErrorLogger Logger { get; }
    public SettingsService Settings { get; }
    public CursorMatcher Matcher { get; }
    public InfSchemeParser Parser { get; }
    public ArchiveExtractor Extractor { get; }
    public CursorSchemeStore Schemes { get; }
    public WindowsCursorService Cursors { get; }
    public ScheduleService Schedule { get; }
    public StartupService Startup { get; }
    public FileAssociationService FileAssociations { get; }
    public UpdateService Updates { get; }
    public InstallerPackageBuilder InstallerBuilder { get; }
}

