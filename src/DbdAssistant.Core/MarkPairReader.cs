namespace DbdAssistant.Core;

/// <summary>
/// Lit les marques de crochets du HUD SURVIVANT. Ce HUD dessine toujours DEUX emplacements voisins (~8 px d'ecart) :
/// clair = crochet deja subi, sombre = libre. On cherche donc une PAIRE de traits fins (clair ou sombre), de meme
/// hauteur et de meme position verticale, a ce bon ecartement, et on compte les traits clairs de la paire.
/// Un bord isole du decor (manteau, brique...) n'a ni le bon partenaire ni la bonne forme et est ignore.
/// Repli : un trait blanc tres net, seul (partenaire sombre invisible sur fond sombre), juste apres le rond d'action.
/// </summary>
public static class MarkPairReader
{
    private sealed record Stroke(double X, bool Bright, double Y0, double Y1, double Strength);

    public static double BrightContrast { get; set; } = 20;  // un trait clair depasse le fond d'au moins ca (luminosite)
    public static double DarkContrast { get; set; } = 12;    // un trait sombre est plus sombre que le fond d'au moins ca
    public static double LoneContrast { get; set; } = 40;    // un trait blanc seul doit etre nettement plus clair que le fond

    /// <returns>Nombre de crochets subis (0..2), ou 0 si aucune marque n'est reconnue.</returns>
    public static int Count(Frame f, Zone z, out string debug)
    {
        int w = z.W, h = z.H;
        double k = Math.Max(0.5, h / 26.0);          // echelle de l'interface (zone de 26 px a l'echelle 1.0)
        var luma = new float[w * h];
        var sorted = new List<float>(w * h);
        for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
            {
                int sx = z.X + x, sy = z.Y + y;
                float l = 0;
                if (sx >= 0 && sy >= 0 && sx < f.Width && sy < f.Height)
                {
                    int i = (sy * f.Width + sx) * 4;
                    l = 0.114f * f.Bgra[i] + 0.587f * f.Bgra[i + 1] + 0.299f * f.Bgra[i + 2];
                }
                luma[y * w + x] = l; sorted.Add(l);
            }
        sorted.Sort();
        float bg = sorted[sorted.Count / 2];

        int minRun = (int)Math.Max(6, Math.Round(0.4 * h));
        int maxRun = (int)Math.Round(0.8 * h);
        int maxWidth = (int)Math.Ceiling(4 * k);

        // Par colonne : meilleure suite verticale claire et sombre (longueur, debut, contraste moyen).
        var cls = new int[w]; var y0s = new int[w]; var y1s = new int[w]; var str = new double[w];
        for (int x = 0; x < w; x++)
        {
            int rb = 0, bb = 0, bbStart = 0, rd = 0, bd = 0, bdStart = 0; double sumB = 0, bestSumB = 0, sumD = 0, bestSumD = 0;
            for (int y = 0; y < h; y++)
            {
                float l = luma[y * w + x];
                if (l >= bg + BrightContrast) { rb++; sumB += l - bg; if (rb > bb) { bb = rb; bbStart = y - rb + 1; bestSumB = sumB; } } else { rb = 0; sumB = 0; }
                if (l <= bg - DarkContrast) { rd++; sumD += bg - l; if (rd > bd) { bd = rd; bdStart = y - rd + 1; bestSumD = sumD; } } else { rd = 0; sumD = 0; }
            }
            if (bb >= minRun && bb <= maxRun) { cls[x] = 1; y0s[x] = bbStart; y1s[x] = bbStart + bb - 1; str[x] = bestSumB / bb; }
            else if (bd >= minRun && bd <= maxRun) { cls[x] = -1; y0s[x] = bdStart; y1s[x] = bdStart + bd - 1; str[x] = bestSumD / bd; }
        }

        // Groupes de colonnes consecutives de meme classe = traits (fins).
        var strokes = new List<Stroke>();
        for (int x = 0; x < w;)
        {
            if (cls[x] == 0) { x++; continue; }
            int c = cls[x], x0 = x;
            while (x < w && cls[x] == c) x++;
            int n = x - x0;
            if (n > maxWidth) continue;
            double y0 = 0, y1 = 0, s = 0;
            for (int q = x0; q < x; q++) { y0 += y0s[q]; y1 += y1s[q]; s += str[q]; }
            strokes.Add(new Stroke((x0 + x - 1) / 2.0, c == 1, y0 / n, y1 / n, s / n));
        }
        debug = $"bg={bg:0} strokes=" + string.Join(",", strokes.Select(s => $"{(s.Bright ? "B" : "d")}{s.X:0}[{s.Y0:0}-{s.Y1:0} c{s.Strength:0}]"));

        // Paire : ~8 px d'ecart, memes extremites verticales (+/- 4 px), a un endroit ou les marques peuvent commencer.
        double dmin = 6 * k, dmax = 10 * k, ytol = 4 * k;
        double darkPairStrength = -1;
        for (int i = 0; i < strokes.Count; i++)
            for (int j = i + 1; j < strokes.Count; j++)
            {
                var a = strokes[i]; var b = strokes[j];
                double d = b.X - a.X;
                if (d < dmin || d > dmax || !ValidStart(a.X, k)) continue;
                if (Math.Abs(a.Y0 - b.Y0) > ytol || Math.Abs(a.Y1 - b.Y1) > ytol) continue;
                if (a.Bright || b.Bright) return (a.Bright ? 1 : 0) + (b.Bright ? 1 : 0);
                darkPairStrength = Math.Max(darkPairStrength, Math.Min(a.Strength, b.Strength));
            }

        // Repli : un trait blanc net et seul (partenaire sombre invisible sur fond sombre), juste apres le rond d'action.
        // Une paire de traits sombres NETTE l'emporte (deux emplacements libres) ; une paire sombre faible (bruit) non.
        double lone = -1;
        foreach (var s in strokes)
            if (s.Bright && s.Strength >= LoneContrast && ValidStart(s.X, k)) lone = Math.Max(lone, s.Strength);
        return lone > 0 && lone > darkPairStrength ? 1 : 0;
    }

    /// <summary>Les marques commencent juste apres le rond d'action (x ~ 0..16) ou juste apres l'icone de statut (x ~ 32..50).</summary>
    private static bool ValidStart(double x, double k) => x <= 16 * k || (x >= 32 * k && x <= 50 * k);
}
