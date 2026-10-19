# -*- coding: utf-8 -*-
"""
HARMONIC BOARD — Pemindai Harmonic Pattern harian saham IDX
Pola   : Bat, Alt Bat, Gartley, Butterfly (Bullish & Bearish)
Swing  : ZigZag berbasis ATR (swing terkunci jika harga berbalik >= k x ATR)
Jalankan: streamlit run harmonic_board.py
Butuh   : streamlit>=1.50, yfinance, pandas, numpy, plotly
"""
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

try:
    import yfinance as yf
except ImportError:
    yf = None


# =============================================================================
# 0. TEMA GELAP (dibuat otomatis sekali; restart Streamlit agar tabel ikut gelap)
# =============================================================================
def ensure_dark_config():
    path = os.path.join(os.getcwd(), ".streamlit", "config.toml")
    if os.path.exists(path):
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                '[theme]\nbase = "dark"\nprimaryColor = "#00ff9c"\n'
                'backgroundColor = "#06080b"\nsecondaryBackgroundColor = "#0d1218"\n'
                'textColor = "#d7e0ea"\nfont = "monospace"\n'
            )
    except Exception:
        pass


ensure_dark_config()

# =============================================================================
# 1. PARAMETER POLA (keputusan final)
# =============================================================================
PATTERNS = {
    #            rentang B (xXA)         D utama   SL         PRZ tambahan
    "Alt Bat":   dict(b=(0.300, 0.382), d=1.130, sl=1.272, extra=[0.886]),
    "Bat":       dict(b=(0.382, 0.500), d=0.886, sl=1.130, extra=[]),
    "Gartley":   dict(b=(0.588, 0.648), d=0.786, sl=1.000, extra=[]),
    "Butterfly": dict(b=(0.756, 0.816), d=1.272, sl=1.414, extra=[]),
}
C_RANGE = (0.382, 0.886)            # C terhadap AB (semua pola)
BC_EXT = (1.618, 2.0, 2.24, 2.618)  # kandidat ekstensi BC untuk konfluensi PRZ
TP_RATIOS = (0.382, 0.618)          # TP1, TP2 = retracement AD

STATUS_ORDER = {"Di PRZ": 0, "Menuju PRZ": 1, "Gagal": 2}

