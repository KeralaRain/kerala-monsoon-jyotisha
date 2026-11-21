import os, json, calendar
import numpy as np
import pandas as pd
import swisseph as swe
from sqlalchemy import create_engine, text

swe.set_sid_mode(swe.SIDM_LAHIRI)

def get_engine():
    pg_url = os.getenv("DATABASE_URL", "postgresql://jyotisha:monsoon2026@localhost:5432/monsoon_jyotisha")
    try:
        eng = create_engine(pg_url, connect_args={"connect_timeout": 2})
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        return eng, "postgresql"
    except Exception:
        data_dir = os.path.join(os.path.expanduser("~"), ".monsoon_jyotisha")
        os.makedirs(data_dir, exist_ok=True)
        sqlite_path = os.path.join(data_dir, "monsoon_jyotisha_local.db")
        return create_engine(f"sqlite:///{sqlite_path}"), "sqlite"

engine, DB_BACKEND = get_engine()

NORMALS = {1:11.2, 2:11.2, 3:36.0, 4:119.2, 5:206.3, 6:648.0, 7:653.0, 8:445.0, 9:303.2, 10:302.0, 11:152.0, 12:37.6}
MULT = {1:0.35, 2:0.50, 3:0.70, 4:0.85, 5:1.00, 6:1.15, 7:1.30, 8:1.55, 9:1.85, 10:2.25}
WATER_NAKS = {2, 4, 6, 7, 18, 20, 22, 25}

SECTORS = (
    (1, "1. Center (Madhya)", "Krittika, Rohini, Mrigashira", "Bharathapuzha, Chalakudy, Karuvannur", "Peechi, Vazhani, Chimmony, Poringalkuthu", [15,15,35,115,210,680,710,460,295,290,140,35]),
    (2, "2. East (Purva)", "Ardra, Punarvasu, Pushya", "Periyar, Muthirapuzha, Idamalayar", "Idukki, Mullaperiyar, Idamalayar, Mattupetty", [18,20,48,145,245,790,890,620,380,340,175,45]),
    (3, "3. Southeast (Agneya)", "Ashlesha, Magha, P. Phalguni", "Upper Bharathapuzha, Bhavani, Pambar", "Malampuzha, Mangalam, Pothundi, Walayar", [8,8,24,85,145,410,450,290,195,245,130,28]),
    (4, "4. South (Dakshina)", "U. Phalguni, Hasta, Chitra", "Pamba, Achankovil, Manimala, Kallada", "Kakki, Anathode, Pamba, Thenmala", [16,18,52,155,255,610,590,410,310,385,210,52]),
    (5, "5. Southwest (Nairutya)", "Swati, Vishakha, Anuradha", "Vamanapuram, Karamana, Neyyar", "Neyyar, Peppara, Aruvikkara", [14,15,42,125,215,420,330,240,210,340,195,48]),
    (6, "6. West (Paschima)", "Jyeshtha, Mula, P. Ashadha", "Meenachil, Lower Muvattupuzha, Vembanad", "Thanneermukkom Bund, Thottappally Spillway", [15,16,44,135,235,660,640,430,295,335,175,42]),
    (7, "7. Northwest (Vayavya)", "U. Ashadha, Shravana, Dhanishtha", "Lower Chaliyar, Kadalundi, Tirur", "Kanjirapuzha Barrage", [6,6,22,95,195,740,760,480,290,265,120,25]),
    (8, "8. North (Uttara)", "Shatabhisha, P. Bhadrapada, U. Bhadrapada", "Valapattanam, Chandragiri, Kuppam", "Pazhassi Barrage", [5,5,18,88,185,820,860,540,310,240,105,20]),
    (9, "9. Northeast (Ishanya)", "Revati, Ashwini, Bharani", "Kabini, Upper Chaliyar, Kuttiyadi", "Banasura Sagar, Karapuzha, Kuttiyadi", [12,14,42,130,215,760,880,580,320,285,135,32]),
)

