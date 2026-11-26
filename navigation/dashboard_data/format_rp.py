# navigation/dashboard_data/format_rp.py
"""Format angka Rupiah singkat, dipakai semua dashboard.

Aturan:  >= 1 triliun -> T | >= 1 miliar -> M | >= 1 juta -> JT | >= 1 ribu -> RB | di bawah itu angka biasa.
Contoh:  fmt_rp(399_760_000_000) -> 'Rp 399.76 M'   fmt_rp(428_000_000) -> 'Rp 428.00 JT'   fmt_rp(7_500) -> 'Rp 7.50 RB'
"""
import math

_UNITS = ((1e12, "T"), (1e9, "M"), (1e6, "JT"), (1e3, "RB"))


def _kosong(x):
    return x is None or (isinstance(x, float) and math.isnan(x)) or (isinstance(x, float) and math.isinf(x))


def fmt_rp(x, prefix="Rp ", dec=2, trim=False):
    """Rupiah singkat. trim=True membuang nol di belakang koma (12.50 -> 12.5, 3.00 -> 3)."""
    if _kosong(x):
        return "-"
    x = float(x)
    sign = "-" if x < 0 else ""
    a = abs(x)
    for i, (lim, suf) in enumerate(_UNITS):
        if a >= lim:
            v = round(a / lim, dec)
            if v >= 1000 and i > 0:          # 999.999 JT dibulatkan -> 1.00 M, bukan 1000.00 JT
                lim, suf = _UNITS[i - 1]
                v = round(a / lim, dec)
            s = f"{v:,.{dec}f}"
            if trim and "." in s:
                s = s.rstrip("0").rstrip(".")
            return f"{sign}{prefix}{s} {suf}"
    s = f"{a:,.0f}"
    return f"{sign}{prefix}{s}"


def fmt_num(x, dec=0):
    """Angka biasa dengan pemisah ribuan (jumlah SKU, faktur, dll)."""
    return "-" if _kosong(x) else f"{float(x):,.{dec}f}"


def fmt_hari(x, dec=1):
    return "-" if _kosong(x) else f"{float(x):,.{dec}f} hari"


def fmt_pct(x, dec=1, tanda=False):
    if _kosong(x):
        return "-"
    return f"{float(x):+,.{dec}f}%" if tanda else f"{float(x):,.{dec}f}%"


def rp_ticks(vmin, vmax, n=6):
    """Tick sumbu Plotly berlabel T/M/JT/RB.  Pakai:
        tv, tt = rp_ticks(0, df['omset'].max())
        fig.update_yaxes(tickvals=tv, ticktext=tt)
    Nilai data tetap dalam Rupiah penuh."""
    if _kosong(vmin) or _kosong(vmax) or vmax <= vmin:
        return None, None
    raw = (vmax - vmin) / max(n, 2)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start = math.floor(vmin / step) * step
    vals, v = [], start
    while v <= vmax + step * 0.5:
        vals.append(v); v += step
    return vals, [fmt_rp(t, prefix="", dec=1, trim=True) if t != 0 else "0" for t in vals]