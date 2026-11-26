using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using DbdAssistant.Core;
using Frame = DbdAssistant.Core.Frame;

namespace DbdAssistant.App;

public partial class MainWindow : Window
{
    private ScreenCapturer? _capturer;
    private StateRecognizer? _recognizer;
    private readonly StateSmoother[] _smoothers = Enumerable.Range(0, 4).Select(_ => new StateSmoother(3)).ToArray();
    private readonly HookCountSmoother[] _hookSmoothers = Enumerable.Range(0, 4).Select(_ => new HookCountSmoother()).ToArray();
    private readonly TextBlock[] _stateText = new TextBlock[4];
    private readonly TextBlock[] _detailText = new TextBlock[4];
    private readonly Border[] _cards = new Border[4];

    private Frame? _frame;
    private PortraitCalibration? _calibration = PortraitCalibration.Load();
    private HudMode _mode = AppSettings.Load().Mode;
    private WriteableBitmap? _bitmap;
    private readonly DispatcherTimer _timer = new() { Interval = TimeSpan.FromMilliseconds(100) }; // 10 FPS
    private readonly Stopwatch _clock = Stopwatch.StartNew();
    private int _frames;
    private OverlayWindow? _overlay;

    public MainWindow()
    {
        InitializeComponent();

        // Fenetre a droite de l'ecran pour ne pas cacher les portraits (a gauche dans le jeu).
        WindowStartupLocation = WindowStartupLocation.Manual;
        Left = Math.Max(0, SystemParameters.PrimaryScreenWidth - Width);
        Top = 40;

        ModeBox.SelectedIndex = _mode == HudMode.Survivor ? 1 : 0;
        BuildCards();
        try
        {
            _recognizer = new StateRecognizer(TemplateLibrary.LoadEmbedded());
            _capturer = new ScreenCapturer();
            InfoText.Text = $"Ecran principal : {_capturer.Width}x{_capturer.Height}";
        }
        catch (Exception ex)
        {
            InfoText.Text = "Demarrage impossible";
            WarningText.Text = ex.Message;
            SaveButton.IsEnabled = false;
            return;
        }
        _timer.Tick += (_, _) => Tick();
        _timer.Start();
        _overlay = new OverlayWindow();
        _overlay.Show();
        Closed += (_, _) => { _overlay?.Close(); _capturer?.Dispose(); };
    }

