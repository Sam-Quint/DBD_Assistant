using System.Text.Json;

namespace DbdAssistant.Core;

/// <summary>
/// Quel HUD est affiche. Le HUD survivant ajoute a droite de chaque portrait un rond d'action et des icones de statut :
/// les marques de crochets (`!`) y sont plus a droite et il y a toujours 2 emplacements (blanc = crochet subi, sombre = libre).
/// Choisi a la main dans l'app : le rond sombre ne permet pas de le deviner de facon fiable (voir JOURNAL.md).
/// </summary>
public enum HudMode { Killer, Survivor }

/// <summary>Reglages memorises entre deux lancements (%APPDATA%\DbdAssistant\settings.json).</summary>
public sealed record AppSettings(HudMode Mode = HudMode.Killer)
{
    public static string DefaultPath =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "DbdAssistant", "settings.json");

    public static AppSettings Load(string? path = null)
    {
        try
        {
            path ??= DefaultPath;
            return File.Exists(path) ? JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(path)) ?? new AppSettings() : new AppSettings();
        }
        catch { return new AppSettings(); }
    }

    public void Save(string? path = null)
    {
        path ??= DefaultPath;
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, JsonSerializer.Serialize(this));
    }
}
