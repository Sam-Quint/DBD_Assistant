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
    public double ScratchThreshold { get; set; } = 0.0115;
    public double BarThreshold { get; set; } = 0.10;
    public int MarkBrightness { get; set; } = 165;

    public StateRecognizer(TemplateLibrary library) => _library = library;

    /// <param name="excludeSource">Ignore les modeles issus de cette capture (evaluation leave-one-out).</param>
    public SurvivorReading Read(Frame f, SurvivorZones z, string? excludeSource = null, HudMode mode = HudMode.Killer)
    {
        int cx = z.Disc.X + z.Disc.W / 2, cy = z.Disc.Y + z.Disc.H / 2;
        double k = z.Disc.W / PortraitLayout.DiscRef; // echelle de l'interface (1.0 = celle des modeles)

        // 1. Icone
        var (bestState, bestScore) = MatchIcon(f, cx, cy, k, excludeSource);

        // Barres et marques
        double bar1 = ColorFraction(f, z.Bar1, red: true) + ColorFraction(f, z.Bar1, red: false);
        double bar2 = ColorFraction(f, z.Bar2, red: true) + ColorFraction(f, z.Bar2, red: false);
        bool yellow = HasYellowBar(f, z.Bar1, firstBar: true) || HasYellowBar(f, z.Bar2, firstBar: false);
        double scratch = ScratchFraction(f, cx, cy, z.Disc.W / 2);
        int marks = mode == HudMode.Survivor ? MarkPairReader.Count(f, z.Marks, out _) : CountMarks(f, z.Marks, MarkBrightness);

        SurvivorState state;
        if (bestScore >= IconThreshold) state = bestState;
        else if (yellow) state = SurvivorState.DeepWounds;
        else if (scratch >= ScratchThreshold) state = SurvivorState.Injured;
        else state = SurvivorState.Healthy;

        return new SurvivorReading(state, bestState, bestScore, marks, bar1, bar2, yellow, scratch);
    }

    // ---------- icone ----------

    private (SurvivorState state, double score) MatchIcon(Frame f, int cx, int cy, double k, string? excludeSource)
    {
        var best = SurvivorState.Unknown;
        double bestScore = -1;
        var patch = new float[P * P];

        for (int dy = -Search; dy <= Search; dy++)
        for (int dx = -Search; dx <= Search; dx++)
        {
            double norm = FillZeroMeanPatch(f, cx + dx, cy + dy, k, patch);
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

    /// <summary>
    /// Remplit patch avec le "blanc minimal" centre sur (cx,cy), moyenne retiree. Renvoie la norme.
    /// k = echelle de l'interface : l'ecran est reechantillonne (interpolation bilineaire) pour que l'icone
    /// ait la taille des modeles, quelle que soit la taille d'interface choisie dans le jeu.
    /// </summary>
    internal static double FillZeroMeanPatch(Frame f, int cx, int cy, double k, float[] patch)
    {
        double sum = 0;
        for (int y = 0; y < P; y++)
            for (int x = 0; x < P; x++)
            {
                float v = Sample(f, cx + (x - P / 2) * k, cy + (y - P / 2) * k);
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
        double k = z.Disc.W / PortraitLayout.DiscRef;
        var raw = new byte[P * P];
        for (int y = 0; y < P; y++)
            for (int x = 0; x < P; x++)
                raw[y * P + x] = (byte)Math.Round(Sample(f, cx + (x - P / 2) * k, cy + (y - P / 2) * k));
        return raw;
    }

    /// <summary>"Blanc minimal" a une position fractionnaire (interpolation bilineaire).</summary>
    private static float Sample(Frame f, double x, double y)
    {
        int x0 = (int)Math.Floor(x), y0 = (int)Math.Floor(y);
        float fx = (float)(x - x0), fy = (float)(y - y0);
        if (fx == 0 && fy == 0) return MinChannel(f, x0, y0);
        float a = MinChannel(f, x0, y0), b = MinChannel(f, x0 + 1, y0);
        float c = MinChannel(f, x0, y0 + 1), d = MinChannel(f, x0 + 1, y0 + 1);
        return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy;
    }

    private static float MinChannel(Frame f, int x, int y)
    {
        if (x < 0 || y < 0 || x >= f.Width || y >= f.Height) return 0;
        int i = (y * f.Width + x) * 4;
        return Math.Min(f.Bgra[i], Math.Min(f.Bgra[i + 1], f.Bgra[i + 2]));
    }

    // ---------- barre jaune (Deep Wounds) ----------

    private static bool IsYellow(int r, int g, int b)
    {
        // Teinte jaune (40-76 degres : le vert ambiant d une map decale la teinte), assez saturee et lumineuse. Independant du fond :
        // le sable orange (teinte ~30) et les tons bruns sont ecartes par la teinte.
        int max = Math.Max(r, Math.Max(g, b)), min = Math.Min(r, Math.Min(g, b));
        if (max < 130 || max == 0) return false;
        double d = max - min;
        if (d / max < 0.45) return false;
        double h = max == r ? 60 * ((g - b) / d) : max == g ? 60 * (2 + (b - r) / d) : 60 * (4 + (r - g) / d);
        if (h < 0) h += 360;
        return h >= 32 && h <= 76;
    }

    /// <summary>Debug : ligne la plus jaune de la zone, plus longue suite jaune et ecart-type de la couleur des pixels jaunes.</summary>
    public static string DebugYellowRows(Frame f, Zone z)
    {
        double best = 0; int bestY = z.Y;
        for (int y = z.Y - 2; y < z.Y + z.H + 2; y++) { double r = YellowRowFraction(f, z.X, z.W, y); if (r > best) { best = r; bestY = y; } }
        int run = 0, maxRun = 0; var gs = new List<double>(); var rs = new List<double>();
        for (int x = z.X; x < z.X + z.W; x++)
        {
            int i = (bestY * f.Width + x) * 4;
            if (x >= 0 && x < f.Width && IsYellow(f.Bgra[i + 2], f.Bgra[i + 1], f.Bgra[i])) { run++; maxRun = Math.Max(maxRun, run); gs.Add(f.Bgra[i + 1]); rs.Add(f.Bgra[i + 2]); }
            else run = 0;
        }
        double Sd(List<double> v) { if (v.Count < 2) return 0; double m = v.Average(); return Math.Sqrt(v.Select(a => (a - m) * (a - m)).Average()); }
        return $"best={best:0.00} run={maxRun}/{z.W} sdG={Sd(gs):0.0} sdR={Sd(rs):0.0}";
    }

    private static double YellowRowFraction(Frame f, int x0, int w, int y)
    {
        if (y < 0 || y >= f.Height) return 0;
        int hits = 0, total = 0;
        for (int x = x0; x < x0 + w; x++)
        {
            if (x < 0 || x >= f.Width) continue;
            int i = (y * f.Width + x) * 4;
            if (IsYellow(f.Bgra[i + 2], f.Bgra[i + 1], f.Bgra[i])) hits++;
            total++;
        }
        return total == 0 ? 0 : (double)hits / total;
    }

    /// <summary>
    /// Une barre = une bande horizontale jaune. On cherche la ligne la plus jaune de la zone (tolerance
    /// verticale +/- 2 px), qui doit etre au moins remplie a 25 % (barre vidant), et on verifie que les
    /// lignes juste au-dessus et en dessous le sont beaucoup moins : un fond jaune uni est refuse.
    /// </summary>
    private static bool HasYellowBar(Frame f, Zone z, bool firstBar)
    {
        double best = 0; int bestY = z.Y;
        for (int y = z.Y - 2; y < z.Y + z.H + 2; y++)
        {
            double r = YellowRowFraction(f, z.X, z.W, y);
            if (r > best) { best = r; bestY = y; }
        }
        if (best < 0.25) return false;
        // Les lignes autour (a 6..12 px) doivent etre bien moins jaunes, en MOYENNE : un sol de briques jaunes
        // a des lignes tantot jaunes tantot sombres (joints) et ne doit pas passer pour une barre.
        double above = 0, below = 0;
        int[] offs = { 6, 8, 10, 12 };
        foreach (int o in offs)
        {
            above += YellowRowFraction(f, z.X, z.W, bestY - o);
            below += YellowRowFraction(f, z.X, z.W, bestY + o);
        }
        above /= offs.Length; below /= offs.Length;
        if (!(above < best * 0.4 && below < best * 0.4)) return false;

        // Epaisseur : une barre fait ~6-7 px (a l'echelle 1.0). Une rangee de briques jaunes est bien plus epaisse.
        double k = z.H / 12.0; // la zone fait 12 px a l'echelle 1.0
        int thickness = 1;
        for (int y = bestY - 1; y >= bestY - 14 && YellowRowFraction(f, z.X, z.W, y) >= best * 0.5; y--) thickness++;
        for (int y = bestY + 1; y <= bestY + 14 && YellowRowFraction(f, z.X, z.W, y) >= best * 0.5; y++) thickness++;
        if (thickness > Math.Ceiling(8.5 * k)) return false;

        // Longueur continue : une barre pleine est une suite quasi ininterrompue (>= 41/47 px mesures), alors qu'un fond
        // texture (briques) donne des segments courts. Une barre qui se vide reste collee au bord gauche de la 1re zone.
        int run = 0, maxRun = 0, leftRun = 0; bool leftOpen = true;
        for (int x = z.X; x < z.X + z.W; x++)
        {
            bool yel = false;
            if (x >= 0 && x < f.Width && bestY >= 0 && bestY < f.Height)
            {
                int i = (bestY * f.Width + x) * 4;
                yel = IsYellow(f.Bgra[i + 2], f.Bgra[i + 1], f.Bgra[i]);
            }
            if (yel) { run++; maxRun = Math.Max(maxRun, run); if (leftOpen) leftRun++; }
            else { run = 0; if (x - z.X >= 2) leftOpen = false; } // 2 px de tolerance sur le bord
        }
        bool full = best >= 0.6 && maxRun >= 0.6 * z.W;
        bool draining = firstBar && leftRun >= 0.25 * z.W;
        return full || draining;
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

    /// <summary>
    /// Griffures = traits rouges FINS dans le cercle du portrait.
    ///  - rouge en proportion (le canal rouge domine) et non un seuil fixe : un portrait assombri ou une scene teintee
    ///    garde des griffures a R~185 ;
    ///  - seuls les traits fins comptent (rouge moins son ouverture 3x3) : les taches larges (eclaboussures de la Peste,
    ///    arc rouge de poursuite) disparaissent.
    /// Renvoie la part du disque occupee par ces traits (0..1).
    /// </summary>
    internal static double ScratchFraction(Frame f, int cx, int cy, int radius)
    {
        int n = 2 * radius + 1;
        var red = new bool[n * n];
        int total = 0;
        for (int y = 0; y < n; y++)
            for (int x = 0; x < n; x++)
            {
                int dx = x - radius, dy = y - radius;
                if (dx * dx + dy * dy > radius * radius) continue;
                int sx = cx + dx, sy = cy + dy;
                if (sx < 0 || sy < 0 || sx >= f.Width || sy >= f.Height) continue;
                total++;
                int i = (sy * f.Width + sx) * 4;
                int b = f.Bgra[i], g = f.Bgra[i + 1], r = f.Bgra[i + 2];
                red[y * n + x] = r >= 110 && g * 10 <= r * 4 && b * 10 <= r * 4;
            }
        if (total == 0) return 0;

        var eroded = new bool[n * n];
        for (int y = 1; y < n - 1; y++)
            for (int x = 1; x < n - 1; x++)
            {
                bool all = true;
                for (int yy = -1; yy <= 1 && all; yy++)
                    for (int xx = -1; xx <= 1; xx++)
                        if (!red[(y + yy) * n + x + xx]) { all = false; break; }
                eroded[y * n + x] = all;
            }
        var opened = new bool[n * n];
        for (int y = 1; y < n - 1; y++)
            for (int x = 1; x < n - 1; x++)
            {
                bool any = false;
                for (int yy = -1; yy <= 1 && !any; yy++)
                    for (int xx = -1; xx <= 1; xx++)
                        if (eroded[(y + yy) * n + x + xx]) { any = true; break; }
                opened[y * n + x] = any;
            }

        int thin = 0;
        for (int i = 0; i < red.Length; i++) if (red[i] && !opened[i]) thin++;
        return (double)thin / total;
    }

    // ---------- marques "!" ----------

    /// <summary>
    /// Compte les traits blancs (`!`). Le seuil de blanc est relatif au fond de la zone (mediane + 60, entre 95 et
    /// <paramref name="brightness"/>) : les marques du HUD survivant sont attenuees (~125) et un fond sombre doit les laisser passer.
    /// Les emplacements sombres (crochet pas encore subi) ne sont jamais comptes.
    /// </summary>
    private static int CountMarks(Frame f, Zone z, int brightness)
    {
        var values = new List<float>(z.W * z.H);
        for (int y = z.Y; y < z.Y + z.H; y++)
            for (int x = z.X; x < z.X + z.W; x++)
                values.Add(MinChannel(f, x, y));
        if (values.Count == 0) return 0;
        values.Sort();
        float median = values[values.Count / 2];
        float threshold = Math.Min(brightness, Math.Max(95f, median + 60f));

        // Un trait = une colonne ou les pixels clairs forment une suite VERTICALE continue (>= 40 % de la hauteur) ;
        // un groupe de colonnes consecutives = une marque, et elle doit etre fine (<= 6 px a l'echelle 1.0) :
        // les taches claires du decor (mousse, briques) sont larges ou decoupees et ne passent pas.
        double k = z.H / 26.0;
        int minRun = (int)Math.Max(6, Math.Round(0.4 * z.H));
        int maxWidth = (int)Math.Ceiling(6 * k);
        int groups = 0, width = 0, gap = 0;
        for (int x = z.X; x <= z.X + z.W; x++)
        {
            bool stroke = false;
            if (x < z.X + z.W)
            {
                int run = 0, best = 0;
                for (int y = z.Y; y < z.Y + z.H; y++)
                {
                    if (MinChannel(f, x, y) >= threshold) { run++; best = Math.Max(best, run); } else run = 0;
                }
                stroke = best >= minRun;
            }
            if (stroke) { width += gap + 1; gap = 0; }       // 1 colonne creuse (anticrenelage) ne coupe pas un trait
            else if (width > 0 && ++gap >= 2)
            {
                if (width <= maxWidth) groups++;
                width = 0; gap = 0;
            }
        }
        if (width > 0 && width <= maxWidth) groups++;
        return Math.Min(groups, 3);
    }
}
