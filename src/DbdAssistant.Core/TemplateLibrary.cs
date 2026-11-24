using System.Reflection;

namespace DbdAssistant.Core;

/// <summary>Un modele d'icone : image "blanc minimal" 40x40 d'un etat connu.</summary>
public sealed class Template
{
    public SurvivorState State { get; init; }
    public string Source { get; init; } = "";   // capture d'origine (sert au leave-one-out)
    public float[] Data { get; init; } = Array.Empty<float>(); // zero-mean
    public float Norm { get; init; }

    public static Template Create(SurvivorState state, string source, byte[] raw)
    {
        var data = new float[raw.Length];
        double mean = raw.Average(b => (double)b);
        double sum = 0;
        for (int i = 0; i < raw.Length; i++) { data[i] = (float)(raw[i] - mean); sum += data[i] * data[i]; }
        return new Template { State = state, Source = source, Data = data, Norm = (float)Math.Sqrt(sum), Raw = raw };
    }

    public byte[] Raw { get; init; } = Array.Empty<byte>();
}

/// <summary>Bibliotheque de modeles, stockee dans templates.bin (embarque dans l'exe).</summary>
public sealed class TemplateLibrary
{
    public const int PatchSize = 40;
    public IReadOnlyList<Template> Items { get; }

    public TemplateLibrary(IEnumerable<Template> items) => Items = items.ToList();

    public static TemplateLibrary LoadEmbedded()
    {
        var asm = Assembly.GetExecutingAssembly();
        using var s = asm.GetManifestResourceStream("DbdAssistant.Core.templates.bin")
            ?? throw new InvalidOperationException("templates.bin introuvable dans l'application.");
        return Load(s);
    }

    public static TemplateLibrary Load(Stream stream)
    {
        using var r = new BinaryReader(stream);
        int n = r.ReadInt32();
        var list = new List<Template>(n);
        for (int i = 0; i < n; i++)
        {
            char code = (char)r.ReadByte();
            string source = r.ReadString();
            byte[] raw = r.ReadBytes(PatchSize * PatchSize);
            list.Add(Template.Create(SurvivorStates.FromCode(code), source, raw));
        }
        return new TemplateLibrary(list);
    }

    public void Save(Stream stream)
    {
        using var w = new BinaryWriter(stream);
        w.Write(Items.Count);
        foreach (var t in Items)
        {
            w.Write((byte)SurvivorStates.ToCode(t.State));
            w.Write(t.Source);
            w.Write(t.Raw);
        }
    }
}
