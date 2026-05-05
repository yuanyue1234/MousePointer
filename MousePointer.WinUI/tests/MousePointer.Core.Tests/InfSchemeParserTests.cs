using MousePointer.Core.Services;

namespace MousePointer.Core.Tests;

public sealed class InfSchemeParserTests
{
    [Fact]
    public void Parses_Alias_And_Registry_Values_From_Inf()
    {
        using var temp = new TempDirectory();
        var arrow = temp.File("arrow.cur");
        var hand = temp.File("hand.cur");
        var pin = temp.File("pin.cur");
        var person = temp.File("person.cur");
        File.WriteAllText(
            Path.Combine(temp.Path, "theme.inf"),
            """
            [Strings]
            arrow = arrow.cur
            hand = hand.cur
            pin = pin.cur
            person = person.cur
            HKCU,"Control Panel\Cursors",Pin,0x00020000,"pin.cur"
            HKCU,"Control Panel\Cursors",Person,0x00020000,"person.cur"
            """);

        var parser = new InfSchemeParser(new CursorMatcher());
        var scheme = Assert.Single(parser.ParseAll(temp.Path));

        Assert.Equal(arrow, scheme.Files["Arrow"]);
        Assert.Equal(hand, scheme.Files["Hand"]);
        Assert.Equal(pin, scheme.Files["Pin"]);
        Assert.Equal(person, scheme.Files["Person"]);
    }
}