DEFAULT_UNIVERSE = """
AADI AALI ABBA ABDA ABMM ACES ACRO ACST ADCP ADES ADHI ADMF ADMG ADMR ADRO AEGS AGAR AGII AGRO
AGRS AHAP AIMS AISA AKKU AKPI AKRA AKSI ALDO ALII ALKA ALMI ALTO AMAG AMAN AMAR AMFG AMIN AMMN
AMMS AMOR AMRT ANDI ANJT ANTM APEX APIC APII APLI APLN ARCI AREA ARGO ARII ARKA ARKO ARMY ARNA
ARTA ARTI ARTO ASBI ASDM ASGR ASHA ASII ASJT ASLC ASLI ASMI ASPI ASRI ASRM ASSA ATAP ATIC ATLA
AUTO AVIA AWAN AXIO AYAM AYLS BABP BABY BACA BAIK BAJA BALI BANK BAPA BAPI BATA BATR BAUT BAYU
BBCA BBHI BBKP BBLD BBMD BBNI BBRI BBRM BBSI BBSS BBTN BBYB BCAP BCIC BCIP BDKR BDMN BEBS BEEF
BEER BEKS BELI BELL BESS BEST BFIN BGTG BHAT BHIT BIKA BIKE BIMA BINA BINO BIPI BIPP BIRD BISI
BJBR BJTM BKDP BKSL BKSW BLES BLTA BLTZ BLUE BMAS BMBL BMHS BMRI BMSR BMTR BNBA BNBR BNGA BNII
BNLI BOAT BOBA BOGA BOLA BOLT BOSS BPFI BPII BPTR BRAM BREN BRIS BRMS BRNA BRPT BRRC BSBK BSDE
BSIM BSML BSSR BSWD BTEK BTEL BTON BTPN BTPS BUAH BUDI BUKA BUKK BULL BUMI BUVA BVIC BWPT BYAN
CAKK CAMP CANI CARE CARS CASA CASH CASS CBDK CBMF CBPE CBRE CBUT CCSI CEKA CENT CFIN CGAS CHEM
CHIP CINT CITA CITY CLAY CLEO CLPI CMNP CMNT CMPP CMRY CNKO CNMA CNTX COAL COCO COWL CPIN CPRI
CPRO CRAB CRSN CSAP CSIS CSMI CSRA CTBN CTRA CTTH CUAN CYBR DAAZ DADA DART DATA DAYA DCII DEAL
DEFI DEPO DEWA DEWI DFAM DGIK DGNS DGWG DIGI DILD DIVA DKFT DLTA DMAS DMMX DMND DNAR DNET DOID
DOOH DOSS DPNS DPUM DRMA DSFI DSNG DSSA DUCK DUTI DVLA DWGL DYAN EAST ECII EDGE EKAD ELIT ELPI
ELSA ELTY EMDE EMTK ENAK ENRG ENVY ENZO EPAC EPMT ERAA ERAL ERTX ESIP ESSA ESTA ESTI ETWA EURO
EXCL FAPA FAST FASW FILM FIMP FIRE FISH FITT FLMC FMII FOLK FOOD FORU FORZ FPNI FREN FUJI FUTR
FWCT GAMA GDST GDYR GEMA GEMS GGRM GGRP GHON GIAA GJTL GLOB GLVA GMFI GMTD GOLD GOLF GOLL GOOD
GOTO GPRA GPSO GRIA GRPH GRPM GSMF GTBO GTRA GTSI GULA GUNA GWSA GZCO HADE HAIS HAJJ HALO HATM
HBAT HDFA HDIT HDTX HEAL HELI HERO HEXA HGII HILL HITS HKMU HMSP HOKI HOME HOMI HOPE HOTL HRME
HRTA HRUM HUMI HYGN IATA IBFN IBOS IBST ICBP ICON IDEA IDPR IFII IFSH IGAR IIKP IKAI IKAN IKBI
IKPM IMAS IMJS IMPC INAF INAI INCF INCI INCO INDF INDO INDR INDS INDX INDY INET INKP INOV INPC
INPP INPS INRU INTA INTD INTP IOTF IPAC IPCC IPCM IPOL IPPE IPTV IRRA IRSX ISAP ISAT ISEA ISSP
ITIC ITMA ITMG JARR JAST JATI JAWA JAYA JECC JGLE JIHD JKON JKSW JMAS JPFA JRPT JSKY JSMR JSPT
JTPE KAEF KARW KAYU KBAG KBLI KBLM KBLV KBRI KDSI KDTN KEEN KEJU KETR KIAS KICI KIJA KING KINO
KIOS KJEN KKES KKGI KLAS KLBF KLIN KMDS KMTR KOBX KOCI KOIN KOKA KONI KOPI KOTA KPAL KPAS KPIG
KRAH KRAS KREN KRYA KSIX KUAS LABA LABS LAJU LAND LAPD LCGP LCKM LEAD LFLO LIFE LINK LION LIVE
LMAS LMAX LMPI LMSH LOPI LPCK LPGI LPIN LPKR LPLI LPPF LPPS LRNA LSIP LTLS LUCK LUCY MABA MAGP
MAHA MAIN MAMI MANG MAPA MAPB MAPI MARI MARK MASA MASB MAXI MAYA MBAP MBMA MBSS MBTO MCAS MCOL
MCOR MDIA MDIY MDKA MDKI MDLN MDRN MEDC MEDS MEGA MEJA MENN MERK META MFIN MFMI MGLV MGNA MGRO
MHKI MICE MIDI MIKA MINA MIRA MITI MKAP MKNT MKPI MKTR MLBI MLIA MLPL MLPT MMIX MMLP MNCN MOLI
MORA MPIX MPMX MPOW MPPA MPRO MPXL MRAT MREI MSIE MSIN MSJA MSKY MSTI MTDL MTEL MTFN MTLA MTMH
MTPS MTRA MTSM MTWI MUTU MYOH MYOR MYRX MYTX NAIK NANO NASA NASI NATO NAYZ NCKL NELY NEST NETV
NFCX NICE NICK NICL NIKL NINE NIPS NIRO NISP NOBU NPGF NRCA NSSS NTBK NUSA NZIA OASA OBAT OBMD
OCAP OILS OKAS OLIV OMED OMRE OPMS PACK PADA PADI PALM PAMG PANI PANR PANS PART PBID PBRX PBSA
PCAR PDES PDPP PEGE PEHA PEVE PGAS PGEO PGJO PGLI PGUN PICO PIPA PJAA PKPK PLAN PLAS PLIN PMJS
PMMP PNBN PNBS PNGO PNIN PNLF PNSE POLA POLI POLL POLU POLY POOL PORT POSA POWR PPGL PPRE PPRI
PPRO PRAS PRAY PRDA PRIM PSAB PSDN PSGO PSKT PSSI PTBA PTDU PTIS PTMP PTMR PTPP PTPS PTPW PTRO
PTSN PTSP PUDP PURA PURE PURI PWON PYFA PZZA RAAM RAFI RAJA RALS RANC RATU RBMS RCCC RDTX REAL
RELF RELI RGAS RICY RIGS RIMO RISE RMKE RMKO ROCK RODA RONY ROTI RSCH RSGK RUIS RUNS SAFE SAGE
SAME SAMF SAPX SATU SBAT SBMA SCCO SCMA SCNP SCPI SDMU SDPC SDRA SEMA SFAN SGER SGRO SHID SHIP
SICO SIDO SILO SIMA SIMP SINI SIPD SKBM SKLT SKRN SKYB SLIS SMAR SMBR SMCB SMDM SMDR SMGA SMGR
SMIL SMKL SMKM SMLE SMMA SMMT SMRA SMRU SMSM SNLK SOCI SOFA SOHO SOLA SONA SOSS SOTS SOUL SPMA
SPRE SPTO SQMI SRAJ SRIL SRSN SRTG SSIA SSMS SSTM STAA STAR STRK STTP SUGI SULI SUNI SUPR SURE
SURI SWAT SWID TALF TAMA TAMU TAPG TARA TAXI TAYS TBIG TBLA TBMS TCID TCPI TDPM TEBE TECH TELE
TFAS TFCO TGKA TGRA TGUK TIFA TINS TIRA TIRT TKIM TLDN TLKM TMAS TMPO TNCA TOBA TOOL TOPS TOSK
TOTL TOTO TOWR TOYS TPIA TPMA TRAM TRGU TRIL TRIM TRIN TRIO TRIS TRJA TRON TRST TRUE TRUK TRUS
TSPC TUGU TYRE UANG UCID UDNG UFOE ULTJ UNIC UNIQ UNIT UNSP UNTD UNTR UNVR URBN UVCR VAST VERN
VICI VICO VINS VISI VIVA VKTR VOKS VRNA VTNY WAPO WEGE WEHA WGSH WICO WIDI WIFI WIIM WIKA WINE
WINR WINS WIRG WMPP WMUU WOMF WOOD WOWS WSBP WSKT WTON YELO YOII YPAS YULE ZATA ZBRA ZINC ZONE
ZYRX
"""

