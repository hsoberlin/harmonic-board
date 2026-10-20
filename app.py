# -*- coding: utf-8 -*-
"""
HARMONIC BOARD — Pemindai Harmonic Pattern harian saham IDX
Pola   : Bat, Alt Bat, Gartley, Butterfly (Bullish & Bearish)
Swing  : ZigZag berbasis ATR (swing terkunci jika harga berbalik >= k x ATR)
Jalankan: streamlit run app.py
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

STATUS_ORDER = {"Di PRZ": 0, "Menuju PRZ": 1, "Selesai": 2, "Gagal": 3}
C_LOOKBACK = 8   # titik C dicari sampai 8 swing terkunci ke belakang
X_LOOKBACK = 4   # titik X dicari sampai 4 kandidat (swing sejenis) ke belakang

SCALES = {"Kecil (1.5×ATR)": 1.5, "Menengah (3×ATR)": 3.0, "Besar (5×ATR)": 5.0}
SCALE_AGE = {"Kecil (1.5×ATR)": 40, "Menengah (3×ATR)": 80, "Besar (5×ATR)": 150}

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


def idx_tick(price):
    """Fraksi harga BEI."""
    p = abs(price)
    if p < 200:
        return 1
    if p < 500:
        return 2
    if p < 2000:
        return 5
    if p < 5000:
        return 10
    return 25


def round_tick(price, mode):
    """Bulatkan ke fraksi BEI. mode 'down' / 'up'."""
    t = idx_tick(price)
    q = price / t
    v = (np.floor(q + 1e-9) if mode == "down" else np.ceil(q - 1e-9)) * t
    # kalau pembulatan melewati batas rentang fraksi, cek ulang dengan fraksi baru
    t2 = idx_tick(v)
    if t2 != t:
        q = price / t2
        v = (np.floor(q + 1e-9) if mode == "down" else np.ceil(q - 1e-9)) * t2
    return float(v)


def pick_x(piv, ai, s):
    """
    Titik X = awal kaki XA yang 'bersih'. Kaki XA boleh punya pantulan di tengah:
    X dicari sampai X_LOOKBACK kandidat ke belakang (swing sejenis), dan dipilih yang
    paling ekstrem, dengan syarat tidak ada swing di antara X dan A yang melewati X atau A.
    """
    a_or = s * piv[ai][1]
    best = None
    for k in range(X_LOOKBACK):
        xi = ai - 1 - 2 * k
        if xi < 0:
            break
        x_or = s * piv[xi][1]
        mid = [s * q[1] for q in piv[xi + 1:ai]]
        if mid and (min(mid) < x_or or max(mid) > a_or):
            break                      # kaki tidak bersih, kandidat lebih jauh juga gugur
        if best is None or x_or < s * best[1]:
            best = piv[xi]
    return best


def detect_patterns(df, atr_len=14, mult=1.5, max_age=40, stats=None,
                    stop_basis="Low intraday", buf_atr=0.0):
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

    # Kandidat titik C:
    #  - swing terkunci terakhir            -> D sedang berjalan
    #  - swing sebelum terakhir             -> D sudah terkunci (swing terakhir)
    #  - sampai C_LOOKBACK swing ke belakang -> D masih berjalan, kaki CD boleh punya
    #    pantulan di tengah, asal harga belum pernah menembus C (garis Invalid)
    for ci in range(len(piv) - 1, max(2, len(piv) - 1 - C_LOOKBACK), -1):
        if ci < 3:
            continue
        A, B, C = piv[ci - 2:ci + 1]
        s = 1 if A[2] == "H" else -1          # 1 = bullish (D = titik beli), -1 = bearish
        X = pick_x(piv, ci - 2, s)
        if X is None:
            continue
        x, a, b, cc = s * X[1], s * A[1], s * B[1], s * C[1]
        xa, ab = a - x, a - b
        if xa <= 0 or ab <= 0:
            continue
        lookback = ci < len(piv) - 2
        if lookback:
            # Invalid: sisi berlawanan dari kaki CD tidak boleh melewati C
            opp = (h if s == 1 else -l)[C[0] + 1:]
            if len(opp) == 0 or float(opp.max()) > cc:
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

        # Penjaga kewajaran: proyeksi bullish yang jatuh ke harga nol/negatif tidak masuk akal
        if s == 1 and (sl <= 0 or min(z["bot"] for z in zones) <= 0):
            continue
        low_or = l if s == 1 else -h            # sisi "menuju D" dalam ruang terorientasi
        path = low_or[C[0] + 1:]
        if len(path) == 0:
            continue
        pmin = float(path.min())
        # Stop: basis low/high intraday atau close harian, dikurangi buffer x ATR (ATR saat C)
        atr_c = float(atr[C[0]]) if not np.isnan(atr[C[0]]) else float(np.nanmean(atr))
        sl_eff = sl - buf_atr * atr_c
        chk = (s * c[C[0] + 1:]) if stop_basis == "Close harian" else path
        chk_min = float(chk.min())
        hit = np.where(path <= entry)[0]
        touch_idx = int(C[0] + 1 + hit[0]) if len(hit) else None
        reach_top = max(z["top"] for z in zones)

        d_locked = (ci == len(piv) - 2)

        # Urutan kejadian setelah C: sentuh PRZ -> (TP tercapai?) -> (SL jebol?)
        hi_or = (h if s == 1 else -l)[C[0] + 1:]
        t_prz = np.where(path <= reach_top)[0]
        t_sl = np.where(chk < sl_eff)[0]
        t_sl = int(t_sl[0]) if len(t_sl) else None
        tp_hit, t_tp = None, None
        if len(t_prz):
            after = hi_or[t_prz[0]:]
            i1 = np.where(after >= tp1)[0]
            if len(i1):
                t_tp = int(t_prz[0] + i1[0])
                tp_hit = "TP2" if (after >= tp2).any() else "TP1"
        if t_tp is not None and (t_sl is None or t_tp < t_sl):
            status = "Selesai"          # pola sudah berhasil mencapai target
        elif t_sl is not None:
            status = "Gagal"
        elif len(t_prz):
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
        # Posisi harga sekarang terhadap seluruh zona PRZ, dan tembusan terdalam sejak C
        z_top = max(z["top"] for z in zones)
        z_bot = min(z["bot"] for z in zones)
        if cur > z_top:      # sisi asal (belum masuk / sudah memantul keluar)
            posisi = "Di atas PRZ" if s == 1 else "Di bawah PRZ"
        elif cur >= z_bot:
            posisi = "Di dalam PRZ"
        else:                # sisi jauh (menembus zona)
            posisi = "Di bawah PRZ" if s == 1 else "Di atas PRZ"
        tembus = max(0.0, (z_bot - pmin) / abs(z_bot) * 100)

        # Keseimbangan waktu: lama kaki CD dibanding AB (hari bursa)
        ab_bars = int(B[0] - A[0])
        if d_locked:
            cd_bars, cd_jalan = int(piv[-1][0] - C[0]), False
        elif len(t_prz):
            cd_bars, cd_jalan = int(t_prz[0] + 1), False   # sampai pertama menyentuh PRZ
        else:
            cd_bars, cd_jalan = int((n - 1) - C[0]), True
        if cd_jalan:
            waktu_lbl = "berjalan"
            waktu_txt = f"AB {ab_bars} hari · CD berjalan {cd_bars} hari"
        else:
            r_t = cd_bars / max(ab_bars, 1)
            waktu_lbl = ("CD terlalu cepat" if r_t < 0.5 else
                         "CD terlalu lambat" if r_t > 2 else "seimbang")
            waktu_txt = f"AB {ab_bars} hari · CD {cd_bars} hari → {waktu_lbl}"
        catatan = ""
        if status == "Selesai":
            catatan = f"{tp_hit} sudah tercapai"
            if dist <= 5:
                catatan += ", kini kembali ke PRZ" if dist == 0 else ", kini mendekati PRZ lagi"
        rr = (tp2 - entry) / (entry - sl_eff) if entry > sl_eff else np.nan
        # Dari harga sekarang (ruang terorientasi): risiko ke SL efektif, potensi ke TP1/TP2
        risk_now = cur - sl_eff
        rr_now1 = (tp1 - cur) / risk_now if risk_now > 0 and tp1 > cur else np.nan
        rr_now2 = (tp2 - cur) / risk_now if risk_now > 0 and tp2 > cur else np.nan
        to_sl = -risk_now / abs(cur) * 100
        to_tp1 = (tp1 - cur) / abs(cur) * 100
        to_tp2 = (tp2 - cur) / abs(cur) * 100
        jebol = (chk_min - sl) / abs(sl) * 100  # + = belum menyentuh SL pola

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
            entry=real(entry), sl=real(sl), sl_eff=real(sl_eff), tp1=real(tp1), tp2=real(tp2),
            jebol=jebol, stop_basis=stop_basis, buf_atr=buf_atr,
            rr=rr, dist=dist, age=age, price=float(c[-1]), touch_idx=touch_idx,
            tp_hit=tp_hit, catatan=catatan, posisi=posisi, tembus=tembus,
            waktu_lbl=waktu_lbl, waktu_txt=waktu_txt, rr_now1=rr_now1, rr_now2=rr_now2, to_sl=to_sl, to_tp1=to_tp1, to_tp2=to_tp2,
            pivots=piv, tent=tent,
        ))
        apply_ticks(out[-1], s)
    return out


def apply_ticks(p, s):
    """
    Bulatkan level order ke fraksi BEI supaya bisa langsung dipasang di aplikasi sekuritas.
    Bullish: entry ke atas (mudah terisi), TP ke bawah (mudah terisi), SL ke bawah (beri ruang).
    Bearish: kebalikannya. Persentase dan R:R dihitung ulang dari angka yang sudah dibulatkan.
    """
    up, dn = ("up", "down") if s == 1 else ("down", "up")
    p["entry"] = round_tick(p["entry"], up)
    p["tp1"] = round_tick(p["tp1"], dn)
    p["tp2"] = round_tick(p["tp2"], dn)
    p["sl"] = round_tick(p["sl"], dn)
    p["sl_eff"] = round_tick(p["sl_eff"], dn)
    cur = p["price"]
    risk_e = s * (p["entry"] - p["sl_eff"])
    p["rr"] = s * (p["tp2"] - p["entry"]) / risk_e if risk_e > 0 else np.nan
    risk_n = s * (cur - p["sl_eff"])
    r1, r2 = s * (p["tp1"] - cur), s * (p["tp2"] - cur)
    p["rr_now1"] = r1 / risk_n if risk_n > 0 and r1 > 0 else np.nan
    p["rr_now2"] = r2 / risk_n if risk_n > 0 and r2 > 0 else np.nan
    p["to_sl"] = (p["sl_eff"] / cur - 1) * 100
    p["to_tp1"] = (p["tp1"] / cur - 1) * 100
    p["to_tp2"] = (p["tp2"] / cur - 1) * 100


def diagnose(piv):
    """Alasan tidak ada pola, dibaca dari 4 swing terkunci terakhir (C = swing terakhir)."""
    if len(piv) < 4:
        return [f"Baru ada {len(piv)} swing terkunci; butuh minimal 4 (X, A, B, C)."]
    msgs = []
    for ci, tag in ((len(piv) - 1, "Skenario D berjalan"), (len(piv) - 2, "Skenario D terkunci")):
        if ci < 3:
            continue
        A, B, C = piv[ci - 2:ci + 1]
        s = 1 if A[2] == "H" else -1
        X = pick_x(piv, ci - 2, s) or piv[ci - 3]
        x, a, b, cc = s * X[1], s * A[1], s * B[1], s * C[1]
        xa, ab = a - x, a - b
        arah = "bullish" if s == 1 else "bearish"
        if xa <= 0 or ab <= 0:
            msgs.append(f"• {tag}: struktur swing tidak membentuk XA-AB yang sah.")
            continue
        br, cr = ab / xa, (cc - b) / ab
        why = []
        if not (C_RANGE[0] <= cr <= C_RANGE[1]):
            why.append(f"C = {cr:.3f} AB (syarat 0.382–0.886)")
        if classify_b(br) is None:
            extra = " → B menembus X" if br >= 1 else ""
            why.append(f"B = {br:.3f} XA{extra} (syarat: Alt Bat 0.30–0.382, Bat 0.382–0.50, "
                       "Gartley 0.588–0.648, Butterfly 0.756–0.816)")
        if not why:
            why.append(f"rasio lolos (B {br:.3f} XA, C {cr:.3f} AB), tapi kaki D berbalik "
                       "sebelum menyentuh PRZ, jadi pola batal")
        msgs.append(f"• {tag} ({arah}): " + "; ".join(why) + ".")
    return msgs


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


@st.cache_data(ttl=3 * 3600, show_spinner=False)
def load_one(code, period="3y"):
    if yf is None:
        return None
    try:
        d = yf.download(code + ".JK", period=period, interval="1d", auto_adjust=False,
                        progress=False)
    except Exception:
        return None
    if d is None or d.empty:
        return None
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d = d[["Open", "High", "Low", "Close", "Volume"]].dropna()
    d = d[d["Volume"] > 0]
    if len(d) < 60:
        return None
    idx = pd.to_datetime(d.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    d.index = idx
    return d.copy()


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def run_scan(codes, atr_len, mult, max_age, stop_basis="Low intraday", buf_atr=0.0):
    data = load_data(codes)
    rows, detail = [], {}
    stats = {}
    for t, df in data.items():
        try:
            pats = detect_patterns(df, atr_len, mult, max_age, stats, stop_basis, buf_atr)
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
                "Entry D": p["entry"], "SL": p["sl"], "SL Efektif": p["sl_eff"],
                "Jarak ke SL %": p["jebol"], "TP1": p["tp1"], "TP2": p["tp2"],
                "R:R TP2": p["rr"],
                "R:R Rencana": p["rr"] if p["status"] == "Menuju PRZ" else p["rr_now2"],
                "R:R Skrg TP1": p["rr_now1"], "R:R Skrg TP2": p["rr_now2"],
                "Ke SL %": p["to_sl"], "Ke TP2 %": p["to_tp2"], "B/XA": p["b_ratio"], "C/AB": p["c_ratio"],
                "Catatan": p["catatan"], "Waktu": p["waktu_txt"], "Posisi vs PRZ": p["posisi"],
                "Tembus Terdalam %": p["tembus"], "Umur C": p["age"], "D Terkunci": "Ya" if p["d_locked"] else "-",
                "Value Min 20H (M)": val_min,
            })
    return pd.DataFrame(rows), detail, len(data), stats


# =============================================================================
# 5. GRAFIK
# =============================================================================
COL = dict(bg="#06080b", panel="#0b1016", grid="#141c25", text="#c9d4df",
           green="#00ff9c", red="#ff4d6d", amber="#ffb000", cyan="#22d3ee",
           violet="#a78bfa", dim="#4b5a6a")

FONT = "JetBrains Mono, Consolas, monospace"


def _base_layout(fig, df, start, x_end, title, title_color, nticks=7):
    xs = np.arange(start, len(df))
    step = max(1, len(xs) // nticks)
    tv = list(xs[step // 2::step])  # geser dari tepi kiri agar label pertama tidak terpotong
    tt, prev_y = [], None
    for i in tv:
        d = df.index[i]
        lab = d.strftime("%d %b")
        if d.year != prev_y:          # tampilkan tahun hanya saat berganti tahun
            lab += d.strftime(" '%y")
            prev_y = d.year
        tt.append(lab)
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=COL["bg"], plot_bgcolor=COL["panel"],
        font=dict(family=FONT, color=COL["text"], size=12),
        height=620, margin=dict(l=8, r=8, t=44, b=8),
        title=dict(text=title, font=dict(color=title_color, size=15), x=0.01),
        xaxis=dict(rangeslider=dict(visible=False), tickvals=tv, ticktext=tt,
                   gridcolor=COL["grid"], range=[start - 2, x_end]),
        yaxis=dict(gridcolor=COL["grid"], side="right", tickformat=",.0f"),
        showlegend=False, hovermode="x unified", dragmode="pan",
    )


def _candles(fig, df, start):
    d = df.iloc[start:]
    xs = np.arange(start, len(df))
    fig.add_trace(go.Candlestick(
        x=xs, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"],
        increasing=dict(line=dict(color=COL["green"], width=1), fillcolor=COL["green"]),
        decreasing=dict(line=dict(color=COL["red"], width=1), fillcolor=COL["red"]),
        hovertext=list(d.index.strftime("%d %b %Y")), hoverinfo="text+y", name="Harga",
    ))


def _zigzag(fig, pivots, tent, start):
    zz = [q for q in pivots if q[0] >= start]
    if tent and tent[0] >= start:
        zz = zz + [tent]
    if zz:
        fig.add_trace(go.Scatter(x=[q[0] for q in zz], y=[q[1] for q in zz], mode="lines",
                                 line=dict(color=COL["dim"], width=1, dash="dot"),
                                 hoverinfo="skip"))


def _ratio_label(fig, q1, q2, txt, color):
    fig.add_annotation(x=(q1[0] + q2[0]) / 2, y=(q1[1] + q2[1]) / 2, text=txt, showarrow=False,
                       font=dict(color=color, size=11), bgcolor="rgba(6,8,11,0.85)")


def make_chart(code, df, p, scale_txt="", compact=False):
    n = len(df)
    proj = 20 if compact else 30
    start = max(0, (p["B"][0] - 10) if compact else (p["X"][0] - 30))
    x1 = n - 1 + proj
    bull = p["arah"] == "Bullish"
    accent = COL["cyan"] if bull else COL["amber"]
    fill = "rgba(34,211,238,0.13)" if bull else "rgba(255,176,0,0.13)"

    fig = go.Figure()
    _candles(fig, df, start)
    _zigzag(fig, p["pivots"], p["tent"], start)

    X, A, B, C = p["X"], p["A"], p["B"], p["C"]
    if p["D"] is not None:
        D = (p["D"][0], p["D"][1])
        d_dash = "solid"
    elif p.get("touch_idx") is not None:
        D = (p["touch_idx"], p["entry"])      # harga sudah menyentuh level D
        d_dash = "solid"
    else:
        D = (n - 1 + proj // 3, p["entry"])  # proyeksi
        d_dash = "dash"

    # Segitiga XAB & BCD
    for pts in ([X, A, B], [B, C, D]):
        fig.add_trace(go.Scatter(x=[q[0] for q in pts] + [pts[0][0]],
                                 y=[q[1] for q in pts] + [pts[0][1]],
                                 fill="toself", fillcolor=fill, line=dict(width=0),
                                 hoverinfo="skip"))
    # Kaki utama
    fig.add_trace(go.Scatter(x=[X[0], A[0], B[0], C[0]], y=[X[1], A[1], B[1], C[1]],
                             mode="lines+markers", line=dict(color=accent, width=2),
                             marker=dict(size=7, color=accent), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[C[0], D[0]], y=[C[1], D[1]], mode="lines",
                             line=dict(color=accent, width=2, dash=d_dash), hoverinfo="skip"))
    # Garis bantu rasio: XB, AC, BD, XD
    for q1, q2 in ([] if compact else ([X, B], [A, C], [B, D], [X, D])):
        fig.add_trace(go.Scatter(x=[q1[0], q2[0]], y=[q1[1], q2[1]], mode="lines",
                                 line=dict(color=accent, width=1, dash="dot"), hoverinfo="skip"))

    d_price = D[1]
    bd_ext = abs(C[1] - d_price) / abs(C[1] - B[1])
    xd = abs(A[1] - d_price) / abs(A[1] - X[1])
    if not compact:
        _ratio_label(fig, X, B, f"{p['b_ratio']:.3f}", accent)
        _ratio_label(fig, A, C, f"{p['c_ratio']:.3f}", accent)
        _ratio_label(fig, B, D, f"{bd_ext:.3f}", accent)
        _ratio_label(fig, X, D, f"{xd:.3f}", accent)

    # Label titik
    for lab, q in zip("XABCD", [X, A, B, C, D]):
        if q[0] < start:
            continue
        is_low = (lab in "XBD") if bull else (lab in "AC")
        fig.add_annotation(x=q[0], y=q[1], text=f"<b>{lab}</b>", showarrow=False,
                           yshift=-16 if is_low else 16, font=dict(color=COL["text"], size=14))

    # Kotak PRZ + harga batas
    zone_fill = ["rgba(167,139,250,0.30)", "rgba(167,139,250,0.15)"]
    printed = []   # hindari label batas PRZ yang bertumpuk (beda < 0.5%)
    for k, z in enumerate(p["zones"]):
        x0 = C[0] + (D[0] - C[0]) // 2
        # Tebal minimum kotak (hanya visual, ±0.6% harga) agar zona sempit tetap terlihat.
        # Angka batas di kanan tetap harga PRZ sebenarnya.
        mid = (z["lo"] + z["hi"]) / 2
        half = max((z["hi"] - z["lo"]) / 2, abs(mid) * 0.006)
        y0v, y1v = mid - half, mid + half
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0v, y1=y1v,
                      fillcolor=zone_fill[min(k, 1)], line=dict(color=COL["violet"], width=1))
        if compact and k > 0:
            pass
        else:
          fig.add_annotation(x=x0, y=y1v, xanchor="left", yanchor="bottom", showarrow=False,
                           text=(f"PRZ {z['r']}" if compact else
                                 f"PRZ {z['r']} XA · BC {z['bc_e']}"),
                           font=dict(color=COL["violet"], size=11), bgcolor="rgba(6,8,11,0.75)")
        for v, yv, anc in ((z["hi"], y1v, "bottom"), (z["lo"], y0v, "top")):
            if any(abs(v - w) / max(abs(w), 1e-9) < 0.005 for w in printed):
                continue
            printed.append(v)
            fig.add_annotation(x=x1, y=yv, xanchor="right", yanchor=anc, showarrow=False,
                               text=f"({v:,.0f})", font=dict(color=COL["violet"], size=11))

    # SL, TP, Invalid
    lines = [(p["sl"], "STOP POLA", COL["red"]), (p["tp1"], "TP1", COL["green"]),
             (p["tp2"], "TP2", COL["green"])]
    if p.get("buf_atr", 0) > 0:
        lines.append((p["sl_eff"], f"STOP EFEKTIF +{p['buf_atr']:g}ATR", "#ff8fa3"))
    if p["status"] == "Menuju PRZ":
        lines.append((C[1], "INVALID", COL["amber"]))
    for lvl, lab, colr in lines:
        fig.add_shape(type="line", x0=C[0], x1=x1, y0=lvl, y1=lvl,
                      line=dict(color=colr, width=1, dash="dash"))
        fig.add_annotation(x=x1, y=lvl, xanchor="right", yanchor="bottom", showarrow=False,
                           text=f"{lab} ({lvl:,.0f})", font=dict(color=colr, size=11),
                           bgcolor="rgba(6,8,11,0.7)")

    # Harga sekarang
    last_px = float(df["Close"].iloc[-1])
    fig.add_shape(type="line", x0=start, x1=x1, y0=last_px, y1=last_px,
                  line=dict(color="#ffffff", width=1.2, dash="dot"))
    fig.add_trace(go.Scatter(x=[n - 1], y=[last_px], mode="markers",
                             marker=dict(size=10, color="#ffffff", symbol="diamond",
                                         line=dict(color=COL["bg"], width=1)),
                             hoverinfo="skip"))
    fig.add_annotation(x=start, y=last_px, xanchor="left", yanchor="bottom", showarrow=False,
                       text=f"<b>HARGA {last_px:,.0f}</b>", font=dict(color="#000", size=11),
                       bgcolor="#ffffff")

    # Panah proyeksi D -> TP2
    tx = min(x1 - 2, D[0] + proj // 2)
    fig.add_annotation(x=tx, y=p["tp2"], ax=D[0], ay=D[1], xref="x", yref="y",
                       axref="x", ayref="y", showarrow=True, arrowhead=3, arrowsize=1.2,
                       arrowwidth=1.5, arrowcolor=COL["green"], text="")

    title = f"{code} · {p['pattern']} {p['arah']} · {p['status']}"
    if scale_txt:
        title += f" · swing {scale_txt}"
    _base_layout(fig, df, start, x1 + 2, title, accent, nticks=4 if compact else 7)
    if compact:
        fig.update_layout(height=460, title=dict(font=dict(size=12)),
                          margin=dict(l=4, r=4, t=36, b=4))
    return fig


def make_swing_chart(code, df, piv, tent, scale_txt):
    """Grafik saat tidak ada pola valid: ZigZag + 4 swing terakhir."""
    n = len(df)
    last = piv[-4:] if len(piv) >= 4 else piv
    start = max(0, (last[0][0] if last else n - 250) - 30)
    fig = go.Figure()
    _candles(fig, df, start)
    _zigzag(fig, piv, tent, start)
    if len(last) == 4:
        fig.add_trace(go.Scatter(x=[q[0] for q in last], y=[q[1] for q in last],
                                 mode="lines+markers", line=dict(color=COL["dim"], width=2),
                                 marker=dict(size=7, color=COL["text"]), hoverinfo="skip"))
        for lab, q in zip("XABC", last):
            fig.add_annotation(x=q[0], y=q[1], text=f"<b>{lab}?</b>", showarrow=False,
                               yshift=16 if q[2] == "H" else -16,
                               font=dict(color=COL["dim"], size=13))
    _base_layout(fig, df, start, n + 10, f"{code} · tidak ada pola valid · swing {scale_txt}",
                 COL["dim"])
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
.hb-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:12px; }}
.hb-grid.six {{ grid-template-columns:repeat(6,1fr); }}
.hb-grid.eight {{ grid-template-columns:repeat(4,1fr); }}
.hb-grid.five {{ grid-template-columns:repeat(5,1fr); }}
.hb-lad {{ margin:4px 0 8px 0; }}
.hb-mc {{ background:{COL['panel']}; border:1px solid #1a2430; padding:12px 14px 10px 14px;
  margin:10px 0 4px 0; font-size:16px; line-height:1.55; color:{COL['text']}; }}
.hb-mc .t {{ font-size:18px; margin-bottom:4px; }}
.hb-mc .t .k {{ font-weight:800; color:#ffffff; font-size:20px; }}
.hb-mc .t .b {{ float:right; font-size:12px; font-weight:800; border:1px solid; padding:2px 8px;
  letter-spacing:1px; }}
.hb-mc .q {{ color:{COL['cyan']}; font-size:15px; margin-top:4px; border-top:1px dashed #22313d;
  padding-top:4px; }}
.hb-mc .n {{ color:{COL['amber']}; font-size:13px; margin-top:4px; }}
.hb-lad-r {{ display:grid; grid-template-columns:1.6fr 1fr 0.8fr; gap:8px; padding:5px 10px;
  background:{COL['panel']}; margin-bottom:3px; font-size:13px; }}
.hb-lad-r .v {{ text-align:right; color:{COL['text']}; font-weight:700; }}
.hb-lad-r .p {{ text-align:right; color:{COL['dim']}; }}
.hb-lad-r.now {{ background:#1d2630; outline:1px solid #ffffff; }}
.hb-lad-r.now .v {{ color:#ffffff; }}
.hb-card {{ border:1px solid #1a2430; background:{COL['panel']}; padding:10px 14px; }}
.hb-card .k {{ color:{COL['dim']}; font-size:11px; letter-spacing:1px; }}
.hb-card .v {{ font-size:22px; font-weight:800; }}
@media (max-width: 640px) {{
  .hb-grid, .hb-grid.six, .hb-grid.eight, .hb-grid.five {{ grid-template-columns:repeat(2,1fr); }}
  .hb-card .v {{ font-size:18px; }} .hb-title {{ font-size:20px; }} }}
.hb-fn {{ margin:6px 0; }}
.hb-fn-l {{ color:{COL['dim']}; font-size:12px; margin-bottom:2px; }}
.hb-fn-t {{ display:flex; align-items:center; gap:8px; }}
.hb-fn-b {{ height:14px; background:linear-gradient(90deg,{COL['green']},{COL['cyan']}); }}
.hb-fn-t span {{ color:{COL['text']}; font-weight:700; font-size:13px; }}
.hb-why {{ border:1px solid #2a1f10; border-left:3px solid {COL['amber']}; background:#0f0c07;
  padding:10px 14px; color:{COL['text']}; font-size:13px; margin:6px 0 10px 0; }}
div.stButton > button {{ background:#0d1a14; color:{COL['green']}; border:1px solid {COL['green']};
  border-radius:2px; letter-spacing:1px; }}
div.stButton > button:hover {{ background:{COL['green']}; color:#000; }}
.stTabs [data-baseweb="tab"] {{ font-family:'JetBrains Mono', monospace; letter-spacing:1px; }}
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


def cards_html(items, cls=""):
    return f'<div class="hb-grid {cls}">' + "".join(
        f'<div class="hb-card" style="border-left:3px solid {c}">'
        f'<div class="k">{k}</div><div class="v" style="color:{c}">{v}</div></div>'
        for k, v, c in items) + "</div>"


WAKTU_COL = {"seimbang": COL["green"], "CD terlalu cepat": COL["amber"],
             "CD terlalu lambat": COL["amber"]}
STATUS_COL = {"Di PRZ": COL["violet"], "Menuju PRZ": COL["cyan"], "Selesai": COL["amber"],
              "Gagal": COL["red"]}


def ladder_html(p):
    """Tangga level: semua harga penting diurutkan, harga sekarang disorot, % dari harga sekarang."""
    cur = p["price"]
    items = [("TP2", p["tp2"], COL["green"]), ("TP1", p["tp1"], COL["green"]),
             ("ENTRY D", p["entry"], COL["violet"]), ("STOP", p["sl_eff"], COL["red"])]
    for z in p["zones"]:
        items.append((f"PRZ {z['r']} atas", z["hi"], COL["violet"]))
        items.append((f"PRZ {z['r']} bawah", z["lo"], COL["violet"]))
    if p["status"] == "Menuju PRZ":
        items.append(("INVALID (C)", p["C"][1], COL["amber"]))
    # gabungkan level yang praktis sama (beda < 0.1%)
    items.sort(key=lambda t: -t[1])
    rows, seen = [], []
    for lab, v, c in items:
        if any(abs(v - w) / max(abs(w), 1e-9) < 0.003 for w in seen):
            continue
        seen.append(v)
        rows.append((lab, v, c, False))
    rows.append(("HARGA SEKARANG", cur, "#ffffff", True))
    rows.sort(key=lambda t: -t[1])
    html = '<div class="hb-lad">'
    for lab, v, c, is_now in rows:
        pct = (v / cur - 1) * 100
        pct_txt = "" if is_now else f"{pct:+.1f}%"
        cls = "hb-lad-r now" if is_now else "hb-lad-r"
        html += (f'<div class="{cls}" style="border-left:3px solid {c}">'
                 f'<span class="l" style="color:{c}">{lab}</span>'
                 f'<span class="v">{v:,.0f}</span><span class="p">{pct_txt}</span></div>')
    return html + "</div>"


def render_detail(code, df, p, scale_txt="", key=""):
    """Panel angka + tangga level + grafik + tabel swing."""
    def f2(v):
        return f"{v:.2f}" if pd.notna(v) else "-"
    stop_lab = (f"STOP · {('close' if p.get('stop_basis') == 'Close harian' else 'low')}"
                + (f" +{p['buf_atr']:g}ATR" if p.get("buf_atr", 0) > 0 else ""))
    rr_now_col = COL["green"] if pd.notna(p["rr_now2"]) and p["rr_now2"] >= 2 else (
        COL["amber"] if pd.notna(p["rr_now2"]) and p["rr_now2"] >= 1 else COL["red"])
    st.markdown(cards_html([
        ("STATUS", p["status"], STATUS_COL[p["status"]]),
        ("HARGA SEKARANG", f"{p['price']:,.0f}", "#ffffff"),
        ("ENTRY D", f"{p['entry']:,.0f}", COL["violet"]),
        (stop_lab, f"{p['sl_eff']:,.0f}", COL["red"]),
        ("TP1 · 0.382 AD", f"{p['tp1']:,.0f}", COL["green"]),
        ("TP2 · 0.618 AD", f"{p['tp2']:,.0f}", COL["green"]),
        ("R:R DARI ENTRY D · TP2", f2(p["rr"]), COL["text"]),
        ("DARI HARGA SKRG: RISIKO · POTENSI TP1 / TP2",
         f"{p['to_sl']:+.0f}% · {p['to_tp1']:+.0f}% / {p['to_tp2']:+.0f}%", rr_now_col),
    ], "eight"), unsafe_allow_html=True)
    st.caption(f"Waktu: {p['waktu_txt']}")
    st.caption(f"Posisi harga: {p['posisi']} · tembus terdalam melewati PRZ sejak C: "
               f"{p['tembus']:.1f}%.")
    st.caption(f"Masuk di harga sekarang: risiko {p['to_sl']:+.1f}% ke stop, potensi "
               f"{p['to_tp1']:+.1f}% ke TP1 dan {p['to_tp2']:+.1f}% ke TP2.")
    with st.expander("▌TANGGA LEVEL (posisi harga sekarang)", expanded=compact_mode):
        st.markdown(ladder_html(p), unsafe_allow_html=True)
    st.plotly_chart(make_chart(code, df, p, scale_txt, compact=compact_mode), width="stretch",
                    config={"displaylogo": False, "scrollZoom": True}, key=f"ch_{key}")

    def dt(q):
        return df.index[q[0]].strftime("%d %b %Y")
    rows = [["X", dt(p["X"]), p["X"][1], "-"],
            ["A", dt(p["A"]), p["A"][1], "-"],
            ["B", dt(p["B"]), p["B"][1], f"{p['b_ratio']:.3f} XA"],
            ["C", dt(p["C"]), p["C"][1], f"{p['c_ratio']:.3f} AB"]]
    if p["D"] is not None:
        rows.append(["D", dt(p["D"]), p["D"][1], "terkunci"])
    else:
        rows.append(["D", dt((p["touch_idx"],)) if p.get("touch_idx") is not None else "proyeksi",
                     p["entry"], f"{PATTERNS[p['pattern']]['d']} XA"])
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


# ---------------- Pengaturan dari URL (agar tersimpan lewat bookmark) ----------------
QP = st.query_params


def qp_get(key, default, cast=str):
    try:
        return cast(QP[key]) if key in QP else default
    except Exception:
        return default


def qp_list(key, options, default):
    if key not in QP:
        return default
    vals = [v for v in str(QP[key]).split(",") if v in options]
    return vals


SCALE_OPTS = list(SCALES.keys())

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### ▌TAMPILAN")
    compact_mode = st.toggle("Grafik ringkas (HP)", value=qp_get("hp", "0") == "1",
                             help="Grafik di-zoom dari titik B sampai hari ini, label rasio "
                                  "disembunyikan, dan tangga level langsung terbuka.")

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
    atr_len = st.number_input("Periode ATR", 5, 50, qp_get("atr", 14, int), 1)
    sk = qp_get("sk", SCALE_OPTS[0])
    scale_name = st.selectbox("Skala swing (screener)", SCALE_OPTS,
                              index=SCALE_OPTS.index(sk) if sk in SCALE_OPTS else 0)
    mult = SCALES[scale_name]
    age_def = qp_get("age", SCALE_AGE.get(scale_name, 40), int) if sk == scale_name \
        else SCALE_AGE.get(scale_name, 40)
    max_age = st.slider("Umur maks. titik C (hari bursa)", 5, 250, min(max(age_def, 5), 250),
                        key=f"age_{scale_name}")

    st.markdown("### ▌ATURAN STOP")
    STOP_OPTS = ["Low intraday", "Close harian"]
    sb = qp_get("sb", "Close harian")
    stop_basis = st.radio("Basis stop", STOP_OPTS, horizontal=True,
                          index=STOP_OPTS.index(sb) if sb in STOP_OPTS else 1,
                          help="Low intraday: pola Gagal begitu ekor candle menembus SL. "
                               "Close harian: hanya dihitung jebol kalau harga DITUTUP di luar SL.")
    buf_atr = st.number_input("Buffer di luar SL (× ATR)", 0.0, 1.0,
                              min(max(qp_get("buf", 0.0, float), 0.0), 1.0), 0.25,
                              help="Toleransi tambahan di luar SL pola. ATR diambil saat titik C. "
                                   "Contoh 0.5 = pola baru Gagal jika tembus SL lebih dari "
                                   "setengah ATR.")

    if buf_atr > 0.5:
        st.warning("Buffer besar: pola yang sudah rusak bisa tetap tampil hidup. "
                   "Untuk ekor candle sesaat, lebih tepat pakai basis stop Close harian.")

    run = st.button("▶ PINDAI ULANG", width="stretch")
    if run:
        load_data.clear()
        run_scan.clear()
        load_one.clear()

    st.markdown("### ▌FILTER SCREENER")
    PAT_OPTS = list(PATTERNS.keys())
    f_pola = st.multiselect("Pola", PAT_OPTS, default=qp_list("pola", PAT_OPTS, PAT_OPTS))
    f_arah = st.multiselect("Arah", ["Bullish", "Bearish"],
                            default=qp_list("arah", ["Bullish", "Bearish"], ["Bullish", "Bearish"]))
    ST_OPTS = list(STATUS_ORDER.keys())
    f_status = st.multiselect("Status", ST_OPTS,
                              default=qp_list("st", ST_OPTS, ["Di PRZ", "Menuju PRZ", "Selesai"]))
    POS_OPTS = ["Di atas PRZ", "Di dalam PRZ", "Di bawah PRZ"]
    f_pos = st.multiselect("Posisi harga vs PRZ", POS_OPTS,
                           default=qp_list("pos", POS_OPTS, POS_OPTS))
    f_tembus = st.slider("Tembus terdalam maks. (%)", 0.0, 50.0,
                         min(max(qp_get("tmb", 50.0, float), 0.0), 50.0), 0.5,
                         help="Seberapa jauh harga pernah menembus sisi jauh PRZ sejak titik C "
                              "(sisi bawah untuk bullish, sisi atas untuk bearish). "
                              "0 = hanya pola yang belum pernah menembus PRZ.")
    f_rr = st.slider("R:R minimum ke TP2 (×)", 0.0, 6.0,
                     min(max(qp_get("rr", 2.0, float), 0.0), 6.0), 0.25,
                     help="Menuju PRZ dihitung dari entry D (rencana antri beli). Status lain "
                          "dihitung dari harga sekarang. 2× = cukup menang 1 dari 3 transaksi "
                          "untuk impas. Geser ke 0 untuk menampilkan semua.")
    f_dist = st.slider("Jarak maks. ke PRZ (%)", 0.0, 50.0,
                       min(max(qp_get("dist", 15.0, float), 0.0), 50.0), 0.5)
    f_val = st.number_input("Value transaksi minimum harian 20H (miliar)", 0.0, 1000.0,
                            qp_get("val", 1.0, float), 1.0)

    st.caption("Pengaturan ikut tersimpan di alamat (URL) halaman. Bookmark halaman ini supaya "
               "saat dibuka lagi pengaturannya sama.")

# Tulis balik pengaturan ke URL
try:
    st.query_params.update({
        "hp": "1" if compact_mode else "0", "atr": str(int(atr_len)), "sk": scale_name,
        "m": f"{mult:g}", "age": str(int(max_age)), "sb": stop_basis, "buf": f"{buf_atr:g}",
        "pola": ",".join(f_pola), "arah": ",".join(f_arah), "st": ",".join(f_status),
        "dist": f"{f_dist:g}", "val": f"{f_val:g}",
        "pos": ",".join(f_pos), "tmb": f"{f_tembus:g}", "rr": f"{f_rr:g}",
    })
except Exception:
    pass

tab_scr, tab_emt = st.tabs(["▌SCREENER", "▌ANALISA EMITEN"])

# =============================================================================
# TAB 1 — SCREENER
# =============================================================================
with tab_scr:
    with st.spinner(f"Menarik data {len(codes)} emiten & menghitung swing... "
                    "(pindai pertama bisa 1-3 menit)"):
        table, detail, n_loaded, stats = run_scan(tuple(codes), int(atr_len), float(mult),
                                                  int(max_age), stop_basis, float(buf_atr))

    if table.empty:
        table = pd.DataFrame(columns=["_id", "Kode", "Pola", "Arah", "Status", "Harga",
                                      "Jarak PRZ %", "PRZ Bawah", "PRZ Atas", "Entry D", "SL",
                                      "SL Efektif", "Jarak ke SL %", "TP1", "TP2", "R:R TP2", "R:R Rencana", "R:R Skrg TP1",
                                      "R:R Skrg TP2", "Catatan", "Waktu", "Posisi vs PRZ", "Tembus Terdalam %", "Ke SL %", "Ke TP2 %",
                                      "B/XA", "C/AB", "Umur C",
                                      "D Terkunci", "Value Min 20H (M)"])

    # Saring bertahap supaya alasan tiap baris tersembunyi bisa dihitung
    m_status = table["Status"].isin(f_status)
    m_pola = table["Pola"].isin(f_pola) & table["Arah"].isin(f_arah)
    m_val = table["Value Min 20H (M)"] >= f_val
    m_dist = (table["Jarak PRZ %"] <= f_dist) | table["Jarak PRZ %"].isna()
    m_pos = table["Posisi vs PRZ"].isin(f_pos) & (table["Tembus Terdalam %"] <= f_tembus + 1e-9)
    m_rr = (table["R:R Rencana"] >= f_rr - 1e-9) | (
        table["R:R Rencana"].isna() & (table["Status"] == "Gagal")) | (f_rr <= 0)
    keep = m_status & m_pola & m_val & m_dist & m_pos & m_rr

    hid = []
    rest = ~keep
    for lab, m in [("status " + "/".join(sorted(set(table.loc[~m_status, "Status"])) or ["-"]),
                    m_status),
                   ("pola/arah", m_pola),
                   (f"value di bawah {f_val:g} M", m_val),
                   (f"jarak PRZ lebih dari {f_dist:g}%", m_dist),
                   ("posisi/tembus PRZ", m_pos),
                   (f"R:R di bawah {f_rr:g}×", m_rr)]:
        cnt = int((rest & ~m).sum())
        if cnt:
            hid.append(f"{cnt} {lab}")
        rest = rest & m

    view = table[keep].copy()
    view["_s"] = view["Status"].map(STATUS_ORDER)
    view = view.sort_values(["_s", "Jarak PRZ %"], na_position="last").drop(columns="_s")
    view = view.reset_index(drop=True)

    st.markdown(cards_html([
        ("SAHAM TERMUAT", n_loaded, COL["text"]),
        ("DI PRZ", int((view["Status"] == "Di PRZ").sum()), COL["violet"]),
        ("MENUJU PRZ", int((view["Status"] == "Menuju PRZ").sum()), COL["cyan"]),
        ("SELESAI", int((view["Status"] == "Selesai").sum()), COL["amber"]),
        ("GAGAL", int((view["Status"] == "Gagal").sum()), COL["red"]),
    ], "five"), unsafe_allow_html=True)
    skala_txt = f"skala {scale_name.split(' ')[0]} {mult:g}×ATR"
    stop_txt = f"stop {stop_basis.lower()}" + (f" +{buf_atr:g}ATR" if buf_atr > 0 else "")
    rincian = (f"{len(table)} pola terdeteksi · {len(view)} tampil · {skala_txt} · {stop_txt}")
    if hid:
        rincian += " · tersembunyi oleh filter: " + ", ".join(hid)
    st.markdown(f'<div class="hb-sub" style="margin:-4px 0 10px 0">{rincian}</div>',
                unsafe_allow_html=True)

    if not compact_mode:
      with st.expander("▌CORONG SARINGAN: kenapa polanya sedikit?"):
            steps = [
                ("Jendela 4 swing terakhir yang dicek", stats.get("jendela", 0)),
                ("Lolos C = 0.382–0.886 AB", stats.get("lolos_c", 0)),
                ("Lolos B sesuai salah satu pola", stats.get("lolos_b", 0)),
                (f"Titik C belum lewat {int(max_age)} hari", stats.get("lolos_umur", 0)),
                ("Pola aktif (D belum batal)", stats.get("aktif", 0)),
            ]
            top = max(1, steps[0][1])
            bars = ""
            for lab, v in steps:
                w = max(1.5, v / top * 100)
                bars += (f'<div class="hb-fn"><div class="hb-fn-l">{lab}</div>'
                         f'<div class="hb-fn-t"><div class="hb-fn-b" style="width:{w:.1f}%"></div>'
                         f'<span>{v}</span></div></div>')
            st.markdown(bars, unsafe_allow_html=True)
            st.caption("Tiap saham dicek di 2 posisi: titik C = swing terkunci terakhir (D sedang "
                       "berjalan) atau sebelum terakhir (D sudah terkunci). Penyaring terberat "
                       "biasanya rasio B: saat pasar tren kuat, B sering menembus X sehingga bukan "
                       "pola harmonic. Coba skala swing Menengah/Besar untuk pola yang lebih lebar.")

    ids = view["_id"].tolist()
    show = view.drop(columns="_id")

    def color_status(v):
        c = STATUS_COL.get(v)
        return f"color:{c};font-weight:700" if c else ""

    def color_arah(v):
        return f"color:{COL['green']}" if v == "Bullish" else f"color:{COL['amber']}"

    num0 = st.column_config.NumberColumn(format="%.0f")
    num2 = st.column_config.NumberColumn(format="%.2f")
    num3 = st.column_config.NumberColumn(format="%.3f")
    fsig = hash((tuple(f_pola), tuple(f_arah), tuple(f_status), f_dist, f_val, atr_len,
                 mult, max_age, len(codes), stop_basis, buf_atr))
    fkey = f"tbl2_{fsig}"

    event = None
    if view.empty:
        if table.empty:
            st.info(f"Dari {n_loaded} saham, belum ada pola harmonic yang terbentuk dengan "
                    "skala swing ini. Coba skala lain di sidebar.")
        else:
            hidden = table["Status"].value_counts().to_dict()
            rinci = ", ".join(f"{v} {k}" for k, v in hidden.items())
            st.info(f"Ada {len(table)} pola terdeteksi ({rinci}), tapi semuanya tersembunyi oleh "
                    "filter. Buka sidebar (tombol » di kiri atas) lalu longgarkan filter Status, "
                    "Pola, jarak PRZ, atau value transaksi.")
    elif compact_mode:
        # ---- Mode HP: daftar kartu, satu saham satu kartu ----
        def pct(v):
            return "-" if pd.isna(v) else f"{v:+.0f}%"
        for i, row in view.iterrows():
            p = detail[row["_id"]]
            colr = STATUS_COL.get(p["status"], COL["text"])
            jarak = "" if pd.isna(p["dist"]) or p["dist"] == 0 else f" {p['dist']:.0f}%"
            pos = p["posisi"].replace("Di ", "di ") + jarak
            risk_ok = pd.notna(p["to_sl"]) and p["to_sl"] < 0
            pot1 = pct(p["to_tp1"]) if p["to_tp1"] > 0 else "-"
            pot2 = pct(p["to_tp2"]) if p["to_tp2"] > 0 else "-"
            st.markdown(f"""
