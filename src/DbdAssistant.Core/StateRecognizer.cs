namespace DbdAssistant.Core;

/// <summary>Ce qui a ete lu pour un survivant a un instant donne.</summary>
public sealed record SurvivorReading(
    SurvivorState State,
    SurvivorState BestIcon,  // meilleur modele d'icone, meme sous le seuil
    double IconScore,        // 0..1 : ressemblance avec ce modele
    int HookMarks,           // nombre de "!" (crochets deja subis)
    double Bar1,             // part de pixels "barre coloree" dans la barre 1 (0..1)
    double Bar2,
    bool YellowBar,          // barre jaune = Deep Wounds
    double Scratch);         // part de pixels rouge vif dans le cercle (griffures)

/// <summary>
/// Lit l'etat d'un survivant uniquement a partir des pixels de son portrait.
///  1. Icone (crochet, rampant, porte, crane, porte de sortie) : comparaison avec des modeles
///     sur l'image "blanc minimal" (min des canaux R,V,B) : les fonds colores et les cercles
///     bleus/rouges disparaissent, il ne reste que le dessin blanc de l'icone.
///  2. Sinon barre jaune : Deep Wounds.
///  3. Sinon griffures rouges sur le visage : blesse.
///  4. Sinon sain.
/// </summary>
public sealed class StateRecognizer
{
    private readonly TemplateLibrary _library;
    private const int P = TemplateLibrary.PatchSize;
    private const int Search = 3; // tolerance de position (+/- pixels)

    public double IconThreshold { get; set; } = 0.72;
    public double ScratchThreshold { get; set; } = 0.002;
    public double BarThreshold { get; set; } = 0.10;

    public StateRecognizer(TemplateLibrary library) => _library = library;

    /// <param name="excludeSource">Ignore les modeles issus de cette capture (evaluation leave-one-out).</param>
    public SurvivorReading Read(Frame f, SurvivorZones z, string? excludeSource = null)
    {
        int cx = z.Disc.X + z.Disc.W / 2, cy = z.Disc.Y + z.Disc.H / 2;

        // 1. Icone
        var (bestState, bestScore) = MatchIcon(f, cx, cy, excludeSource);

        // Barres et marques
        double bar1 = ColorFraction(f, z.Bar1, red: true) + ColorFraction(f, z.Bar1, red: false);
        double bar2 = ColorFraction(f, z.Bar2, red: true) + ColorFraction(f, z.Bar2, red: false);
        bool yellow = ColorFraction(f, z.Bar1, red: false) >= BarThreshold
                   || ColorFraction(f, z.Bar2, red: false) >= BarThreshold;
        double scratch = ScratchFraction(f, cx, cy, z.Disc.W / 2);
        int marks = CountMarks(f, z.Marks);

        SurvivorState state;
        if (bestScore >= IconThreshold) state = bestState;
        else if (yellow) state = SurvivorState.DeepWounds;
        else if (scratch >= ScratchThreshold) state = SurvivorState.Injured;
        else state = SurvivorState.Healthy;

        return new SurvivorReading(state, bestState, bestScore, marks, bar1, bar2, yellow, scratch);
    }

    // ---------- icone ----------

    private (SurvivorState state, double score) MatchIcon(Frame f, int cx, int cy, string? excludeSource)
    {
        var best = SurvivorState.Unknown;
        double bestScore = -1;
        var patch = new float[P * P];

        for (int dy = -Search; dy <= Search; dy++)
        for (int dx = -Search; dx <= Search; dx++)
        {
            double norm = FillZeroMeanPatch(f, cx + dx, cy + dy, patch);
            if (norm < 1e-3) continue; // zone uniforme
            foreach (var t in _library.Items)
            {
                if (excludeSource != null && t.Source == excludeSource) continue;
                if (t.Norm < 1e-3) continue;
                double dot = 0;
                var td = t.Data;
                for (int i = 0; i < patch.Length; i++) dot += patch[i] * td[i];
                double score = dot / (norm * t.Norm);
                if (score > bestScore) { bestScore = score; best = t.State; }
            }
        }
        return (best, Math.Max(0, bestScore));
    }