# =============================================================================
# 2. INDIKATOR & ZIGZAG
# =============================================================================
def atr_wilder(h, l, c, n=14):
    pc = np.roll(c, 1)
    pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().values


def zigzag_atr(h, l, atr, mult):
    """
    Swing dikunci bila harga berbalik >= mult x ATR dari titik ekstrem sementara.
    Return: pivots = [(idx, harga, 'H'/'L'), ...] yang sudah terkunci,
            tentative = (idx, harga, 'H'/'L') ekstrem berjalan yang belum terkunci.
    """
    n = len(h)
    valid = np.where(~np.isnan(atr))[0]
    if len(valid) == 0:
        return [], None
    s = valid[0]
    piv = []
    trend = 0
    hi, hi_i, lo, lo_i = h[s], s, l[s], s
    ext, ext_i = None, None

    for i in range(s + 1, n):
        th = mult * atr[i]
        if trend == 0:
            if h[i] > hi:
                hi, hi_i = h[i], i
            if l[i] < lo:
                lo, lo_i = l[i], i
            if lo_i < i and h[i] - lo >= th:
                piv.append((lo_i, lo, "L"))
                seg = h[lo_i + 1:i + 1]
                k = int(np.argmax(seg))
                ext, ext_i, trend = seg[k], lo_i + 1 + k, 1
            elif hi_i < i and hi - l[i] >= th:
                piv.append((hi_i, hi, "H"))
                seg = l[hi_i + 1:i + 1]
                k = int(np.argmin(seg))
                ext, ext_i, trend = seg[k], hi_i + 1 + k, -1
        elif trend == 1:
            if h[i] > ext:
                ext, ext_i = h[i], i
            elif ext - l[i] >= th:
                piv.append((ext_i, ext, "H"))
                seg = l[ext_i + 1:i + 1]
                k = int(np.argmin(seg))
                ext, ext_i, trend = seg[k], ext_i + 1 + k, -1
        else:
            if l[i] < ext:
                ext, ext_i = l[i], i
            elif h[i] - ext >= th:
                piv.append((ext_i, ext, "L"))
                seg = h[ext_i + 1:i + 1]
                k = int(np.argmax(seg))
                ext, ext_i, trend = seg[k], ext_i + 1 + k, 1

    tent = None
    if trend != 0:
        tent = (ext_i, ext, "H" if trend == 1 else "L")
    return piv, tent


# =============================================================================
# 3. DETEKSI POLA
# =============================================================================
def classify_b(br):
    for name, p in PATTERNS.items():
        lo, hi = p["b"]
        if name == "Bat":
            if lo < br <= hi:          # 0.382 < B <= 0.50
                return name
        elif lo <= br <= hi:
            return name
    return None