<div class="hb-mc" style="border-left:4px solid {colr}">
  <div class="t"><span class="k">{row['Kode']}</span> · {p['pattern']}
    <span class="b" style="color:{colr};border-color:{colr}">{p['status'].upper()}</span></div>
  <div class="r">Harga <b>{p['price']:,.0f}</b> · {pos}</div>
  <div class="r">SL <b style="color:{COL['red']}">{p['sl_eff']:,.0f}</b> · TP
    <b style="color:{COL['green']}">{p['tp1']:,.0f}</b> /
    <b style="color:{COL['green']}">{p['tp2']:,.0f}</b></div>
  <div class="r">Risiko <b style="color:{COL['red']}">{pct(p['to_sl']) if risk_ok else '-'}</b>
    · Potensi <b style="color:{COL['green']}">{pot1}</b> / <b style="color:{COL['green']}">{pot2}</b></div>
  <div class="r" style="font-size:14px;color:{COL['dim']}">Waktu: {p['waktu_txt'].replace(p['waktu_lbl'], f"<b style='color:{WAKTU_COL.get(p['waktu_lbl'], COL['dim'])}'>{p['waktu_lbl']}</b>") if p['waktu_lbl'] != 'berjalan' else p['waktu_txt']}</div>
  {f'<div class="q">Antri beli di <b>{p["entry"]:,.0f}</b> · R:R ke TP2 <b>{p["rr"]:.1f}×</b></div>' if p["status"] == "Menuju PRZ" and pd.notna(p["rr"]) else ''}
  {f'<div class="n">{p["catatan"]}</div>' if p["catatan"] else ''}
