using System.Runtime.InteropServices;
using Vortice.Direct3D;
using Vortice.Direct3D11;
using Vortice.DXGI;

namespace DbdAssistant.Core;

/// <summary>Une image BGRA 32 bits d'un ecran entier.</summary>
public sealed class Frame
{
    public int Width { get; init; }
    public int Height { get; init; }
    public byte[] Bgra { get; init; } = Array.Empty<byte>();

    /// <summary>Vrai si l'image est (quasi) entierement noire : signe d'un jeu non capturable.</summary>
    public bool IsBlack()
    {
        int step = Math.Max(1, (Width * Height) / 2000);
        for (int p = 0; p < Width * Height; p += step)
        {
            int i = p * 4;
            if (Bgra[i] > 8 || Bgra[i + 1] > 8 || Bgra[i + 2] > 8) return false;
        }
        return true;
    }
}

/// <summary>
/// Lit les pixels de l'ecran principal via DXGI Desktop Duplication.
/// Lecture seule : aucune injection dans le jeu, aucune lecture clavier/souris.
/// </summary>
public sealed class ScreenCapturer : IDisposable
{
    private readonly ID3D11Device _device;
    private readonly ID3D11DeviceContext _context;
    private readonly IDXGIOutputDuplication _duplication;
    private ID3D11Texture2D? _staging;
    private byte[] _buffer = Array.Empty<byte>();
    private Frame? _last;

    public int Width { get; }
    public int Height { get; }

    public ScreenCapturer(uint adapterIndex = 0, uint outputIndex = 0)
    {
        using var factory = DXGI.CreateDXGIFactory1<IDXGIFactory1>();
        factory.EnumAdapters1(adapterIndex, out IDXGIAdapter1? adapter).CheckError();
        using (adapter)
        {
            D3D11.D3D11CreateDevice(adapter, DriverType.Unknown, DeviceCreationFlags.BgraSupport,
                new[] { FeatureLevel.Level_11_0 }, out _device!, out _context!).CheckError();

            adapter!.EnumOutputs(outputIndex, out IDXGIOutput? output).CheckError();
            using (output)
            {
                var rect = output!.Description.DesktopCoordinates;
                Width = rect.Right - rect.Left;
                Height = rect.Bottom - rect.Top;
                using var output1 = output.QueryInterface<IDXGIOutput1>();
                _duplication = output1.DuplicateOutput(_device);
            }
        }
    }

    /// <summary>
    /// Renvoie la derniere image. Si l'ecran n'a pas change depuis le dernier appel,
    /// renvoie l'image precedente. Renvoie null tant qu'aucune image n'a ete recue.
    /// </summary>
    public Frame? Capture(int timeoutMs = 100)
    {
        var result = _duplication.AcquireNextFrame((uint)timeoutMs, out _, out IDXGIResource? resource);
        if (result.Failure)
            return _last; // timeout : l'ecran n'a pas change

        try
        {
            using var texture = resource!.QueryInterface<ID3D11Texture2D>();
            var desc = texture.Description;

            if (_staging == null || _staging.Description.Width != desc.Width || _staging.Description.Height != desc.Height)
            {
                _staging?.Dispose();
                desc.Usage = ResourceUsage.Staging;
                desc.BindFlags = BindFlags.None;
                desc.CPUAccessFlags = CpuAccessFlags.Read;
                desc.MiscFlags = ResourceOptionFlags.None;
                _staging = _device.CreateTexture2D(desc);
                _buffer = new byte[desc.Width * desc.Height * 4];
            }

            _context.CopyResource(_staging, texture);
            var map = _context.Map(_staging, 0u, MapMode.Read);
            try
            {
                int w = (int)_staging.Description.Width, h = (int)_staging.Description.Height;
                int rowBytes = w * 4;
                for (int y = 0; y < h; y++)
                    Marshal.Copy(map.DataPointer + y * (int)map.RowPitch, _buffer, y * rowBytes, rowBytes);
                _last = new Frame { Width = w, Height = h, Bgra = (byte[])_buffer.Clone() };
            }
            finally { _context.Unmap(_staging, 0u); }
        }
        finally
        {
            resource?.Dispose();
            _duplication.ReleaseFrame();
        }
        return _last;
    }

    public void Dispose()
    {
        _staging?.Dispose();
        _duplication.Dispose();
        _context.Dispose();
        _device.Dispose();
    }
}
