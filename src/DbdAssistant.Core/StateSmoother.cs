namespace DbdAssistant.Core;

/// <summary>
/// Evite le clignotement : un nouvel etat n'est accepte que s'il est lu sur plusieurs images de suite.
/// </summary>
public sealed class StateSmoother
{
    private readonly int _framesRequired;
    private SurvivorState _stable = SurvivorState.Unknown;
    private SurvivorState _candidate = SurvivorState.Unknown;
    private int _count;

    public StateSmoother(int framesRequired = 3) => _framesRequired = framesRequired;

    public SurvivorState Stable => _stable;

    public SurvivorState Update(SurvivorState read)
    {
        if (read == _stable) { _candidate = read; _count = 0; return _stable; }
        if (read == _candidate) _count++;
        else { _candidate = read; _count = 1; }
        if (_count >= _framesRequired) { _stable = _candidate; _count = 0; }
        return _stable;
    }
}
