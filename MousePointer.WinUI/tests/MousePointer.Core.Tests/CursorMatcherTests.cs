using MousePointer.Core.Services;

namespace MousePointer.Core.Tests;

public sealed class CursorMatcherTests
{
    [Fact]
    public void Maps_New_Windows_11_Roles_Without_Confusing_Handwriting_And_Link()
    {
        using var temp = new TempDirectory();
        var files = new[]
        {
            temp.File("normal_arrow.cur"),
            temp.File("handwriting_pen.cur"),
            temp.File("link_hand.ani"),
            temp.File("precision_crosshair.cur"),
            temp.File("location_pin.cur"),
            temp.File("person_user.cur")
        };

        var mapping = new CursorMatcher().MapFilesToRoles(files);

        Assert.Equal(files[0], mapping["Arrow"]);
        Assert.Equal(files[1], mapping["NWPen"]);
        Assert.Equal(files[2], mapping["Hand"]);
        Assert.Equal(files[3], mapping["Crosshair"]);
        Assert.Equal(files[4], mapping["Pin"]);
        Assert.Equal(files[5], mapping["Person"]);
    }

    [Fact]
    public void Uses_Numbered_Fallback_For_All_Seventeen_Roles()
    {
        using var temp = new TempDirectory();
        var files = Enumerable.Range(1, 17).Select(index => temp.File($"{index:00}.cur")).ToList();

        var mapping = new CursorMatcher().MapFilesToRoles(files);

        Assert.Equal(17, mapping.Count);
        Assert.True(mapping.ContainsKey("Pin"));
        Assert.True(mapping.ContainsKey("Person"));
    }
}

