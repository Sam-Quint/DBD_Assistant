using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using DbdAssistant.Core;

namespace DbdAssistant.App;

public partial class MainWindow : Window
{
    private ScreenCapturer? _capturer;
    private Frame? _frame;
    private WriteableBitmap? _bitmap;
    private readonly DispatcherTimer _timer = new() { Interval = TimeSpan.FromMilliseconds(100) }; // 10 FPS
    private readonly Stopwatch _clock = Stopwatch.StartNew();
    private int _frames;

    public MainWindow()
    {
        InitializeComponent();
        try
        {
            _capturer = new ScreenCapturer();
            InfoText.Text = $"Ecran principal : {_capturer.Width}x{_capturer.Height}";
        }
        catch (Exception ex)
        {
            InfoText.Text = "Capture impossible";
            WarningText.Text = ex.Message;
            SaveButton.IsEnabled = false;
            return;
        }
        _timer.Tick += (_, _) => Tick();
        _timer.Start();
        Closed += (_, _) => _capturer?.Dispose();
    }

    private void Tick()
    {
        var frame = _capturer!.Capture(0);
        if (frame == null) return;
        _frame = frame;

        if (_bitmap == null || _bitmap.PixelWidth != frame.Width || _bitmap.PixelHeight != frame.Height)
        {
            _bitmap = new WriteableBitmap(frame.Width, frame.Height, 96, 96, PixelFormats.Bgra32, null);
            Preview.Source = _bitmap;
        }
        _bitmap.WritePixels(new Int32Rect(0, 0, frame.Width, frame.Height), frame.Bgra, frame.Width * 4, 0);

        _frames++;
        if (_clock.ElapsedMilliseconds >= 1000)
        {
            double fps = _frames * 1000.0 / _clock.ElapsedMilliseconds;
            _frames = 0;
            _clock.Restart();
            InfoText.Text = $"Ecran principal : {frame.Width}x{frame.Height}  -  {fps:0} images/s";
            WarningText.Text = frame.IsBlack()
                ? "Image noire : le jeu n'est peut-etre pas capturable (plein ecran exclusif ?). Essaie le mode fenetre sans bordure."
                : "";
        }
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