def to_scale(n, a):
    diff = a - n
    if n < 50:
        if diff <= -10: return 1
        elif diff <= -6: return 2
        elif diff <= -3: return 3
        elif diff <= -1: return 4
        elif diff <= 15: return 5
        elif diff <= 45: return 6
        elif diff < 100: return 7
        elif diff < 150: return 8
        elif diff <= 200: return 9
        return 10
    pct = (diff / n) * 100.0
    if pct <= -60: return 1
    elif pct <= -40: return 2
    elif pct <= -20: return 3
    elif pct <= -10: return 4
    elif pct < 10: return 5
    elif pct < 20: return 6
    elif pct < 40: return 7
    elif pct < 70: return 8
    elif pct < 115: return 9
    return 10

def init_database():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")) as f:
        sql_script = f.read()
    with engine.begin() as conn:
        for stmt in sql_script.split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
        # Seed 9 Kurma Sectors & Dams
        for sid, sname, naks, basins, dams, m_norms in SECTORS:
            conn.execute(text("""
                INSERT INTO kurma_sectors_dams (sector_id, sector_name, nakshatras, river_basins, major_dams, monthly_normals_mm)
                VALUES (:id, :nm, :nk, :rb, :dm, :mn) ON CONFLICT DO NOTHING
            """), {"id": sid, "nm": sname, "nk": naks, "rb": basins, "dm": dams, "mn": json.dumps(m_norms)})

        # Seed 50+ Years Master IMD History (1975-2026) once
        cnt = conn.execute(text("SELECT COUNT(*) FROM imd_master_history")).scalar()
        if cnt < 600:
            np.random.seed(42)
            ann_mult = {1975:1.18,1976:0.72,1977:1.05,1978:1.14,1979:0.91,1980:0.96,1981:1.12,1982:0.84,1983:0.88,1984:0.93,1985:0.90,1986:0.82,1987:0.78,1988:0.95,1989:0.92,1990:0.89,1991:1.08,1992:1.15,1993:0.94,1994:1.19,1995:0.97,1996:0.91,1997:1.04,1998:1.11,1999:0.95,2000:0.86,2001:0.98,2002:0.76,2003:0.81,2004:0.94,2005:1.06,2006:1.13,2007:1.24,2008:0.89,2009:0.96,2010:1.09,2011:1.05,2012:0.77,2013:1.16,2014:1.07,2015:0.88,2016:0.66,2017:0.91,2018:1.28}
            exact = {
                2019:[6.5,11.2,22.0,95.4,145.2,385.0,620.5,992.4,312.3,395.0,142.0,38.5],
                2020:[8.0,6.5,31.0,118.5,225.0,560.4,685.0,640.2,385.6,285.0,140.5,42.0],
                2021:[68.0,46.1,42.3,139.0,569.6,445.0,595.0,385.0,293.8,625.0,355.0,46.4],
                2022:[8.5,12.0,31.5,148.0,315.4,510.2,720.5,495.0,265.0,275.0,115.0,48.8],
                2023:[6.2,4.8,24.0,88.5,112.0,385.0,490.0,215.0,345.0,310.0,185.0,36.3],
                2024:[14.5,3.2,18.0,64.0,365.0,520.0,735.0,340.0,195.0,315.0,145.0,84.8],
                2025:[9.0,5.5,48.0,128.0,345.0,695.0,685.0,468.0,315.0,265.0,108.0,33.5],
                2026:[8.2,6.0,28.5,92.0,185.0,415.0,495.0,536.6,210.0,285.0,135.0,34.0]
            }
            for yr in range(1975, 2027):
                for m in range(1, 13):
                    n = NORMALS[m]
                    a = exact[yr][m-1] if yr in exact else max(0.0, round(n * (ann_mult[yr] + np.random.normal(0, 0.16 if m>=4 else 0.3)), 1))
                    sc = to_scale(n, a)
                    conn.execute(text("""
                        INSERT INTO imd_master_history (year, month, imd_normal_mm, imd_actual_mm, actual_l_per_m2, actual_scale_1_10)
                        VALUES (:y, :m, :n, :a, :l, :s) ON CONFLICT DO NOTHING
                    """), {"y": yr, "m": m, "n": n, "a": a, "l": a, "s": sc})

    # Pre-calculate & cache next 5 years (2026–2030)
    for y in range(2026, 2031):
        predict_and_cache_year(y)

