using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Shapes;
using DbdAssistant.Core;

namespace DbdAssistant.App;

/// <summary>
/// Overlay transparent plein ecran, par-dessus le jeu : un anneau colore autour de chaque portrait
/// (couleur = etat), les crochets subis (2 pastilles) et un emplacement reserve sous le portrait
/// pour les futurs timers. La souris traverse la fenetre, et elle est exclue de la capture d'ecran
/// (sinon l'app lirait ses propres dessins).
/// </summary>
public sealed class OverlayWindow : Window
{
    private const int GWL_EXSTYLE = -20;
    private const int WS_EX_TRANSPARENT = 0x20, WS_EX_TOOLWINDOW = 0x80, WS_EX_NOACTIVATE = 0x08000000;
    private const uint WDA_EXCLUDEFROMCAPTURE = 0x11;

    [DllImport("user32.dll")] private static extern int GetWindowLong(IntPtr hwnd, int index);
    [DllImport("user32.dll")] private static extern int SetWindowLong(IntPtr hwnd, int index, int value);
    [DllImport("user32.dll")] private static extern bool SetWindowDisplayAffinity(IntPtr hwnd, uint affinity);

    private sealed class Slot
    {
        public required Ellipse Ring;
        public required Ellipse[] Pips;
        public required Border TimerSlot; // reserve pour les timers (vide pour l'instant)
    }

    private readonly Canvas _canvas = new();
    private readonly Slot[] _slots = new Slot[4];

    /// <summary>Faux si Windows n'a pas pu exclure l'overlay de la capture (Windows trop ancien).</summary>
    public bool ExcludedFromCapture { get; private set; }

    public OverlayWindow()
    {
        WindowStyle = WindowStyle.None;
        AllowsTransparency = true;
        Background = Brushes.Transparent;
        ShowInTaskbar = false;
        ShowActivated = false;
        Topmost = true;
        ResizeMode = ResizeMode.NoResize;
        Content = _canvas;
        for (int i = 0; i < 4; i++) _slots[i] = BuildSlot();
    }

    private Slot BuildSlot()
    {
        var ring = new Ellipse { StrokeThickness = 4, Fill = Brushes.Transparent, Visibility = Visibility.Collapsed };
        var pips = new[] { MakePip(), MakePip() };
        var timer = new Border
        {
            CornerRadius = new CornerRadius(3), Visibility = Visibility.Collapsed,
            // Emplacement futur des barres de timer : invisible tant qu'il n'y a pas de timer.
        };
        _canvas.Children.Add(ring);
        foreach (var p in pips) _canvas.Children.Add(p);
        _canvas.Children.Add(timer);
        return new Slot { Ring = ring, Pips = pips, TimerSlot = timer };
    }

    private static Ellipse MakePip() => new()
    {
        Stroke = new SolidColorBrush(Color.FromRgb(0x10, 0x10, 0x14)), StrokeThickness = 1.5,
        Visibility = Visibility.Collapsed,
    };

    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        var hwnd = new WindowInteropHelper(this).Handle;
        // Click-through, sans activation, hors barre des taches.
        SetWindowLong(hwnd, GWL_EXSTYLE, GetWindowLong(hwnd, GWL_EXSTYLE) | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE);
        ExcludedFromCapture = SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE);
    }

    /// <summary>Couvre l'ecran principal (dimensions en pixels de la capture).</summary>
    public void Fit(int pixelWidth, int pixelHeight)
    {
        var dpi = VisualTreeHelper.GetDpi(this);
        Left = 0; Top = 0;
        Width = pixelWidth / dpi.DpiScaleX;
        Height = pixelHeight / dpi.DpiScaleY;
    }

    /// <summary>Met a jour un survivant. Les zones sont en pixels ecran.</summary>
    public void Update(int index, SurvivorZones z, SurvivorState state, int hooks, Color color)
    {
        var dpi = VisualTreeHelper.GetDpi(this);
        double sx = 1 / dpi.DpiScaleX, sy = 1 / dpi.DpiScaleY;
        var s = _slots[index];

        bool show = state != SurvivorState.Unknown;
        s.Ring.Visibility = show ? Visibility.Visible : Visibility.Collapsed;
        bool dim = state is SurvivorState.Dead or SurvivorState.Mori or SurvivorState.Escaped;
        s.Ring.Opacity = dim ? 0.5 : 0.95;
        s.Ring.Stroke = new SolidColorBrush(color);

        // Anneau legerement autour du portrait.
        double pad = 4 * sx;
        s.Ring.Width = z.Disc.W * sx + 2 * pad;
        s.Ring.Height = z.Disc.H * sy + 2 * pad;
        Canvas.SetLeft(s.Ring, z.Disc.X * sx - pad);
        Canvas.SetTop(s.Ring, z.Disc.Y * sy - pad);

        // 2 pastilles de crochets, en bas a droite du portrait (plein = crochet subi).
        double d = Math.Max(8, z.Disc.W * sx * 0.17);
        double px = (z.Disc.X + z.Disc.W) * sx - d * 2.3, py = (z.Disc.Y + z.Disc.H) * sy - d * 0.6;
        for (int i = 0; i < 2; i++)
        {
            var pip = s.Pips[i];
            pip.Visibility = show ? Visibility.Visible : Visibility.Collapsed;
            pip.Width = pip.Height = d;
            pip.Fill = i < hooks ? new SolidColorBrush(Color.FromRgb(0xe5, 0x48, 0x48)) : new SolidColorBrush(Color.FromArgb(0x90, 0x20, 0x20, 0x26));
            Canvas.SetLeft(pip, px + i * (d + 2 * sx));
            Canvas.SetTop(pip, py);
        }

        // Emplacement des timers : sous le portrait, meme largeur (rien d'affiche pour l'instant).
        s.TimerSlot.Width = z.Disc.W * sx;
        s.TimerSlot.Height = Math.Max(6, z.Disc.H * sy * 0.12);
        Canvas.SetLeft(s.TimerSlot, z.Disc.X * sx);
        Canvas.SetTop(s.TimerSlot, (z.Disc.Y + z.Disc.H) * sy + pad);
    }
}
