using System.Text.Json;

namespace DbdAssistant.Core;

/// <summary>
/// Position reelle des portraits sur l'ecran du joueur, obtenue par la calibration (2 clics : 1er et 4e portrait).
/// Tout est exprime en fraction de la HAUTEUR de l'ecran : l'interface de DBD est dimensionnee par la hauteur.
/// </summary>
public sealed record PortraitCalibration(double XFrac, double Y1Frac, double Y4Frac)
{
    /// <summary>Distance verticale entre deux portraits voisins (le 1er et le 4e sont espaces de 3 pas).</summary>
    public double StepFrac => (Y4Frac - Y1Frac) / 3;

    public static PortraitCalibration FromPixels(double x, double y1, double y4, int screenHeight) =>
        new(x / screenHeight, y1 / screenHeight, y4 / screenHeight);

    /// <summary>Verifie que les deux clics ont un sens : 1er au-dessus du 4e, meme colonne, espacement plausible.</summary>
    public static bool IsPlausible(double x1, double y1, double x4, double y4, int screenHeight, out string reason)
    {
        double step = (y4 - y1) / 3;
        if (step < screenHeight * 0.04) { reason = "Clique sur le 1er portrait (en haut) puis sur le 4e (en bas)."; return false; }
        if (step > screenHeight * 0.15) { reason = "Les deux clics sont trop espaces pour 1er et 4e portraits."; return false; }
        if (Math.Abs(x4 - x1) > step / 3) { reason = "Les deux clics doivent etre dans la meme colonne verticale."; return false; }
        reason = "";
        return true;
    }

    public static string DefaultPath =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "DbdAssistant", "calibration.json");

    public static PortraitCalibration? Load(string? path = null)
    {
        try
        {
            path ??= DefaultPath;
            if (!File.Exists(path)) return null;
            var c = JsonSerializer.Deserialize<PortraitCalibration>(File.ReadAllText(path));
            return c != null && c.StepFrac > 0 ? c : null;
        }
        catch { return null; } // fichier abime : on revient au calcul par defaut
    }

    public void Save(string? path = null)
    {
        path ??= DefaultPath;
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, JsonSerializer.Serialize(this));
    }

    public static void Delete(string? path = null)
    {
        path ??= DefaultPath;
        if (File.Exists(path)) File.Delete(path);
    }
}