    private void BuildCards()
    {
        for (int i = 0; i < 4; i++)
        {
            _stateText[i] = new TextBlock { Text = "-", FontSize = 22, FontWeight = FontWeights.SemiBold, TextWrapping = TextWrapping.Wrap };
            _detailText[i] = new TextBlock { FontSize = 11, Foreground = new SolidColorBrush(Color.FromRgb(0x9a, 0x9a, 0xa2)), TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 6, 0, 0) };
            var panel = new StackPanel();
            panel.Children.Add(new TextBlock { Text = $"Survivant {i + 1}", FontSize = 12, Foreground = new SolidColorBrush(Color.FromRgb(0x9a, 0x9a, 0xa2)) });
            panel.Children.Add(_stateText[i]);
            panel.Children.Add(_detailText[i]);
            _cards[i] = new Border
            {
                Child = panel, Padding = new Thickness(12), Margin = new Thickness(0, 0, i < 3 ? 8 : 0, 0),
                CornerRadius = new CornerRadius(8), Background = new SolidColorBrush(Color.FromRgb(0x26, 0x26, 0x2c)),
                BorderThickness = new Thickness(0, 0, 0, 4), BorderBrush = Brushes.Gray,
            };
            Cards.Children.Add(_cards[i]);
        }
    }

    private static Color ColorOf(SurvivorState s) => s switch
    {
        SurvivorState.Healthy => Color.FromRgb(0x4c, 0xc2, 0x7a),
        SurvivorState.Injured => Color.FromRgb(0xf0, 0x9a, 0x3e),
        SurvivorState.DeepWounds => Color.FromRgb(0xf2, 0xd0, 0x3a),
        SurvivorState.Downed => Color.FromRgb(0xe5, 0x48, 0x48),
        SurvivorState.Carried => Color.FromRgb(0xb0, 0x7c, 0xe6),
        SurvivorState.Hooked => Color.FromRgb(0xe5, 0x48, 0x48),
        SurvivorState.Dead => Color.FromRgb(0x8a, 0x8a, 0x92),
        SurvivorState.Mori => Color.FromRgb(0x8a, 0x8a, 0x92),
        SurvivorState.Escaped => Color.FromRgb(0x4a, 0x9e, 0xf0),
        _ => Color.FromRgb(0x60, 0x60, 0x68),
    };

    private void Tick()
    {
        var frame = _capturer!.Capture(0);
        if (frame == null) return;
        _frame = frame;
        if (_overlay != null && (double.IsNaN(_overlay.Width) || Math.Abs(_overlay.Width * VisualTreeHelper.GetDpi(_overlay).DpiScaleX - frame.Width) > 1))
            _overlay.Fit(frame.Width, frame.Height);

        if (_bitmap == null || _bitmap.PixelWidth != frame.Width || _bitmap.PixelHeight != frame.Height)
        {
            _bitmap = new WriteableBitmap(frame.Width, frame.Height, 96, 96, PixelFormats.Bgra32, null);
            Preview.Source = _bitmap;
        }
        _bitmap.WritePixels(new Int32Rect(0, 0, frame.Width, frame.Height), frame.Bgra, frame.Width * 4, 0);

        var zones = PortraitLayout.Compute(frame.Height, _calibration, _mode);
        for (int i = 0; i < 4; i++)
        {
            var r = _recognizer!.Read(frame, zones[i], null, _mode);
            var state = _smoothers[i].Update(r.State);
            int hooks = _hookSmoothers[i].Update(r.HookMarks);
            var color = ColorOf(state);
            _stateText[i].Text = SurvivorStates.Label(state);
            _stateText[i].Foreground = new SolidColorBrush(color);
            _cards[i].BorderBrush = new SolidColorBrush(color);
            if (OverlayBox.IsChecked == true) _overlay?.Update(i, zones[i], state, hooks, color);
            _detailText[i].Text =
                $"icone : {SurvivorStates.Label(r.BestIcon)} ({r.IconScore:0.00})\n" +
                $"crochets : {hooks}  (brut {r.HookMarks}, a valider)\n" +
                $"griffures : {r.Scratch:0.000}  barre jaune : {(r.YellowBar ? "oui" : "non")}";
        }

        _frames++;
        if (_clock.ElapsedMilliseconds >= 1000)
        {
            double fps = _frames * 1000.0 / _clock.ElapsedMilliseconds;
            _frames = 0;
            _clock.Restart();
            InfoText.Text = $"Ecran principal : {frame.Width}x{frame.Height}  -  {fps:0} images/s";
            WarningText.Text = frame.IsBlack()
                ? "Image noire : le jeu n'est peut-etre pas capturable (plein ecran exclusif ?). Essaie le mode fenetre sans bordure."
                : (_overlay is { ExcludedFromCapture: false } && OverlayBox.IsChecked == true
                    ? "Overlay : Windows n'a pas pu l'exclure de la capture (Windows 10 mai 2020 ou plus requis). Decoche « Overlay » si les lectures se degradent."
                : _calibration == null ? "Portraits non calibres : lance le jeu, puis clique sur « Calibrer les portraits » (2 clics)." : "");
        }
    }

    private void ModeBox_Changed(object sender, SelectionChangedEventArgs e)
    {
        var mode = ModeBox.SelectedIndex == 1 ? HudMode.Survivor : HudMode.Killer;
        if (mode == _mode) return;
        _mode = mode;
        new AppSettings(mode).Save();
    }

    private void OverlayBox_Changed(object sender, RoutedEventArgs e)
    {
        if (_overlay == null) return;
        if (OverlayBox.IsChecked == true) _overlay.Show(); else _overlay.Hide();
    }

    private void CalibrateButton_Click(object sender, RoutedEventArgs e)
    {
        if (_frame == null) return;
        _timer.Stop();
        _overlay?.Hide();
        try
        {
            var win = new CalibrationWindow(_frame) { Owner = this };
            if (win.ShowDialog() == true && win.Result != null)
            {
                _calibration = win.Result;
                _calibration.Save();
            }
        }
        finally { _timer.Start(); if (OverlayBox.IsChecked == true) _overlay?.Show(); }
    }

    private void SaveButton_Click(object sender, RoutedEventArgs e)
    {
        if (_frame == null) return;
        Directory.CreateDirectory("Captures");
        string path = Path.Combine("Captures", $"capture_{DateTime.Now:yyyyMMdd_HHmmss}.png");
        var src = BitmapSource.Create(_frame.Width, _frame.Height, 96, 96, PixelFormats.Bgra32, null, _frame.Bgra, _frame.Width * 4);
        var enc = new PngBitmapEncoder();
        enc.Frames.Add(BitmapFrame.Create(src));
        using var fs = File.Create(path);
        enc.Save(fs);
        InfoText.Text = "Enregistre : " + Path.GetFullPath(path);
    }
}
