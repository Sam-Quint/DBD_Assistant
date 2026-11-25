namespace DbdAssistant.Core;

/// <summary>Un rectangle en pixels ecran.</summary>
public readonly record struct Zone(int X, int Y, int W, int H);

/// <summary>Les zones a lire pour un survivant.</summary>
public sealed record SurvivorZones(
    int Index,
    Zone Disc,   // cercle du portrait / icone d'etat (visage, crochet, rampant, crane, porte...)
    Zone Marks,  // marques "!" / "!!" : nombre de crochets deja subis
    Zone Bar1,   // 1re barre (1er stade de crochet / saignement / Deep Wounds)
    Zone Bar2);  // 2e barre (2e stade de crochet)

/// <summary>
/// Position des 4 portraits de survivants, calculee a partir de la hauteur de l'ecran.
/// L'interface de DBD est ancree a gauche et dimensionnee par la HAUTEUR : le ratio (16:9, 21:9...)
/// ne change rien. Mesures faites en 1920x1080, echelle d'interface 100 %.
/// </summary>
public static class PortraitLayout
{
    public const int RefHeight = 1080;

    // Mesures de reference (1080p) : centre du 1er portrait et pas vertical.
    private const double CenterX = 128;
    private const double FirstY = 457;
    private const double StepY = 88;

    // Zones relatives au centre du portrait (1080p).
    private const double DiscSize = 64;
    /// <summary>Diametre du cercle a l'echelle de reference (celle des modeles d'icones).</summary>
    public const double DiscRef = DiscSize;
    private static readonly (double dx, double dy, double w, double h) Marks = (57, -26, 24, 26);
    // HUD survivant : rond d action puis icone de statut eventuelle, puis les marques : zone large apres le rond.
    private static readonly (double dx, double dy, double w, double h) MarksSurvivor = (99, -26, 69, 26);
    private static readonly (double dx, double dy, double w, double h) Bar1 = (57, 25, 47, 12);
    private static readonly (double dx, double dy, double w, double h) Bar2 = (110, 25, 47, 12);

    /// <param name="screenHeight">Hauteur de l'ecran en pixels.</param>
    /// <param name="calibration">Position mesuree par la calibration (2 clics). Prioritaire sur le calcul par defaut.</param>
    /// <param name="uiScale">Echelle d'interface choisie dans les options du jeu (1.0 = 100 %). Ignoree si calibre.</param>
    /// <param name="offsetX">Decalage horizontal fin, en pixels ecran.</param>
    /// <param name="offsetY">Decalage vertical fin, en pixels ecran.</param>
    public static IReadOnlyList<SurvivorZones> Compute(int screenHeight, PortraitCalibration? calibration = null, HudMode mode = HudMode.Killer,
        double uiScale = 1.0, int offsetX = 0, int offsetY = 0)
    {
        double k, centerX, firstY, step;
        if (calibration != null)
        {
            centerX = calibration.XFrac * screenHeight;
            firstY = calibration.Y1Frac * screenHeight;
            step = calibration.StepFrac * screenHeight;
            k = step / StepY; // echelle d'interface deduite de l'espacement mesure
        }
        else
        {
            // L'interface est ancree en bas a gauche : la distance au BAS de l'ecran est proportionnelle a l'echelle.
            k = (double)screenHeight / RefHeight * uiScale;
            centerX = CenterX * k;
            step = StepY * k;
            firstY = screenHeight - (RefHeight - FirstY) * k;
        }

        var marks = mode == HudMode.Survivor ? MarksSurvivor : Marks;
        var list = new List<SurvivorZones>(4);
        for (int i = 0; i < 4; i++)
        {
            double cx = centerX + offsetX;
            double cy = firstY + i * step + offsetY;
            list.Add(new SurvivorZones(
                i,
                Make(cx, cy, -DiscSize / 2 * k, -DiscSize / 2 * k, DiscSize * k, DiscSize * k),
                Make(cx, cy, marks.dx * k, marks.dy * k, marks.w * k, marks.h * k),
                Make(cx, cy, Bar1.dx * k, Bar1.dy * k, Bar1.w * k, Bar1.h * k),
                Make(cx, cy, Bar2.dx * k, Bar2.dy * k, Bar2.w * k, Bar2.h * k)));
        }
        return list;
    }

    private static Zone Make(double cx, double cy, double dx, double dy, double w, double h) =>
        new((int)Math.Round(cx + dx), (int)Math.Round(cy + dy), (int)Math.Round(w), (int)Math.Round(h));
}
