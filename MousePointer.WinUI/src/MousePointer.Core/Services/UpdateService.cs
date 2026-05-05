using System.Net.Http.Json;
using System.Text.Json.Serialization;
using MousePointer.Core.Infrastructure;

namespace MousePointer.Core.Services;

public sealed class UpdateService
{
    private readonly HttpClient _client = new();

    public async Task<ReleaseInfo?> FetchLatestReleaseAsync(string repositoryUrl, CancellationToken cancellationToken = default)
    {
        var (owner, repo) = ParseRepository(repositoryUrl);
        using var request = new HttpRequestMessage(HttpMethod.Get, $"https://api.github.com/repos/{owner}/{repo}/releases/latest");
        request.Headers.UserAgent.ParseAdd("MousePointer-WinUI");
        using var response = await _client.SendAsync(request, cancellationToken).ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
        {
            return null;
        }

        var release = await response.Content.ReadFromJsonAsync<GithubRelease>(cancellationToken: cancellationToken).ConfigureAwait(false);
        return release is null
            ? null
            : new ReleaseInfo(release.TagName ?? "", release.Name ?? release.TagName ?? "", release.HtmlUrl ?? repositoryUrl);
    }

    private static (string Owner, string Repo) ParseRepository(string repositoryUrl)
    {
        var uri = new Uri(repositoryUrl);
        var parts = uri.AbsolutePath.Trim('/').Split('/', StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length < 2)
        {
            throw new InvalidOperationException("GitHub 地址格式不正确。");
        }

        return (parts[0], parts[1]);
    }

    private sealed class GithubRelease
    {
        [JsonPropertyName("tag_name")]
        public string? TagName { get; set; }

        [JsonPropertyName("name")]
        public string? Name { get; set; }

        [JsonPropertyName("html_url")]
        public string? HtmlUrl { get; set; }
    }
}

public sealed record ReleaseInfo(string TagName, string Name, string Url);