def build_zone(a, xa, c, bc_len, r):
    """Zona PRZ dalam ruang 'terorientasi' (selalu seperti pola bullish)."""
    xa_lvl = a - r * xa
    best_e, best_lvl = None, None
    for e in BC_EXT:
        lvl = c - e * bc_len
        if best_lvl is None or abs(lvl - xa_lvl) < abs(best_lvl - xa_lvl):
            best_e, best_lvl = e, lvl
    return dict(r=r, xa_lvl=xa_lvl, bc_e=best_e, bc_lvl=best_lvl,
                top=max(xa_lvl, best_lvl), bot=min(xa_lvl, best_lvl))


def detect_patterns(df, atr_len=14, mult=1.5, max_age=40, stats=None):
    if stats is None:
        stats = {}
    for k in ("jendela", "lolos_c", "lolos_b", "lolos_umur", "aktif"):
        stats.setdefault(k, 0)
    h = df["High"].values.astype(float)
    l = df["Low"].values.astype(float)
    c = df["Close"].values.astype(float)
    n = len(df)
    atr = atr_wilder(h, l, c, atr_len)
    piv, tent = zigzag_atr(h, l, atr, mult)
    out = []

    # C = swing terkunci terakhir (D sedang berjalan) atau sebelum terakhir (D sudah terkunci)
    for ci in (len(piv) - 1, len(piv) - 2):
        if ci < 3:
            continue
        X, A, B, C = piv[ci - 3:ci + 1]
        s = 1 if X[2] == "L" else -1          # 1 = bullish (D = titik beli), -1 = bearish
        x, a, b, cc = s * X[1], s * A[1], s * B[1], s * C[1]
        xa, ab = a - x, a - b
        if xa <= 0 or ab <= 0:
            continue
        stats["jendela"] += 1
        br = ab / xa
        cr = (cc - b) / ab
        if not (C_RANGE[0] <= cr <= C_RANGE[1]):
            continue
        stats["lolos_c"] += 1
        name = classify_b(br)
        if name is None:
            continue
        stats["lolos_b"] += 1
        age = (n - 1) - C[0]
        if age > max_age:
            continue
        stats["lolos_umur"] += 1

        p = PATTERNS[name]
        bc_len = cc - b
        zones = [build_zone(a, xa, cc, bc_len, p["d"])] + \
                [build_zone(a, xa, cc, bc_len, r) for r in p["extra"]]
        entry = a - p["d"] * xa
        sl = a - p["sl"] * xa
        tp1 = entry + TP_RATIOS[0] * (a - entry)
        tp2 = entry + TP_RATIOS[1] * (a - entry)

        low_or = l if s == 1 else -h            # sisi "menuju D" dalam ruang terorientasi
        path = low_or[C[0] + 1:]
        if len(path) == 0:
            continue
        pmin = float(path.min())
        reach_top = max(z["top"] for z in zones)

        d_locked = (ci == len(piv) - 2)
        if pmin < sl:
            status = "Gagal"
        elif pmin <= reach_top:
            status = "Di PRZ"
        else:
            status = "Menuju PRZ"
        if d_locked and status == "Menuju PRZ":
            continue  # D berbalik sebelum menyentuh PRZ -> pola batal
        stats["aktif"] += 1

        cur = s * c[-1]
        dists = []
        for z in zones:
            if z["bot"] <= cur <= z["top"]:
                dists.append(0.0)
            else:
                edge = z["top"] if cur > z["top"] else z["bot"]
                dists.append(abs(cur - edge) / abs(cur) * 100)
        dist = np.nan if status == "Gagal" else min(dists)
        rr = (tp2 - entry) / (entry - sl) if entry > sl else np.nan

        def real(v):
            return s * v

        rz = []
        for z in zones:
            rz.append(dict(r=z["r"], bc_e=z["bc_e"],
                           xa_lvl=real(z["xa_lvl"]), bc_lvl=real(z["bc_lvl"]),
                           lo=min(real(z["top"]), real(z["bot"])),
                           hi=max(real(z["top"]), real(z["bot"]))))

        out.append(dict(
            pattern=name, arah="Bullish" if s == 1 else "Bearish", status=status,
            X=X, A=A, B=B, C=C, D=piv[-1] if d_locked else None, d_locked=d_locked,
            b_ratio=br, c_ratio=cr, zones=rz,
            entry=real(entry), sl=real(sl), tp1=real(tp1), tp2=real(tp2),
            rr=rr, dist=dist, age=age, price=float(c[-1]),
            pivots=piv, tent=tent,
        ))
    return out


