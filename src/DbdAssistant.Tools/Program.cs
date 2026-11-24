using System.Drawing;
using System.Drawing.Imaging;
using DbdAssistant.Core;

// Outil de dev. Commandes (a lancer depuis DBD_Assistant/) :
//   dotnet run --project src/DbdAssistant.Tools -- annoter   [captures] [sortie]   dessine les zones lues
//   dotnet run --project src/DbdAssistant.Tools -- modeles   [captures]            fabrique templates.bin depuis labels.txt
//   dotnet run --project src/DbdAssistant.Tools -- evaluer   [captures]            teste la reconnaissance (leave-one-capture-out)
string cmd = args.Length > 0 ? args[0] : "annoter";
string capDir = args.Length > 1 ? args[1] : "Captures";
string labelsPath = Path.Combine("src", "DbdAssistant.Tools", "labels.txt");
string templatesPath = Path.Combine("src", "DbdAssistant.Core", "templates.bin");

switch (cmd)
{
    case "annoter": Annoter(capDir, args.Length > 2 ? args[2] : Path.Combine(capDir, "annotees")); break;
    case "modeles": Modeles(capDir); break;
    case "evaluer": Evaluer(capDir); break;
    case "lissage": TestLissage(); break;
    case "lire": Lire(capDir, args.Length > 2 ? args[2] : ""); break;
    default: Console.WriteLine("Commandes : annoter | modeles | evaluer"); break;
}