    /// <summary>Remplit patch avec le "blanc minimal" centre sur (cx,cy), moyenne retiree. Renvoie la norme.</summary>
    internal static double FillZeroMeanPatch(Frame f, int cx, int cy, float[] patch)
    {
        int x0 = cx - P / 2, y0 = cy - P / 2;
        double sum = 0;
        for (int y = 0; y < P; y++)
            for (int x = 0; x < P; x++)
            {
                float v = MinChannel(f, x0 + x, y0 + y);
                patch[y * P + x] = v;
                sum += v;
            }
        float mean = (float)(sum / patch.Length);
        double sq = 0;
        for (int i = 0; i < patch.Length; i++) { patch[i] -= mean; sq += patch[i] * patch[i]; }
        return Math.Sqrt(sq);
    }

    /// <summary>Extrait le patch brut (0..255) utilise pour fabriquer un modele.</summary>
    public static byte[] ExtractRawPatch(Frame f, SurvivorZones z)
    {
        int cx = z.Disc.X + z.Disc.W / 2, cy = z.Disc.Y + z.Disc.H / 2;
        int x0 = cx - P / 2, y0 = cy - P / 2;
        var raw = new byte[P * P];
        for (int y = 0; y < P; y++)
            for (int x = 0; x < P; x++)
                raw[y * P + x] = (byte)MinChannel(f, x0 + x, y0 + y);
        return raw;
    }

    private static float MinChannel(Frame f, int x, int y)
    {
        if (x < 0 || y < 0 || x >= f.Width || y >= f.Height) return 0;
        int i = (y * f.Width + x) * 4;
        return Math.Min(f.Bgra[i], Math.Min(f.Bgra[i + 1], f.Bgra[i + 2]));
    }

    // ---------- couleurs ----------

    private static double ColorFraction(Frame f, Zone z, bool red)
    {
        int hits = 0, total = 0;
        for (int y = z.Y; y < z.Y + z.H; y++)
            for (int x = z.X; x < z.X + z.W; x++)
            {
                if (x < 0 || y < 0 || x >= f.Width || y >= f.Height) continue;
                int i = (y * f.Width + x) * 4;
                int b = f.Bgra[i], g = f.Bgra[i + 1], r = f.Bgra[i + 2];
                bool hit = red ? (r >= 170 && g <= 80 && b <= 80)
                               : (r >= 220 && g >= 200 && b <= 90);
                if (hit) hits++;
                total++;
            }
        return total == 0 ? 0 : (double)hits / total;
    }

    private static double ScratchFraction(Frame f, int cx, int cy, int radius)
    {
        int hits = 0, total = 0;
        for (int y = cy - radius; y <= cy + radius; y++)
            for (int x = cx - radius; x <= cx + radius; x++)
            {
                int dx = x - cx, dy = y - cy;
                if (dx * dx + dy * dy > radius * radius) continue;
                if (x < 0 || y < 0 || x >= f.Width || y >= f.Height) continue;
                int i = (y * f.Width + x) * 4;
                int b = f.Bgra[i], g = f.Bgra[i + 1], r = f.Bgra[i + 2];
                if (r >= 200 && g <= 70 && b <= 70) hits++;
                total++;
            }
        return total == 0 ? 0 : (double)hits / total;
    }

    // ---------- marques "!" ----------

    private static int CountMarks(Frame f, Zone z)
    {
        int groups = 0;
        bool inGroup = false;
        for (int x = z.X; x < z.X + z.W; x++)
        {
            int count = 0;
            for (int y = z.Y; y < z.Y + z.H; y++)
                if (MinChannel(f, x, y) >= 190) count++;
            bool stroke = count >= Math.Max(6, z.H / 3);
            if (stroke && !inGroup) groups++;
            inGroup = stroke;
        }
        return Math.Min(groups, 3);
    }
}