</div>""", unsafe_allow_html=True)
            if st.button(f"Buka grafik {row['Kode']} ›", key=f"open_{row['_id']}",
                         width="stretch"):
                st.session_state["_open_card"] = row["_id"]
    else:
        styled = show.style.map(color_status, subset=["Status"]).map(color_arah, subset=["Arah"])
        st.caption("Klik baris untuk membuka grafik pola.")
        event = st.dataframe(
            styled, hide_index=True, width="stretch", height=min(520, 38 + 35 * len(show)),
            on_select="rerun", selection_mode="single-row", key=fkey,
            column_order=["Kode", "Pola", "Arah", "Status", "Posisi vs PRZ", "Tembus Terdalam %",
                          "R:R Rencana", "Catatan", "Waktu", "Harga", "Jarak PRZ %",
                          "PRZ Bawah", "PRZ Atas", "Entry D", "SL", "SL Efektif", "Jarak ke SL %",
                          "TP1", "TP2", "R:R TP2", "R:R Skrg TP1", "R:R Skrg TP2",
                          "Ke SL %", "Ke TP2 %", "B/XA", "C/AB", "Umur C", "D Terkunci", "Value Min 20H (M)"],
            column_config={
                "Harga": num0, "PRZ Bawah": num0, "PRZ Atas": num0, "Entry D": num0,
                "SL": num0, "SL Efektif": num0, "Jarak ke SL %": num2,
                "TP1": num0, "TP2": num0, "Jarak PRZ %": num2, "R:R TP2": num2,
                "R:R Skrg TP1": num2, "R:R Skrg TP2": num2, "R:R Rencana": num2, "Ke SL %": num2, "Ke TP2 %": num2,
                "Tembus Terdalam %": st.column_config.NumberColumn(format="%.1f"),
                "B/XA": num3, "C/AB": num3,
                "Value Min 20H (M)": st.column_config.NumberColumn(format="%.1f"),
            },
        )

    @st.dialog("DETAIL POLA", width="large")
    def show_detail(rid):
        p = detail[rid]
        code = rid.split("|")[0]
        df = load_data(tuple(codes))[code]
        render_detail(code, df, p, f"{mult:g}×ATR", key=rid)

    rows_sel = event.selection.rows if event is not None and hasattr(event, "selection") else []
    card_rid = st.session_state.pop("_open_card", None)
    if card_rid and card_rid in detail:
        show_detail(card_rid)
    elif rows_sel:
        rid = ids[rows_sel[0]]
        if st.session_state.get("_open") != rid:
            st.session_state["_open"] = rid
            show_detail(rid)
    else:
        st.session_state["_open"] = None

    if not compact_mode:
      st.caption(f"Aturan stop: basis {stop_basis.lower()}, buffer {buf_atr:g}×ATR. "
               "Kolom 'Jarak ke SL %' = posisi terendah harga (low/close sesuai basis) sejak C "
               "terhadap SL pola; negatif berarti sudah pernah tembus.")
      st.caption("Data: Yahoo Finance (harian, 2 tahun). Swing terakhir ZigZag selalu sementara "
               "sampai harga berbalik ≥ k×ATR; status dihitung ulang tiap pindai.")

# =============================================================================
# TAB 2 — ANALISA EMITEN
# =============================================================================
with tab_emt:
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    code_in = c1.text_input("Kode emiten", placeholder="contoh: PANI", max_chars=6)
    c2.button("▶ ANALISA", width="stretch", key="btn_emt")
    code = code_in.strip().upper().replace(".JK", "")

    if not code:
        st.caption("Ketik kode saham lalu tekan Enter. Ketiga skala swing (Kecil 1.5×, "
                   "Menengah 3×, Besar 5× ATR) diperiksa sekaligus.")
    else:
        with st.spinner(f"Menarik data {code} 3 tahun..."):
            df1 = load_one(code)
        if df1 is None:
            st.error(f"Data {code} tidak ditemukan di Yahoo Finance. Cek lagi kodenya.")
        else:
            res = {}
            for nm, m in SCALES.items():
                pats = detect_patterns(df1, int(atr_len), m, max_age=10_000,
                                       stop_basis=stop_basis, buf_atr=float(buf_atr))
                res[nm] = (m, pats)
            last = df1["Close"].iloc[-1]
            chg = (last / df1["Close"].iloc[-2] - 1) * 100
            n_found = sum(len(v[1]) for v in res.values())
            st.markdown(cards_html([
                (code, f"{last:,.0f}", COL["text"]),
                ("PERUBAHAN 1H", f"{chg:+.2f}%", COL["green"] if chg >= 0 else COL["red"]),
                ("DATA TERAKHIR", df1.index[-1].strftime("%d %b %Y"), COL["dim"]),
                ("POLA DITEMUKAN", n_found, COL["violet"] if n_found else COL["dim"]),
            ]), unsafe_allow_html=True)

            labels = [f"{nm.split(' ')[0]} · {len(v[1])} pola" for nm, v in res.items()]
            for tab, (nm, (m, pats)) in zip(st.tabs(labels), res.items()):
                with tab:
                    scale_txt = f"{m:g}×ATR"
                    if pats:
                        for j, p in enumerate(pats):
                            if j:
                                st.divider()
                            render_detail(code, df1, p, scale_txt, key=f"{code}_{m}_{j}")
                    else:
                        h = df1["High"].values.astype(float)
                        l = df1["Low"].values.astype(float)
                        c = df1["Close"].values.astype(float)
                        piv, tent = zigzag_atr(h, l, atr_wilder(h, l, c, int(atr_len)), m)
                        st.markdown('<div class="hb-why"><b>Kenapa tidak ada pola?</b><br>'
                                    + "<br>".join(diagnose(piv)) + "</div>",
                                    unsafe_allow_html=True)
                        st.plotly_chart(make_swing_chart(code, df1, piv, tent, scale_txt),
                                        width="stretch", key=f"sw_{code}_{m}",
                                        config={"displaylogo": False, "scrollZoom": True})
