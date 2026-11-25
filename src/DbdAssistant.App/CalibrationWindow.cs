using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Shapes;
using DbdAssistant.Core;
using Frame = DbdAssistant.Core.Frame;

namespace DbdAssistant.App;

/// <summary>
/// Calibration en 2 clics : on affiche une capture figee du jeu, l'utilisateur clique au centre du 1er
/// puis du 4e portrait. Les 4 zones deduites sont dessinees pour verification, Entree valide.
/// </summary>
public sealed class CalibrationWindow : Window
{
    private readonly Frame _frame;
    private readonly Canvas _canvas;
    private readonly TextBlock _message;
    private readonly List<Point> _clicks = new();
    private PortraitCalibration? _pending;

    public PortraitCalibration? Result { get; private set; }

    public CalibrationWindow(Frame frame)
    {
        _frame = frame;
        WindowStyle = WindowStyle.None;
        WindowState = WindowState.Maximized;
        Background = Brushes.Black;
        Title = "Calibration des portraits";

        var image = new Image
        {
            Source = BitmapSource.Create(frame.Width, frame.Height, 96, 96, PixelFormats.Bgra32, null, frame.Bgra, frame.Width * 4),
            Width = frame.Width, Height = frame.Height,
        };
        // Le canevas fait la taille exacte de la capture : la position du clic = le pixel de la capture.
        _canvas = new Canvas { Width = frame.Width, Height = frame.Height, Cursor = Cursors.Cross };
        _canvas.Children.Add(image);
        _canvas.MouseLeftButtonDown += OnClick;

        _message = new TextBlock
        {
            Foreground = Brushes.White, FontSize = 18, Padding = new Thickness(14, 8, 14, 8),
            Background = new SolidColorBrush(Color.FromArgb(220, 0, 0, 0)),
            HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Top,
            Margin = new Thickness(0, 12, 0, 0), IsHitTestVisible = false, TextWrapping = TextWrapping.Wrap,
        };

        var grid = new Grid();
        grid.Children.Add(new Viewbox { Stretch = Stretch.Uniform, Child = _canvas });
        grid.Children.Add(_message);
        Content = grid;

        KeyDown += OnKey;
        Reset();
    }

    private void Reset()
    {
        _clicks.Clear();
        _pending = null;
        for (int i = _canvas.Children.Count - 1; i >= 1; i--) _canvas.Children.RemoveAt(i); // garde l'image
        _message.Text = "Clique au centre du PREMIER portrait de survivant (celui du haut).   Echap = annuler";
    }

    private void OnClick(object sender, MouseButtonEventArgs e)
    {
        if (_pending != null) { Reset(); return; } // clic apres l'apercu = on recommence
        var p = e.GetPosition(_canvas);
        _clicks.Add(p);
        AddDot(p, Brushes.Lime);

        if (_clicks.Count == 1)
        {
            _message.Text = "Maintenant clique au centre du QUATRIEME portrait (celui du bas).";
            return;
        }

        var (a, b) = (_clicks[0], _clicks[1]);
        if (!PortraitCalibration.IsPlausible(a.X, a.Y, b.X, b.Y, _frame.Height, out string reason))
        {
            Reset();
            _message.Text = reason + "   Recommence : clique sur le PREMIER portrait.";
            return;
        }

        // Le x est la moyenne des deux clics ; les cercles servent de verification visuelle.
        _pending = PortraitCalibration.FromPixels((a.X + b.X) / 2, a.Y, b.Y, _frame.Height);
        DrawZones(_pending);
        _message.Text = "Les 4 cercles verts sont-ils bien centres sur les portraits ?\nEntree = valider      Clic = recommencer      Echap = annuler";
    }

    private void DrawZones(PortraitCalibration cal)
    {
        foreach (var s in PortraitLayout.Compute(_frame.Height, cal))
        {
            AddShape(new Ellipse { Width = s.Disc.W, Height = s.Disc.H }, s.Disc, Brushes.Lime);
            AddShape(new Rectangle { Width = s.Marks.W, Height = s.Marks.H }, s.Marks, Brushes.Yellow);
            AddShape(new Rectangle { Width = s.Bar1.W, Height = s.Bar1.H }, s.Bar1, Brushes.Cyan);
            AddShape(new Rectangle { Width = s.Bar2.W, Height = s.Bar2.H }, s.Bar2, Brushes.Cyan);
        }
    }

    private void AddShape(Shape shape, Zone z, Brush stroke)
    {
        shape.Stroke = stroke; shape.StrokeThickness = 2; shape.IsHitTestVisible = false;
        Canvas.SetLeft(shape, z.X); Canvas.SetTop(shape, z.Y);
        _canvas.Children.Add(shape);
    }

    private void AddDot(Point p, Brush fill)
    {
        var dot = new Ellipse { Width = 8, Height = 8, Fill = fill, IsHitTestVisible = false };
        Canvas.SetLeft(dot, p.X - 4); Canvas.SetTop(dot, p.Y - 4);
        _canvas.Children.Add(dot);
    }

    private void OnKey(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Escape) { DialogResult = false; }
        else if (e.Key == Key.Enter && _pending != null) { Result = _pending; DialogResult = true; }
    }
}