# =============================================================================
# 4. DATA
# =============================================================================
def parse_codes(text):
    raw = text.replace(",", " ").replace(";", " ").replace("\n", " ").split()
    codes = []
    for t in raw:
        t = t.strip().upper().replace(".JK", "")
        if t.isalnum() and 2 <= len(t) <= 6 and t not in codes:
            codes.append(t)
    return codes


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def load_data(codes, period="2y"):
    data = {}
    if yf is None:
        return data
    codes = list(codes)
    for k in range(0, len(codes), 80):
        chunk = codes[k:k + 80]
        syms = [t + ".JK" for t in chunk]
        try:
            raw = yf.download(syms, period=period, interval="1d", group_by="ticker",
                              auto_adjust=False, threads=True, progress=False)
        except Exception:
            continue
        if raw is None or raw.empty:
            continue
        for t, sym in zip(chunk, syms):
            try:
                d = raw[sym] if isinstance(raw.columns, pd.MultiIndex) else raw
                d = d[["Open", "High", "Low", "Close", "Volume"]].dropna()
            except Exception:
                continue
            d = d[d["Volume"] > 0]
            if len(d) < 80:
                continue
            idx = pd.to_datetime(d.index)
            if idx.tz is not None:
                idx = idx.tz_localize(None)
            d.index = idx
            data[t] = d.copy()
    return data


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def run_scan(codes, atr_len, mult, max_age):
    data = load_data(codes)
    rows, detail = [], {}
    stats = {}
    for t, df in data.items():
        try:
            pats = detect_patterns(df, atr_len, mult, max_age, stats)
        except Exception:
            continue
        val_min = float((df["Close"] * df["Volume"]).tail(20).min()) / 1e9
        for j, p in enumerate(pats):
            rid = f"{t}|{p['pattern']}|{p['arah']}|{j}"
            detail[rid] = p
            z0 = p["zones"][0]
            rows.append({
                "_id": rid, "Kode": t, "Pola": p["pattern"], "Arah": p["arah"],
                "Status": p["status"], "Harga": p["price"],
                "Jarak PRZ %": p["dist"], "PRZ Bawah": z0["lo"], "PRZ Atas": z0["hi"],
                "Entry D": p["entry"], "SL": p["sl"], "TP1": p["tp1"], "TP2": p["tp2"],
                "R:R TP2": p["rr"], "B/XA": p["b_ratio"], "C/AB": p["c_ratio"],
                "Umur C": p["age"], "D Terkunci": "Ya" if p["d_locked"] else "-",
                "Value Min 20H (M)": val_min,
            })
    return pd.DataFrame(rows), detail, len(data), stats


# =============================================================================
# 5. GRAFIK
# =============================================================================
COL = dict(bg="#06080b", panel="#0b1016", grid="#141c25", text="#c9d4df",
           green="#00ff9c", red="#ff4d6d", amber="#ffb000", cyan="#22d3ee",
           violet="#a78bfa", dim="#4b5a6a")