static Frame LoadFrame(string path)
{
    using var bmp = new Bitmap(path);
    var data = bmp.LockBits(new Rectangle(0, 0, bmp.Width, bmp.Height), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
    try
    {
        var bytes = new byte[bmp.Width * bmp.Height * 4];
        System.Runtime.InteropServices.Marshal.Copy(data.Scan0, bytes, 0, bytes.Length);
        return new Frame { Width = bmp.Width, Height = bmp.Height, Bgra = bytes };
    }
    finally { bmp.UnlockBits(data); }
}

static List<(string capture, int survivor, SurvivorState state)> LoadLabels(string path)
{
    var list = new List<(string, int, SurvivorState)>();
    foreach (var line in File.ReadAllLines(path))
    {
        if (line.StartsWith('#') || string.IsNullOrWhiteSpace(line)) continue;
        var p = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        list.Add((p[0], int.Parse(p[1]), SurvivorStates.FromCode(p[2][0])));
    }
    return list;
}

static void Annoter(string inDir, string outDir)
{
    Directory.CreateDirectory(outDir);
    using var penDisc = new Pen(Color.Lime, 2);
    using var penMarks = new Pen(Color.Yellow, 2);
    using var penBar = new Pen(Color.Cyan, 2);
    var files = Directory.GetFiles(inDir, "*.png").OrderBy(f => f, StringComparer.Ordinal).ToArray();
    foreach (var file in files)
    {
        using var bmp = new Bitmap(file);
        using var g = Graphics.FromImage(bmp);
        foreach (var s in PortraitLayout.Compute(bmp.Height))
        {
            g.DrawEllipse(penDisc, s.Disc.X, s.Disc.Y, s.Disc.W, s.Disc.H);
            g.DrawRectangle(penMarks, s.Marks.X, s.Marks.Y, s.Marks.W, s.Marks.H);
            g.DrawRectangle(penBar, s.Bar1.X, s.Bar1.Y, s.Bar1.W, s.Bar1.H);
            g.DrawRectangle(penBar, s.Bar2.X, s.Bar2.Y, s.Bar2.W, s.Bar2.H);
        }
        bmp.Save(Path.Combine(outDir, Path.GetFileName(file)), ImageFormat.Png);
    }
    Console.WriteLine($"{files.Length} image(s) annotee(s) -> {Path.GetFullPath(outDir)}");
}

static void Modeles(string capDir)
{
    var labels = LoadLabels(Path.Combine("src", "DbdAssistant.Tools", "labels.txt"));
    var items = new List<Template>();
    foreach (var group in labels.GroupBy(l => l.capture))
    {
        string file = Path.Combine(capDir, group.Key + ".png");
        if (!File.Exists(file)) { Console.WriteLine($"Capture absente : {file}"); continue; }
        var frame = LoadFrame(file);
        var zones = PortraitLayout.Compute(frame.Height);
        foreach (var (cap, s, state) in group)
        {
            if (!SurvivorStates.IsIconState(state)) continue; // visages et barres : pas de modele
            items.Add(Template.Create(state, cap, StateRecognizer.ExtractRawPatch(frame, zones[s])));
        }
    }
    var lib = new TemplateLibrary(items);
    using (var fs = File.Create(Path.Combine("src", "DbdAssistant.Core", "templates.bin"))) lib.Save(fs);
    Console.WriteLine($"{items.Count} modele(s) ecrit(s) dans src/DbdAssistant.Core/templates.bin");
    foreach (var g in items.GroupBy(i => i.State)) Console.WriteLine($"  {SurvivorStates.Label(g.Key),-12} {g.Count()}");
}

static void Evaluer(string capDir)
{
    var lib = TemplateLibrary.Load(File.OpenRead(Path.Combine("src", "DbdAssistant.Core", "templates.bin")));
    var rec = new StateRecognizer(lib);
    var labels = LoadLabels(Path.Combine("src", "DbdAssistant.Tools", "labels.txt"));
    var confusion = new Dictionary<(SurvivorState truth, SurvivorState got), int>();
    var errors = new List<string>();
    int ok = 0, total = 0;
    var detail = new List<(SurvivorState truth, SurvivorReading r)>();

    foreach (var group in labels.GroupBy(l => l.capture))
    {
        var frame = LoadFrame(Path.Combine(capDir, group.Key + ".png"));
        var zones = PortraitLayout.Compute(frame.Height);
        foreach (var (cap, s, truth) in group)
        {
            var r = rec.Read(frame, zones[s], excludeSource: cap); // jamais ses propres modeles
            detail.Add((truth, r));
            total++;
            if (r.State == truth) ok++;
            else errors.Add($"  {cap[^6..]}.{s}  attendu {SurvivorStates.Label(truth),-11} lu {SurvivorStates.Label(r.State),-11} icone={SurvivorStates.Label(r.BestIcon)} {r.IconScore:0.00}  griffures={r.Scratch:0.000}  jaune={r.YellowBar}");
            confusion[(truth, r.State)] = confusion.GetValueOrDefault((truth, r.State)) + 1;
        }
    }

    Console.WriteLine($"Exactitude : {ok}/{total} = {100.0 * ok / total:0.0} %  (modeles de la meme capture exclus)\n");
    Console.WriteLine("Par etat (attendu -> lu) :");
    foreach (var truth in confusion.Keys.Select(k => k.truth).Distinct().OrderBy(s => s))
    {
        int n = confusion.Where(k => k.Key.truth == truth).Sum(k => k.Value);
        int good = confusion.GetValueOrDefault((truth, truth));
        string other = string.Join(", ", confusion.Where(k => k.Key.truth == truth && k.Key.got != truth).Select(k => $"{SurvivorStates.Label(k.Key.got)} x{k.Value}"));
        Console.WriteLine($"  {SurvivorStates.Label(truth),-12} {good}/{n}{(other.Length > 0 ? "   erreurs : " + other : "")}");
    }
    if (errors.Count > 0) { Console.WriteLine("\nErreurs :"); errors.ForEach(Console.WriteLine); }

    Console.WriteLine("\nMarques ! lues (nombre de crochets) : repartition par etat attendu");
    foreach (var g in detail.GroupBy(d => d.truth).OrderBy(g => g.Key))
        Console.WriteLine($"  {SurvivorStates.Label(g.Key),-12} " + string.Join("  ", g.GroupBy(d => d.r.HookMarks).OrderBy(x => x.Key).Select(x => $"{x.Key}:{x.Count()}")));

    // Aide au reglage des seuils
    Console.WriteLine("\nScores d'icone (meilleur modele) : min/max par etat attendu");
    foreach (var g in detail.GroupBy(d => d.truth).OrderBy(g => g.Key))
        Console.WriteLine($"  {SurvivorStates.Label(g.Key),-12} icone {g.Min(d => d.r.IconScore):0.00}..{g.Max(d => d.r.IconScore):0.00}   griffures {g.Min(d => d.r.Scratch):0.000}..{g.Max(d => d.r.Scratch):0.000}");
}


static void TestLissage()
{
    static string Run(string name, IEnumerable<int> raw)
    {
        var sm = new HookCountSmoother();
        var outp = raw.Select(sm.Update).ToArray();
        return $"{name,-34} sortie : {string.Join("", outp.Select(x => x.ToString()))}";
    }
    var flicker = Enumerable.Range(0, 60).Select(i => i % 2 == 0 ? 1 : 0).ToList();   // 1,0,1,0...
    var spike = Enumerable.Repeat(0, 30).Concat(new[] { 3, 3 }).Concat(Enumerable.Repeat(0, 40));  // pic parasite
    var real = Enumerable.Repeat(0, 20).Concat(Enumerable.Repeat(1, 40));               // vrai 1er crochet
    var dips = Enumerable.Repeat(1, 30).Concat(new[] { 0, 0, 0, 0, 0 }).Concat(Enumerable.Repeat(1, 30)); // "!" masque 0,5 s
    var two = Enumerable.Repeat(1, 25).Concat(Enumerable.Repeat(2, 30));                 // 1 puis 2
    Console.WriteLine(Run("scintillement 1,0,1,0", flicker));
    Console.WriteLine(Run("pic parasite 3 (2 images)", spike));
    Console.WriteLine(Run("vrai 1er crochet", real));
    Console.WriteLine(Run("! masque 0,5 s", dips));
    Console.WriteLine(Run("1 puis 2 crochets", two));
}

static void Lire(string capDir, string prefix)
{
    var lib = TemplateLibrary.Load(File.OpenRead(Path.Combine("src", "DbdAssistant.Core", "templates.bin")));
    var rec = new StateRecognizer(lib);
    if (Environment.GetEnvironmentVariable("MARK_BRIGHT") is string mb) rec.MarkBrightness = int.Parse(mb);
    foreach (var file in Directory.GetFiles(capDir, prefix + "*.png").OrderBy(f => f, StringComparer.Ordinal))
    {
        var frame = LoadFrame(file);
        var zones = PortraitLayout.Compute(frame.Height);
        var parts = zones.Select(z => rec.Read(frame, z)).Select(r => $"{SurvivorStates.Label(r.State)}{(r.YellowBar ? "[jaune]" : "")}/!{r.HookMarks}");
        Console.WriteLine($"{Path.GetFileNameWithoutExtension(file)[^6..]}  " + string.Join("  |  ", parts));
    }
}
