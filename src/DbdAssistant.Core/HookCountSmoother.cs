namespace DbdAssistant.Core;

/// <summary>
/// Stabilise le nombre de crochets lu sur les marques "!". La lecture brute oscille (0, 1, 0, 1...)
/// quand un "!" est flou ou masque. Regles :
///  - le nombre monte des qu'une valeur est lue sur au moins 8 des 20 dernieres images ;
///  - il ne redescend que si la valeur n'a plus ete vue du tout depuis 60 images (~6 s) :
///    en partie, le nombre de crochets ne diminue jamais, sauf nouvelle partie.
/// </summary>
public sealed class HookCountSmoother
{
    private const int UpWindow = 20, UpNeeded = 8, DownWindow = 60;
    private readonly Queue<int> _history = new();
    private int _stable;

    public int Stable => _stable;

    public int Update(int raw)
    {
        _history.Enqueue(raw);
        while (_history.Count > DownWindow) _history.Dequeue();

        var all = _history.ToArray();
        var recent = all.Skip(Math.Max(0, all.Length - UpWindow)).ToArray();

        int candidate = 0;
        for (int v = 3; v >= 1; v--)
            if (recent.Count(x => x >= v) >= UpNeeded) { candidate = v; break; }

        if (candidate > _stable) _stable = candidate;
        else if (_stable > 0 && all.Length >= DownWindow && !all.Any(x => x >= _stable))
            _stable = candidate; // plus vu du tout : retombe
        return _stable;
    }
}