def make_chart(code, df, p):
    n = len(df)
    start = max(0, p["X"][0] - 30)
    proj = 20
    d = df.iloc[start:]
    xs = np.arange(start, n)
    dates = d.index.strftime("%d %b %y")
    accent = COL["cyan"] if p["arah"] == "Bullish" else COL["amber"]

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=xs, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"],
        increasing=dict(line=dict(color=COL["green"], width=1), fillcolor=COL["green"]),
        decreasing=dict(line=dict(color=COL["red"], width=1), fillcolor=COL["red"]),
        name="Harga", customdata=dates,
        hovertext=[f"{dt}" for dt in dates], hoverinfo="text+y",
    ))

    # ZigZag lengkap (redup)
    zz = [q for q in p["pivots"] if q[0] >= start]
    if p["tent"] and p["tent"][0] >= start:
        zz = zz + [p["tent"]]
    if zz:
        fig.add_trace(go.Scatter(x=[q[0] for q in zz], y=[q[1] for q in zz], mode="lines",
                                 line=dict(color=COL["dim"], width=1, dash="dot"),
                                 name="ZigZag", hoverinfo="skip"))

    X, A, B, C = p["X"], p["A"], p["B"], p["C"]
    z0 = p["zones"][0]
    if p["D"] is not None:
        D = (p["D"][0], p["D"][1])
        d_dash = "solid"
    else:
        D = (n - 1 + proj // 2, p["entry"])
        d_dash = "dash"

    # Segitiga XAB dan BCD
    fill = "rgba(34,211,238,0.10)" if p["arah"] == "Bullish" else "rgba(255,176,0,0.10)"
    for pts in ([X, A, B], [B, C, D]):
        fig.add_trace(go.Scatter(x=[q[0] for q in pts] + [pts[0][0]],
                                 y=[q[1] for q in pts] + [pts[0][1]],
                                 fill="toself", fillcolor=fill, line=dict(width=0),
                                 hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=[X[0], A[0], B[0], C[0]], y=[X[1], A[1], B[1], C[1]],
                             mode="lines+markers", line=dict(color=accent, width=2),
                             marker=dict(size=7, color=accent), name=p["pattern"],
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[C[0], D[0]], y=[C[1], D[1]], mode="lines",
                             line=dict(color=accent, width=2, dash=d_dash),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[X[0], B[0]], y=[X[1], B[1]], mode="lines",
                             line=dict(color=accent, width=1, dash="dot"),
                             showlegend=False, hoverinfo="skip"))

    # Label titik
    bull = p["arah"] == "Bullish"
    for lab, q in zip("XABCD", [X, A, B, C, D]):
        is_low = (lab in "XBD") if bull else (lab in "AC")
        fig.add_annotation(x=q[0], y=q[1], text=f"<b>{lab}</b>", showarrow=False,
                           yshift=-16 if is_low else 16,
                           font=dict(color=COL["text"], size=14))

    # Rasio di tengah kaki
    def mid(a_, b_):
        return (a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2
    for (q1, q2, txt) in [(X, B, f"{p['b_ratio']:.3f} XA"), (B, C, f"{p['c_ratio']:.3f} AB")]:
        mx, my = mid(q1, q2)
        fig.add_annotation(x=mx, y=my, text=txt, showarrow=False,
                           font=dict(color=accent, size=11),
                           bgcolor="rgba(6,8,11,0.8)")

    # Kotak PRZ
    x1 = n - 1 + proj
    zone_cols = ["rgba(167,139,250,0.28)", "rgba(167,139,250,0.14)"]
    for k, z in enumerate(p["zones"]):
        fig.add_shape(type="rect", x0=C[0], x1=x1, y0=z["lo"], y1=z["hi"],
                      fillcolor=zone_cols[min(k, 1)], line=dict(color=COL["violet"], width=1))
        fig.add_annotation(x=x1, y=z["hi"], xanchor="right", yanchor="bottom", showarrow=False,
                           text=f"PRZ {z['r']} XA · BC {z['bc_e']}",
                           font=dict(color=COL["violet"], size=11))

    # SL / TP
    for lvl, lab, colr in [(p["sl"], "SL", COL["red"]), (p["tp1"], "TP1", COL["green"]),
                           (p["tp2"], "TP2", COL["green"]), (p["entry"], "ENTRY D", COL["violet"])]:
        fig.add_shape(type="line", x0=C[0], x1=x1, y0=lvl, y1=lvl,
                      line=dict(color=colr, width=1, dash="dash"))
        fig.add_annotation(x=x1, y=lvl, xanchor="left", showarrow=False,
                           text=f" {lab} {lvl:,.0f}", font=dict(color=colr, size=11))

    # Sumbu X: indeks bar dengan label tanggal
    step = max(1, len(xs) // 8)
    tv = list(xs[::step])
    tt = [df.index[i].strftime("%d %b %y") for i in tv]
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=COL["bg"], plot_bgcolor=COL["panel"],
        font=dict(family="JetBrains Mono, Consolas, monospace", color=COL["text"], size=12),
        height=640, margin=dict(l=10, r=90, t=40, b=10),
        title=dict(text=f"{code} · {p['pattern']} {p['arah']} · {p['status']}",
                   font=dict(color=accent, size=15)),
        xaxis=dict(rangeslider=dict(visible=False), tickvals=tv, ticktext=tt,
                   gridcolor=COL["grid"], range=[start - 2, x1 + 12]),
        yaxis=dict(gridcolor=COL["grid"], side="right", tickformat=",.0f"),
        showlegend=False, hovermode="x unified",
    )
    return fig


# =============================================================================
# 6. ANTARMUKA
# =============================================================================
st.set_page_config(page_title="Harmonic Board", page_icon="◆", layout="wide")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&display=swap');
.stApp {{ background: radial-gradient(1200px 600px at 10% -10%, #0e1a14 0%, {COL['bg']} 55%); }}
.stApp, .stMarkdown, p, label, input, textarea, button, h1, h2, h3, h4,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{
  font-family: 'JetBrains Mono', Consolas, monospace !important; }}
section[data-testid="stSidebar"] {{ background:#080b10; border-right:1px solid #18212b; }}
.hb-head {{ border:1px solid #1a2430; border-left:4px solid {COL['green']};
  background:linear-gradient(90deg, rgba(0,255,156,0.06), rgba(0,0,0,0));
  padding:14px 18px; margin-bottom:14px; }}
.hb-title {{ color:{COL['green']}; font-size:26px; font-weight:800; letter-spacing:2px; }}
.hb-sub {{ color:{COL['dim']}; font-size:12px; letter-spacing:1px; }}
.hb-blink {{ color:{COL['green']}; animation: blink 1.1s steps(1) infinite; }}
@keyframes blink {{ 50% {{ opacity:0; }} }}
.hb-card {{ border:1px solid #1a2430; background:{COL['panel']}; padding:10px 14px; }}
.hb-card .k {{ color:{COL['dim']}; font-size:11px; letter-spacing:1px; }}
.hb-card .v {{ font-size:24px; font-weight:800; }}
div.stButton > button {{ background:#0d1a14; color:{COL['green']}; border:1px solid {COL['green']};
  border-radius:2px; letter-spacing:1px; }}
div.stButton > button:hover {{ background:{COL['green']}; color:#000; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="hb-head">
  <div class="hb-title">◆ HARMONIC BOARD <span class="hb-blink">█</span></div>
  <div class="hb-sub">IDX // DAILY // ZIGZAG ATR // BAT · ALT BAT · GARTLEY · BUTTERFLY</div>
</div>""", unsafe_allow_html=True)

if yf is None:
    st.error("Paket yfinance belum terpasang. Jalankan: pip install yfinance")
    st.stop()

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### ▌UNIVERSE")
    src = st.radio("Sumber kode saham", ["Daftar bawaan", "Tempel daftar", "Unggah file"],
                   label_visibility="collapsed")
    codes = parse_codes(DEFAULT_UNIVERSE)
    if src == "Tempel daftar":
        txt = st.text_area("Kode dipisah spasi/koma/baris", height=120)
        if txt.strip():
            codes = parse_codes(txt)
    elif src == "Unggah file":
        up = st.file_uploader("File .txt / .csv berisi kode", type=["txt", "csv"])
        if up is not None:
            codes = parse_codes(up.read().decode("utf-8", errors="ignore"))
    st.caption(f"{len(codes)} kode siap dipindai")

    st.markdown("### ▌MESIN ZIGZAG")
    atr_len = st.number_input("Periode ATR", 5, 50, 14, 1)
    mult = st.number_input("Kunci swing (x ATR)", 0.5, 5.0, 1.5, 0.1)
    max_age = st.slider("Umur maks. titik C (hari bursa)", 5, 120, 40)

    run = st.button("▶ PINDAI ULANG", width="stretch")
    if run:
        load_data.clear()
        run_scan.clear()

    st.markdown("### ▌FILTER")
    f_pola = st.multiselect("Pola", list(PATTERNS.keys()), default=list(PATTERNS.keys()))
    f_arah = st.multiselect("Arah", ["Bullish", "Bearish"], default=["Bullish", "Bearish"])
    f_status = st.multiselect("Status", list(STATUS_ORDER.keys()),
                              default=["Di PRZ", "Menuju PRZ"])
    f_dist = st.slider("Jarak maks. ke PRZ (%)", 0.0, 50.0, 15.0, 0.5)
    f_val = st.number_input("Value transaksi minimum harian 20H (miliar)", 0.0, 1000.0, 5.0, 1.0)

# ---------------- Pindai ----------------
with st.spinner("Menarik data & menghitung swing..."):
    table, detail, n_loaded = run_scan(tuple(codes), int(atr_len), float(mult), int(max_age))

if table.empty:
    st.warning(f"Data termuat: {n_loaded} saham. Belum ada pola yang terdeteksi dengan parameter ini.")
    st.stop()

view = table[
    table["Pola"].isin(f_pola) & table["Arah"].isin(f_arah) & table["Status"].isin(f_status)
    & (table["Value Min 20H (M)"] >= f_val)
    & ((table["Jarak PRZ %"] <= f_dist) | table["Jarak PRZ %"].isna())
].copy()
view["_s"] = view["Status"].map(STATUS_ORDER)
view = view.sort_values(["_s", "Jarak PRZ %"], na_position="last").drop(columns="_s")
view = view.reset_index(drop=True)

# ---------------- Kartu ringkasan ----------------
cards = [("SAHAM TERMUAT", n_loaded, COL["text"]),
         ("DI PRZ", int((view["Status"] == "Di PRZ").sum()), COL["violet"]),
         ("MENUJU PRZ", int((view["Status"] == "Menuju PRZ").sum()), COL["cyan"]),
         ("GAGAL", int((view["Status"] == "Gagal").sum()), COL["red"])]
cols = st.columns(4)
for col, (k, v, colr) in zip(cols, cards):
    col.markdown(f'<div class="hb-card" style="border-left:3px solid {colr}">'
                 f'<div class="k">{k}</div><div class="v" style="color:{colr}">{v}</div></div>',
                 unsafe_allow_html=True)
st.markdown("")

# ---------------- Tabel ----------------
ids = view["_id"].tolist()
show = view.drop(columns="_id")


def color_status(v):
    return {"Di PRZ": f"color:{COL['violet']};font-weight:700",
            "Menuju PRZ": f"color:{COL['cyan']};font-weight:700",
            "Gagal": f"color:{COL['red']};font-weight:700"}.get(v, "")


def color_arah(v):
    return f"color:{COL['green']}" if v == "Bullish" else f"color:{COL['amber']}"


styled = show.style.map(color_status, subset=["Status"]).map(color_arah, subset=["Arah"])

num0 = st.column_config.NumberColumn(format="%.0f")
num2 = st.column_config.NumberColumn(format="%.2f")
num3 = st.column_config.NumberColumn(format="%.3f")
fkey = f"tbl_{hash((tuple(f_pola), tuple(f_arah), tuple(f_status), f_dist, f_val, atr_len, mult, max_age, len(codes)))}"

st.caption("Klik baris untuk membuka grafik pola.")
event = st.dataframe(
    styled, hide_index=True, width="stretch", height=520,
    on_select="rerun", selection_mode="single-row", key=fkey,
    column_config={
        "Harga": num0, "PRZ Bawah": num0, "PRZ Atas": num0, "Entry D": num0,
        "SL": num0, "TP1": num0, "TP2": num0, "Jarak PRZ %": num2, "R:R TP2": num2,
        "B/XA": num3, "C/AB": num3, "Value Min 20H (M)": st.column_config.NumberColumn(format="%.1f"),
    },
)


@st.dialog("DETAIL POLA", width="large")
def show_detail(rid):
    p = detail[rid]
    code = rid.split("|")[0]
    df = load_data(tuple(codes))[code]
    m = st.columns(6)
    m[0].metric("Status", p["status"])
    m[1].metric("Entry D", f"{p['entry']:,.0f}")
    m[2].metric("SL", f"{p['sl']:,.0f}")
    m[3].metric("TP1", f"{p['tp1']:,.0f}")
    m[4].metric("TP2", f"{p['tp2']:,.0f}")
    m[5].metric("R:R TP2", f"{p['rr']:.2f}" if pd.notna(p["rr"]) else "-")
    st.plotly_chart(make_chart(code, df, p), width="stretch",
                    config={"displaylogo": False, "scrollZoom": True})

    def dt(q):
        return df.index[q[0]].strftime("%d %b %Y")
    rows = [["X", dt(p["X"]), p["X"][1], "-"],
            ["A", dt(p["A"]), p["A"][1], "-"],
            ["B", dt(p["B"]), p["B"][1], f"{p['b_ratio']:.3f} XA"],
            ["C", dt(p["C"]), p["C"][1], f"{p['c_ratio']:.3f} AB"]]
    if p["D"] is not None:
        rows.append(["D", dt(p["D"]), p["D"][1], "terkunci"])
    else:
        rows.append(["D", "proyeksi", p["entry"], f"{PATTERNS[p['pattern']]['d']} XA"])
    c1, c2 = st.columns(2)
    c1.markdown("**Titik swing**")
    c1.dataframe(pd.DataFrame(rows, columns=["Titik", "Tanggal", "Harga", "Rasio"]),
                 hide_index=True, width="stretch",
                 column_config={"Harga": st.column_config.NumberColumn(format="%.0f")})
    zr = [[f"{z['r']} XA", z["xa_lvl"], f"BC {z['bc_e']}", z["bc_lvl"], z["lo"], z["hi"]]
          for z in p["zones"]]
    c2.markdown("**Konfluensi PRZ**")
    c2.dataframe(pd.DataFrame(zr, columns=["Level XA", "Harga XA", "Ekstensi", "Harga BC",
                                           "Bawah", "Atas"]),
                 hide_index=True, width="stretch",
                 column_config={k: st.column_config.NumberColumn(format="%.0f")
                                for k in ["Harga XA", "Harga BC", "Bawah", "Atas"]})


rows_sel = event.selection.rows if event and hasattr(event, "selection") else []
if rows_sel:
    rid = ids[rows_sel[0]]
    if st.session_state.get("_open") != rid:
        st.session_state["_open"] = rid
        show_detail(rid)
else:
    st.session_state["_open"] = None

st.caption("Data: Yahoo Finance (harian, 2 tahun). Swing terakhir ZigZag selalu sementara sampai "
           "harga berbalik ≥ k×ATR; status dihitung ulang tiap pindai.")
