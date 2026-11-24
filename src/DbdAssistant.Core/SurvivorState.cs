namespace DbdAssistant.Core;

public enum SurvivorState
{
    Unknown,
    Healthy,     // H : sain
    Injured,     // I : blesse (griffures)
    DeepWounds,  // W : barre jaune
    Downed,      // D : a terre
    Carried,     // C : porte
    Hooked,      // K : accroche
    Dead,        // X : mort sur crochet (crane qui crie)
    Mori,        // M : mori (crane calme aux yeux rouges)
    Escaped,     // E : sorti
}

public static class SurvivorStates
{
    public static char ToCode(SurvivorState s) => s switch
    {
        SurvivorState.Healthy => 'H',
        SurvivorState.Injured => 'I',
        SurvivorState.DeepWounds => 'W',
        SurvivorState.Downed => 'D',
        SurvivorState.Carried => 'C',
        SurvivorState.Hooked => 'K',
        SurvivorState.Dead => 'X',
        SurvivorState.Mori => 'M',
        SurvivorState.Escaped => 'E',
        _ => '?',
    };

    public static SurvivorState FromCode(char c) => char.ToUpperInvariant(c) switch
    {
        'H' => SurvivorState.Healthy,
        'I' => SurvivorState.Injured,
        'W' => SurvivorState.DeepWounds,
        'D' => SurvivorState.Downed,
        'C' => SurvivorState.Carried,
        'K' => SurvivorState.Hooked,
        'X' => SurvivorState.Dead,
        'M' => SurvivorState.Mori,
        'E' => SurvivorState.Escaped,
        _ => SurvivorState.Unknown,
    };

    public static string Label(SurvivorState s) => s switch
    {
        SurvivorState.Healthy => "Sain",
        SurvivorState.Injured => "Blessé",
        SurvivorState.DeepWounds => "Deep Wounds",
        SurvivorState.Downed => "À terre",
        SurvivorState.Carried => "Porté",
        SurvivorState.Hooked => "Accroché",
        SurvivorState.Dead => "Mort",
        SurvivorState.Mori => "Mori",
        SurvivorState.Escaped => "Sorti",
        _ => "Inconnu",
    };

    /// <summary>Etats reconnus par comparaison avec des modeles d'icones (le reste se lit aux couleurs).</summary>
    public static bool IsIconState(SurvivorState s) =>
        s is SurvivorState.Downed or SurvivorState.Carried or SurvivorState.Hooked
          or SurvivorState.Dead or SurvivorState.Mori or SurvivorState.Escaped;
}