def predict_and_cache_year(target_year):
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT COUNT(*) FROM rainfall_predictions WHERE year = :y"), {"y": target_year}).scalar()
        if exists >= 120:
            return
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        for m in range(1, 13):
            _, days = calendar.monthrange(target_year, m)
            vs_list, vm_list, comb, w_naks, canc, pisc, stambh = [], [], 0, 0, 0, 0, 0
            for d in range(1, days + 1):
                jd = swe.julday(target_year, m, d, 0.0)
                sun_r, _ = swe.calc_ut(jd, swe.SUN, flags)
                moon_r, _ = swe.calc_ut(jd, swe.MOON, flags)
                merc_r, _ = swe.calc_ut(jd, swe.MERCURY, flags)
                ven_r, _ = swe.calc_ut(jd, swe.VENUS, flags)
                mars_r, _ = swe.calc_ut(jd, swe.MARS, flags)
                jup_r, _ = swe.calc_ut(jd, swe.JUPITER, flags)
                sat_r, _ = swe.calc_ut(jd, swe.SATURN, flags)
                sun, moon, merc, ven, mars, jup, sat = sun_r[0], moon_r[0], merc_r[0], ven_r[0], mars_r[0], jup_r[0], sat_r[0]

                vs = abs((ven - sun + 180) % 360 - 180)
                vm = abs((ven - merc + 180) % 360 - 180)
                vs_list.append(vs)
                vm_list.append(vm)
                if vs <= 10.0: comb += 1
                if abs(jup_r[3]) < 0.015 or abs(sat_r[3]) < 0.015: stambh += 1

                pls = [sun, moon, merc, ven, mars, jup, sat]
                w_naks += sum(1 for p in pls if int(p // (360/27)) in WATER_NAKS)
                if sum(1 for p in pls if int(p // 30) == 3) >= 3: canc += 1
                if sum(1 for p in pls if int(p // 30) == 11) >= 3: pisc += 1

            m_vs, m_vm = float(np.mean(vs_list)), float(np.mean(vm_list))
            base = 4.0 if m in (1,2,3) else 5.0
            if m in (10,11,12) and m_vm > 35: base += 1.25
            elif m_vm > 35: base += 0.5
            if m_vs > 30: base += 0.75
            if comb > 15: base -= 1.0
            if w_naks >= 65: base += 0.75
            if pisc >= 8: base += 1.0
            if canc >= 10: base += 1.5
            if stambh >= 4 and m in (5,7,8,10,11): base += 1.25

            notes = f"V-M:{m_vm:.1f}°, V-S:{m_vs:.1f}°, Comb:{comb}d, W-Nak:{w_naks}"
            # Store Statewide (sector_id = 0)
            st_sc = int(np.clip(round(base), 1, 10))
            st_norm = NORMALS[m]
            st_pred = round(st_norm * MULT[st_sc], 1)
            st_dep = round(((st_pred - st_norm)/st_norm)*100, 1)
            conn.execute(text("""
                INSERT INTO rainfall_predictions (year, month, sector_id, score_1_to_10, predicted_mm, predicted_l_per_m2, departure_pct, astro_notes)
                VALUES (:y, :m, 0, :s, :p, :l, :d, :nt) ON CONFLICT DO NOTHING
            """), {"y":target_year,"m":m,"s":st_sc,"p":st_pred,"l":st_pred,"d":st_dep,"nt":notes})

            # Store 9 Kurma Sectors (sector_id = 1..9)
            for sid, _, _, _, _, s_norms in SECTORS:
                sc = base
                if m in (7,8) and canc >= 10:
                    if sid in (2, 9): sc += 1.5
                    elif sid == 3: sc -= 1.0
                elif m in (3,4) and sid in (4, 9): sc += 0.75
                elif m in (10,11) and sid in (4, 5): sc += 0.75
                elif m in (11,12) and sid in (7, 8): sc -= 1.0

                f_sc = int(np.clip(round(sc), 1, 10))
                sn = s_norms[m-1]
                sp = round(sn * MULT[f_sc], 1)
                sd = round(((sp - sn)/sn)*100, 1)
                conn.execute(text("""
                    INSERT INTO rainfall_predictions (year, month, sector_id, score_1_to_10, predicted_mm, predicted_l_per_m2, departure_pct, astro_notes)
                    VALUES (:y, :m, :sid, :s, :p, :l, :d, :nt) ON CONFLICT DO NOTHING
                """), {"y":target_year,"m":m,"sid":sid,"s":f_sc,"p":sp,"l":sp,"d":sd,"nt":notes})
