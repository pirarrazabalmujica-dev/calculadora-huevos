"""
Monitor de Huevos — Menú principal
===================================
Sección 1: Precios internacionales (Brasil, Argentina, Chile, USA)
Sección 2: Importaciones de huevos a Chile (herramienta HTML)
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from io import StringIO, BytesIO
import streamlit.components.v1 as components
import re, os
import pdfplumber
import xlrd

FRED_API_KEY = "a80093ab267bd7a703209192064050b5"
APP_VERSION = "2.0.0"

st.set_page_config(
    page_title="Monitor de Huevos",
    page_icon="🥚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Estilos globales ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
html,body,[class*="css"]{font-family:'Syne',sans-serif;}
[data-testid="stAppViewContainer"]{background:#0b0f1a;color:#e8e6e1;}
[data-testid="stSidebar"]{background:#0f1420;border-right:1px solid #1e2535;}
.block-container{padding-top:2rem;max-width:1200px;}
.kpi-card{background:#131929;border:1px solid #1e2a3a;border-radius:12px;padding:16px 20px;margin-bottom:10px;}
.kpi-label{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#4a5568;margin-bottom:5px;font-family:'JetBrains Mono',monospace;}
.kpi-value{font-size:1.7rem;font-weight:800;font-family:'JetBrains Mono',monospace;line-height:1;}
.kpi-sub{font-size:10px;color:#4a5568;margin-top:4px;font-family:'JetBrains Mono',monospace;}
.fuente-badge{display:inline-block;background:#1e2535;border:1px solid #2a3550;border-radius:6px;padding:2px 8px;font-size:10px;font-family:'JetBrains Mono',monospace;color:#64748b;margin-right:4px;}
.nota{font-size:11px;color:#374151;font-family:'JetBrains Mono',monospace;margin-top:6px;}
.menu-card{
    background:#0f1829;border:1px solid #1e2a3a;border-radius:16px;
    padding:40px 36px;cursor:pointer;transition:all .2s;text-align:center;
    display:block;text-decoration:none;
}
.menu-card:hover{border-color:#f97316;background:#141f35;transform:translateY(-2px);}
.menu-card-icon{font-size:52px;margin-bottom:16px;}
.menu-card-title{font-size:1.4rem;font-weight:800;color:#e8e6e1;margin-bottom:8px;}
.menu-card-desc{font-size:12px;color:#4a5568;line-height:1.6;font-family:'JetBrains Mono',monospace;}
.back-btn{background:transparent;border:1px solid #1e2535;border-radius:8px;
    padding:6px 14px;color:#4a5568;cursor:pointer;font-family:'Syne',sans-serif;
    font-size:12px;transition:all .15s;margin-bottom:20px;}
.back-btn:hover{border-color:#e8e6e1;color:#e8e6e1;}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "seccion" not in st.session_state:
    st.session_state.seccion = "menu"

# ── Version check ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def check_latest_version():
    try:
        r = requests.get(
            "https://raw.githubusercontent.com/pirarrazabalmujica-dev/calculadora-huevos/main/version.txt",
            timeout=5
        )
        if r.status_code == 200:
            return r.text.strip()
    except Exception:
        pass
    return None

# ── Helpers ───────────────────────────────────────────────────────────────────
def last_val(df, col):
    if df is None or col not in df.columns: return None, None
    s = df[col].dropna()
    if s.empty: return None, None
    return s.iloc[-1], df["mes"].iloc[s.index[-1]]

# ── Tipo de cambio ────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600,show_spinner="💱 Actualizando tipo de cambio...")
def get_fx():
    fx = {"USD_CLP":950.0,"BRL_CLP":170.0,"ARS_CLP":0.86,
          "BRL_USD":0.18,"ARS_USD":1/1100,"CLP_USD":1/950}
    try:
        r=requests.get("https://mindicador.cl/api/dolar",timeout=8)
        u=float(r.json()["serie"][0]["valor"]); fx["USD_CLP"]=u; fx["CLP_USD"]=1/u
    except: u=fx["USD_CLP"]
    try:
        r=requests.get("https://economia.awesomeapi.com.br/json/last/USD-BRL",timeout=8)
        b=float(r.json()["USDBRL"]["bid"]); fx["BRL_USD"]=1/b; fx["BRL_CLP"]=u/b
    except: pass
    # MEP (dólar bolsa) — tipo de cambio de mercado, evita la brecha oficial
    try:
        r=requests.get("https://dolarapi.com/v1/dolares/bolsa",timeout=8)
        a_mep=float(r.json()["venta"]); fx["ARS_USD"]=1/a_mep; fx["ARS_CLP"]=u/a_mep
    except:
        # fallback: BCRA oficial
        try:
            today=datetime.now().strftime("%Y-%m-%d"); first=datetime.now().strftime("%Y-%m-01")
            r=requests.get(f"https://api.bcra.gob.ar/estadisticas/v2.0/datosVariable/4/{first}/{today}",timeout=8,verify=False)
            a=float(r.json()["results"][-1]["valor"]); fx["ARS_USD"]=1/a; fx["ARS_CLP"]=u/a
        except: pass
    return fx

# ── Scrapers ──────────────────────────────────────────────────────────────────
HEADERS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Accept-Language":"es,pt;q=0.9"}

def _parse_anual_pdf(pdf_bytes, year):
    """Parsea PDF anual de Procon-SP: extrae los 12 valores mensuales de Ovos Brancos."""
    records=[]
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text=page.extract_text() or ""
                text=re.sub(r'(\d)\s+([,\.])',r'\1\2',text)
                for line in text.split("\n"):
                    if re.search(r'Ovos\s+Brancos',line,re.IGNORECASE):
                        vals=re.findall(r'\d{1,3},\d{2}',line)
                        if len(vals)>=12:
                            for month_idx, val in enumerate(vals[:12],start=1):
                                price=float(val.replace(',','.'))
                                if 3.0<price<100.0:
                                    records.append({
                                        "mes":f"{year}-{month_idx:02d}",
                                        "fecha":pd.Timestamp(f"{year}-{month_idx:02d}-01"),
                                        "precio_brl":round(price/12,4)})
                            return records
    except: pass
    return records

def _brasil_proconsp(on_status=None):
    """Procon-SP — descubre PDFs via WP API, parsea Ovos Brancos dúzia — varejo SP.
    on_status(msg): callback opcional para reportar progreso a la UI.
    """
    def _log(msg):
        if on_status: on_status(msg)

    _log("🔍 Consultando API Procon-SP...")
    try:
        r=requests.get(
            "https://www.procon.sp.gov.br/wp-json/wp/v2/posts?search=cesta+basica&per_page=8&orderby=date&order=desc",
            headers=HEADERS, timeout=12)
        posts=r.json()
        if not isinstance(posts,list): posts=[]
    except: posts=[]; _log("⚠️ No se pudo conectar con Procon-SP")

    records=[]; seen_pdfs=set(); monthly_found=0; pdf_n=0
    MAX_MONTHLY=6
    total=len(posts)

    for i, post in enumerate(posts):
        if monthly_found >= MAX_MONTHLY:
            break
        try:
            pub_date=pd.Timestamp(post["date"][:10])
            data_date=pub_date-pd.DateOffset(months=1)
            data_year=int(data_date.year); data_month=int(data_date.month)
            content=post.get("content",{}).get("rendered","")
            pdf_urls=re.findall(r'https://[^"<>\s]+\.pdf',content)
            cb_pdfs=[u for u in pdf_urls if re.search(r'/CB[-_]|/CB[a-zA-Z]',u)
                     and not any(x in u.lower() for x in ['arroz','planilha','pesquisa','coleta'])
                     and u not in seen_pdfs]
            if not cb_pdfs: continue
            pdf_url=cb_pdfs[0]; seen_pdfs.add(pdf_url); pdf_n+=1
            filename=pdf_url.split("/")[-1]
            is_anual=bool(re.search(r'/CB[-_]?Anual[-_]?\d{2}\.pdf', pdf_url, re.IGNORECASE))
            tipo="anual" if is_anual else f"{data_year}-{data_month:02d}"
            _log(f"📄 PDF {pdf_n} de ~{total}: `{filename}` ({tipo}) — descargando…")
            r2=requests.get(pdf_url, headers=HEADERS, timeout=12)
            if r2.status_code!=200 or len(r2.content)<5000:
                _log(f"⚠️ `{filename}` no disponible (HTTP {r2.status_code})")
                continue
            kb=len(r2.content)//1024
            _log(f"🔎 `{filename}` ({kb} KB) — parseando…")
            if is_anual:
                anual_year=pub_date.year-1
                annual_records=_parse_anual_pdf(r2.content, anual_year)
                records.extend(annual_records)
                _log(f"✅ `{filename}` — {len(annual_records)} meses extraídos")
                continue
            with pdfplumber.open(BytesIO(r2.content)) as pdf:
                for page in pdf.pages:
                    text=page.extract_text() or ""
                    text=re.sub(r'(\d)\s+([,\.])',r'\1\2',text)
                    m=re.search(r'Ovos\s+Brancos[^\n]*?(\d{1,3}[,\.]\d{2})\s+(\d{1,3}[,\.]\d{2})',text)
                    if m:
                        curr=float(m.group(2).replace(',','.'))
                        if 3.0<curr<100.0:
                            records.append({"mes":f"{data_year}-{data_month:02d}",
                                "fecha":pd.Timestamp(f"{data_year}-{data_month:02d}-01"),
                                "precio_brl":round(curr/12,4)})
                            monthly_found+=1
                            _log(f"✅ `{filename}` — R$ {curr:.2f}/docena ({data_year}-{data_month:02d})")
                            break
        except Exception as exc:
            _log(f"⚠️ Error en post {i+1}: {exc}")
            continue
    _log(f"🏁 Brasil listo — {len(records)} registros")
    return records

# Caché manual en session_state para poder mostrar progreso en la primera carga
_BRASIL_TTL = 43200  # 12 h en segundos

def scrape_brasil(on_status=None):
    """Procon-SP con caché en session_state (12 h) y progreso opcional."""
    key_data="brasil_data"; key_ts="brasil_ts"
    now=datetime.now().timestamp()
    cached_ts=st.session_state.get(key_ts,0)
    if now-cached_ts < _BRASIL_TTL and key_data in st.session_state:
        return st.session_state[key_data]
    records=_brasil_proconsp(on_status=on_status)
    if not records:
        result=(None,"Sin datos Brasil")
    else:
        df=pd.DataFrame(records).drop_duplicates("mes").sort_values("mes").reset_index(drop=True)
        result=(df,"Procon-SP varejo")
    st.session_state[key_data]=result
    st.session_state[key_ts]=now
    return result
    df=pd.DataFrame(records).drop_duplicates("mes").sort_values("mes").reset_index(drop=True)
    return df,"Procon-SP varejo"

@st.cache_data(ttl=43200,show_spinner="🇦🇷 Cargando datos INDEC Argentina…")
def scrape_argentina():
    """INDEC IPC Precios Promedio — Huevos de gallina — GBA retail consumidor con IVA"""
    try:
        r=requests.get("https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_precios_promedio.xls",
                       headers=HEADERS,timeout=30)
        r.raise_for_status()
    except Exception as e: return None,str(e)
    try:
        wb=xlrd.open_workbook(file_contents=r.content)
        sh=wb.sheet_by_index(0)
        meses_map={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
                   "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
        # Build column→(year,month) index from header rows 2 and 3
        dates={}; current_year=None
        for col in range(3,sh.ncols):
            yr_raw=str(sh.cell_value(2,col)).strip()
            m_yr=re.search(r'(\d{4})',yr_raw)
            if m_yr: current_year=int(m_yr.group(1))
            mo_raw=str(sh.cell_value(3,col)).strip().lower()
            if mo_raw in meses_map and current_year:
                dates[col]=(current_year,meses_map[mo_raw])
        # Find GBA Huevos de gallina row
        huevos_row=None
        for row in range(sh.nrows):
            if str(sh.cell_value(row,0)).strip()=="GBA" and "huevo" in str(sh.cell_value(row,1)).lower():
                huevos_row=row; break
        if huevos_row is None: return None,"No encontrado Huevos de gallina GBA"
        records=[]
        for col,(year,month) in dates.items():
            raw=sh.cell_value(huevos_row,col)
            try:
                price=float(str(raw).replace(',','.').strip())
                if price>0:
                    records.append({"mes":f"{year}-{month:02d}",
                        "fecha":pd.Timestamp(f"{year}-{month:02d}-01"),
                        "precio_ars":round(price/12,4)})
            except: pass
        if not records: return None,"Sin valores INDEC"
        df=pd.DataFrame(records).drop_duplicates("mes").sort_values("mes").reset_index(drop=True)
        return df,None
    except Exception as e: return None,str(e)

@st.cache_data(ttl=43200,show_spinner="🇨🇱 Cargando datos ODEPA Chile…")
def scrape_chile():
    urls=[
        "https://datos.odepa.gob.cl/dataset/d4646b7f-0d2e-4567-b6fa-932b1a6bb3f3/resource/9f885df4-afeb-4b75-8bab-9334f79db00f/download/precio_consumidor_2026.csv",
        "https://datos.odepa.gob.cl/dataset/d4646b7f-0d2e-4567-b6fa-932b1a6bb3f3/resource/eab239c4-e338-4cde-a9e0-7c4f27826030/download/precio_consumidor_2025.csv",
        "https://datos.odepa.gob.cl/dataset/d4646b7f-0d2e-4567-b6fa-932b1a6bb3f3/resource/5f773b96-6c3a-4017-b871-6340d779ea96/download/precio_consumidor_2024.csv",
        "https://datos.odepa.gob.cl/dataset/d4646b7f-0d2e-4567-b6fa-932b1a6bb3f3/resource/1a73ae5d-f4e2-4706-b2c3-e1e05a23fcb6/download/precio_consumidor_2023.csv",
        "https://datos.odepa.gob.cl/dataset/d4646b7f-0d2e-4567-b6fa-932b1a6bb3f3/resource/e9c3f2fc-9bb7-4f5f-a529-d1d60d7a61a5/download/precio_consumidor_2022.csv",
    ]
    df_all=[]
    for url in urls:
        try:
            r=requests.get(url,headers=HEADERS,timeout=20)
            if r.status_code!=200 or len(r.content)<500: continue
            df=pd.read_csv(StringIO(r.content.decode("utf-8-sig")),sep=",",engine="python")
            df.columns=[c.strip() for c in df.columns]
            df_e=df[df["Producto"].str.contains("blanco",case=False,na=False)].copy()
            df_g=df_e[df_e["Producto"].str.contains("grande",case=False,na=False)]
            if not df_g.empty: df_e=df_g
            df_e=df_e[df_e["Tipo de punto monitoreo"].str.contains("Feria libre",case=False,na=False)].copy()
            if df_e.empty: continue
            df_e["precio_clp_raw"]=pd.to_numeric(df_e["Precio promedio"].astype(str).str.replace(",",".",regex=False),errors="coerce")
            def clp_x_h(row):
                p=row["precio_clp_raw"]; u=str(row["Unidad"])
                if pd.isna(p): return None
                nums=re.findall(r'\d+',u); n=int(nums[-1]) if nums else 12
                return p/n
            df_e["precio_clp"]=df_e.apply(clp_x_h,axis=1)
            df_e["mes"]=df_e["Anio"].astype(str)+"-"+df_e["Mes"].astype(str).str.zfill(2)
            m=df_e.groupby("mes")["precio_clp"].mean().round(2).reset_index(); m.columns=["mes","precio_clp"]; df_all.append(m)
        except: continue
    if not df_all: return None,"Sin datos ODEPA"
    df=pd.concat(df_all).drop_duplicates("mes").sort_values("mes").reset_index(drop=True)
    df["fecha"]=pd.to_datetime(df["mes"]+"-01")
    return df,None

def _usa_ams_txt():
    """USDA AMS nw_py018.txt — Prices Paid to Producers Iowa-MN-WI Large (cents/doz)"""
    records=[]
    try:
        r=requests.get("https://www.ams.usda.gov/mnreports/nw_py018.txt",headers=HEADERS,timeout=15)
        if r.status_code!=200: return records
        text=r.text
        # Date: "FOR THE WEEK OF  JANUARY 31, 2025" or similar
        m_date=re.search(r'FOR THE WEEK OF\s+([A-Z]+ \d{1,2},\s*\d{4})',text,re.IGNORECASE)
        if not m_date: return records
        ts=pd.Timestamp(m_date.group(1).strip())
        # Iowa-MN-WI section → LARGE MOSTLY: NNN
        idx=text.find('IOWA-MN-WI')
        if idx<0: return records
        section=text[idx:idx+400]
        m_p=re.search(r'LARGE[^\n]*?MOSTLY\s*[:\-]?\s*(\d{3,4})',section,re.IGNORECASE)
        if not m_p: return records
        price_usd=float(m_p.group(1))/100/12
        records.append({"mes":f"{ts.year}-{ts.month:02d}",
            "fecha":pd.Timestamp(f"{ts.year}-{ts.month:02d}-01"),
            "precio_usd":round(price_usd,6)})
    except: pass
    return records

def _usa_ams_pdf():
    """USDA AMS ams_2848.pdf — Prices Paid to Producers, formato vigente desde feb 2025"""
    records=[]
    try:
        r=requests.get("https://www.ams.usda.gov/mnreports/ams_2848.pdf",headers=HEADERS,timeout=20)
        if r.status_code!=200 or len(r.content)<10000: return records
        with pdfplumber.open(BytesIO(r.content)) as pdf:
            full_text=""
            for page in pdf.pages:
                full_text+=(page.extract_text() or "")
            # Date header: "JANUARY 31, 2025" or "Week of January 31, 2025"
            m_date=re.search(r'(?:Week of\s+)?([A-Z][a-z]+ \d{1,2},?\s*\d{4})',full_text)
            if not m_date: return records
            ts=pd.Timestamp(m_date.group(1).replace(',','').strip())
            # "PRICES PAID TO PRODUCERS" section → Large eggs, Midwest/Iowa
            idx=full_text.upper().find('PRICES PAID TO PRODUCERS')
            if idx<0:
                # fallback: any "LARGE MOSTLY NNN" pattern
                m_p=re.search(r'LARGE[^\n]{0,30}MOSTLY[^\n]{0,20}?(\d{3,4})',full_text,re.IGNORECASE)
            else:
                section=full_text[idx:idx+800]
                m_p=re.search(r'LARGE[^\n]{0,30}MOSTLY[^\n]{0,20}?(\d{3,4})',section,re.IGNORECASE)
            if not m_p: return records
            price_usd=float(m_p.group(1))/100/12
            records.append({"mes":f"{ts.year}-{ts.month:02d}",
                "fecha":pd.Timestamp(f"{ts.year}-{ts.month:02d}-01"),
                "precio_usd":round(price_usd,6)})
    except: pass
    return records

@st.cache_data(ttl=43200,show_spinner="🇺🇸 Cargando datos USDA / FRED USA…")
def scrape_usa():
    """USDA AMS Prices Paid to Producers (Iowa-MN-WI Large) + FRED retail fallback"""
    # FRED: retail history (APU0000708111), largo historial
    fred_records=[]
    try:
        r=requests.get(f"https://api.stlouisfed.org/fred/series/observations?series_id=APU0000708111&api_key={FRED_API_KEY}&file_type=json&sort_order=desc&limit=60",timeout=15)
        obs=r.json().get("observations",[])
        fred_records=[{"mes":o["date"][:7],"precio_usd":float(o["value"])/12,
            "fecha":pd.Timestamp(o["date"][:7]+"-01")} for o in obs if o.get("value",".")!="."]
    except: pass
    # USDA AMS: precios productor (más recientes, pueden solapar con FRED)
    ams_records=_usa_ams_txt() or _usa_ams_pdf()
    # USDA AMS tiene prioridad sobre FRED: ponerlo al final → keep="last" lo mantiene
    all_records=fred_records+ams_records
    if not all_records: return None,"Sin datos USA"
    df=(pd.DataFrame(all_records)
        .drop_duplicates("mes",keep="last")         # USDA AMS (al final) pisa FRED si hay overlap
        .sort_values("mes").reset_index(drop=True))
    return df,None

# ── Plotly layout ─────────────────────────────────────────────────────────────
LAYOUT=dict(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="JetBrains Mono,monospace",color="#9ca3af",size=11),
    xaxis=dict(gridcolor="#1e2535",showgrid=True,zeroline=False,tickfont=dict(color="#6b7280"),tickformat="%b %Y"),
    yaxis=dict(gridcolor="#1e2535",showgrid=True,zeroline=False,tickfont=dict(color="#6b7280")),
    legend=dict(bgcolor="rgba(13,20,35,0.8)",bordercolor="#1e2535",borderwidth=1,font=dict(size=11)),
    margin=dict(l=10,r=10,t=40,b=10),hovermode="x unified",
    hoverlabel=dict(bgcolor="#0f1829",bordercolor="#334155",font=dict(family="JetBrains Mono,monospace",size=12)))

def make_excel(df_br,df_ar,df_cl,df_us):
    buf=BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as w:
        if df_br is not None and "precio_brl" in df_br.columns:
            df_br[["mes","precio_brl"]].to_excel(w,sheet_name="Brasil_BRL_huevo",index=False)
        if df_ar is not None and "precio_ars" in df_ar.columns:
            df_ar[["mes","precio_ars"]].to_excel(w,sheet_name="Argentina_ARS_huevo",index=False)
        if df_cl is not None: df_cl[["mes","precio_clp"]].to_excel(w,sheet_name="Chile_CLP_huevo",index=False)
        if df_us is not None: df_us[["mes","precio_usd"]].to_excel(w,sheet_name="USA_USD_huevo",index=False)
    return buf.getvalue()

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN: MENÚ PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
def render_menu():
    st.markdown("""
    <div style="text-align:center;padding:40px 0 30px;">
        <div style="font-size:52px;margin-bottom:12px;">🥚</div>
        <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:2.2rem;letter-spacing:-1px;color:#e8e6e1;margin-bottom:8px;">
            Monitor de Huevos
        </div>
        <div style="font-size:12px;color:#374151;font-family:'JetBrains Mono',monospace;letter-spacing:2px;">
            HERRAMIENTAS DE ANÁLISIS · CHILE
        </div>
    </div>
    """, unsafe_allow_html=True)

    _CARD = (
        "background:#0f1829;border:1px solid #2a3a5c;border-radius:16px;"
        "padding:40px 36px;text-align:center;"
    )
    _ICON = "font-size:52px;margin-bottom:16px;"
    _TITLE = "font-size:1.4rem;font-weight:800;color:#e8e6e1;margin-bottom:8px;font-family:'Syne',sans-serif;"
    _DESC = "font-size:12px;color:#4a5568;line-height:1.7;font-family:'JetBrains Mono',monospace;"

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(f"""
        <div style="{_CARD}">
            <div style="{_ICON}">📈</div>
            <div style="{_TITLE}">Precios internacionales</div>
            <div style="{_DESC}">
                Monitoreo en tiempo real del precio del huevo en<br>
                Brasil · Argentina · Chile · USA<br><br>
                Fuentes: Procon-SP · INDEC · ODEPA · FRED/BLS<br>
                Precios retail consumidor · CLP o USD · ARS a tipo MEP
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📈  Abrir Precios internacionales", key="btn_precios", use_container_width=True):
            st.session_state.seccion = "precios"
            st.rerun()

    with col2:
        st.markdown(f"""
        <div style="{_CARD}">
            <div style="{_ICON}">🚢</div>
            <div style="{_TITLE}">Importaciones a Chile</div>
            <div style="{_DESC}">
                Análisis de tendencias de importación<br>
                Partidas arancelarias 407xx y 408xx<br><br>
                Sube archivos mensuales de aduana · Historial acumulado<br>
                Cálculo de N° huevos · Gráficos de tendencia
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚢  Abrir Importaciones a Chile", key="btn_imp", use_container_width=True):
            st.session_state.seccion = "importaciones"
            st.rerun()

    # version notification
    try:
        latest = check_latest_version()
        if latest and latest != APP_VERSION:
            lv = tuple(int(x) for x in latest.split('.'))
            cv = tuple(int(x) for x in APP_VERSION.split('.'))
            if lv > cv:
                st.info(
                    f"🆕 **Nueva versión disponible: v{latest}** (tienes v{APP_VERSION})  \n"
                    f"Descarga la nueva versión desde [GitHub](https://github.com/pirarrazabalmujica-dev/calculadora-huevos) "
                    f"y reemplaza tu archivo **Monitor_Huevos.bat**.",
                    icon="🆕"
                )
    except Exception:
        pass

    st.markdown(f"""
    <div style="text-align:center;margin-top:40px;font-size:10px;color:#1e2535;font-family:'JetBrains Mono',monospace;">
        v{APP_VERSION} · {datetime.now().strftime("%d/%m/%Y %H:%M")}
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN: PRECIOS INTERNACIONALES
# ══════════════════════════════════════════════════════════════════════════════
def render_precios():
    if st.button("← Volver al menú", key="back_precios"):
        st.session_state.seccion = "menu"
        st.rerun()

    st.markdown(f"""
    <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.8rem;letter-spacing:-1px;margin-bottom:6px;">
        📈 Precios internacionales del huevo
    </div>
    <div style="margin-bottom:20px;">
        <span class="fuente-badge">🇧🇷 Procon-SP</span><span class="fuente-badge">🇦🇷 INDEC</span>
        <span class="fuente-badge">🇨🇱 ODEPA</span><span class="fuente-badge">🇺🇸 FRED/BLS</span>
        <span style="font-size:10px;color:#374151;font-family:'JetBrains Mono',monospace;">{datetime.now().strftime("%d/%m/%Y %H:%M")}</span>
    </div>
    """, unsafe_allow_html=True)

    # Detectar si Brasil ya está en caché para no mostrar el status innecesariamente
    _br_cached = (datetime.now().timestamp() - st.session_state.get("brasil_ts",0)) < _BRASIL_TTL

    if _br_cached:
        # Todo cacheado → carga instantánea
        with st.spinner("Cargando datos..."):
            fx=get_fx()
            df_br,e_br=scrape_brasil()
            df_ar,e_ar=scrape_argentina()
            df_cl,e_cl=scrape_chile()
            df_us,e_us=scrape_usa()
    else:
        # Primera carga del día → mostrar progreso detallado
        fx=get_fx()
        with st.status("⏳ Descargando datos de mercado…", expanded=True) as status:
            status.update(label="🇧🇷 Descargando PDFs Procon-SP…")
            df_br,e_br=scrape_brasil(on_status=lambda msg: status.update(label=msg))
            status.update(label="🇦🇷 Descargando INDEC Argentina…")
            df_ar,e_ar=scrape_argentina()
            status.update(label="🇨🇱 Descargando ODEPA Chile…")
            df_cl,e_cl=scrape_chile()
            status.update(label="🇺🇸 Descargando USDA / FRED USA…")
            df_us,e_us=scrape_usa()
            status.update(label="✅ Datos cargados", state="complete", expanded=False)

    with st.sidebar:
        st.markdown("### ⚙️ Opciones")
        st.markdown("**💰 Moneda**")
        moneda=st.radio("",["CLP (pesos chilenos)","USD (dólares)"],index=0)
        en_usd=moneda=="USD (dólares)"; m_lbl="USD" if en_usd else "CLP"; vfmt=".4f" if en_usd else ".0f"

        def conv(v,tipo):
            if v is None: return None
            r={"BRL":fx["BRL_USD"] if en_usd else fx["BRL_CLP"],"ARS":fx["ARS_USD"] if en_usd else fx["ARS_CLP"],
               "CLP":fx["CLP_USD"] if en_usd else 1.0,"USD":1.0 if en_usd else fx["USD_CLP"]}
            return v*r.get(tipo,1)

        st.markdown("---")
        st.markdown("**🌎 Series**")
        show_br=st.checkbox("🇧🇷 Brasil (Procon-SP)",value=True)
        show_ar=st.checkbox("🇦🇷 Argentina (INDEC)",value=True)
        show_cl=st.checkbox("🇨🇱 Chile (ODEPA)",value=True)
        show_us=st.checkbox("🇺🇸 USA (USDA/FRED)",value=True)

        st.markdown("---")
        st.markdown("**📅 Período**")
        if "rango_v3" not in st.session_state:
            st.session_state.rango_v3="3A"
        rango=st.radio("",["6M","1A","2A","3A","Todo"],key="rango_v3",horizontal=True)
        rango_map={"6M":6,"1A":12,"2A":24,"3A":36,"Todo":None}
        meses_rango=rango_map[rango]
        def filtrar(df,col="fecha"):
            if df is None or meses_rango is None: return df
            cutoff=pd.Timestamp.now()-pd.DateOffset(months=meses_rango)
            return df[df[col]>=cutoff].reset_index(drop=True)

        st.markdown("---")
        st.markdown(f"""<div style="font-size:10px;font-family:'JetBrains Mono',monospace;color:#374151;line-height:2;">
        💱 1 USD = CLP${fx['USD_CLP']:,.0f}<br>💱 1 BRL = CLP${fx['BRL_CLP']:.1f}<br>💱 1 ARS = CLP${fx['ARS_CLP']:.4f} <span style="color:#1e3a2f;">(MEP)</span>
        </div>""", unsafe_allow_html=True)

    # KPI Cards
    c1,c2,c3,c4=st.columns(4)
    def kpi(col_obj,label,color,v,m_l,vf,sub):
        cv=conv(v[0],v[1]) if v[0] else 0
        col_obj.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{color};">{cv:{vf}}</div>
            <div class="kpi-sub">{m_l}/huevo · {sub}</div>
        </div>""", unsafe_allow_html=True)

    with c1:
        if df_br is not None:
            v,m=last_val(df_br,"precio_brl")
            kpi(c1,"🇧🇷 Brasil · Procon-SP varejo","#f97316",(v,"BRL"),m_lbl,vfmt,f"R${v:.4f} · {m}" if v else "Sin datos")
    with c2:
        if df_ar is not None:
            v,m=last_val(df_ar,"precio_ars")
            kpi(c2,"🇦🇷 Argentina · GBA · MEP","#60a5fa",(v,"ARS"),m_lbl,vfmt,f"ARS${v:.2f} · {m}" if v else "Sin datos")
    with c3:
        if df_cl is not None:
            v,m=last_val(df_cl,"precio_clp")
            kpi(c3,"🇨🇱 Chile · Feria libre","#4ade80",(v,"CLP"),m_lbl,vfmt,f"CLP${v:.0f} · {m}" if v else "Sin datos")
    with c4:
        if df_us is not None:
            v,m=last_val(df_us,"precio_usd")
            kpi(c4,"🇺🇸 USA · Grade A Large","#e879f9",(v,"USD"),m_lbl,vfmt,f"USD${v:.4f} · {m}" if v else "Sin datos")

    st.markdown("<br>",unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📈 Evolución de precios", "📋 Datos"])

    def hover(name):
        decimals=4 if en_usd else 0
        return f"<b>{name}</b><br>%{{x|%B %Y}}: <b>%{{y:,.{decimals}f}}</b> {m_lbl}/huevo<extra></extra>"

    with tab1:
        fig=go.Figure()
        fbr=filtrar(df_br); far=filtrar(df_ar); fcl=filtrar(df_cl); fus=filtrar(df_us)
        if show_br and fbr is not None and "precio_brl" in fbr.columns:
            y=fbr["precio_brl"].apply(lambda v: conv(v,"BRL"))
            fig.add_trace(go.Scatter(x=fbr["fecha"],y=y,name="🇧🇷 Brasil",
                line=dict(color="#f97316",width=2.5),mode="lines+markers",
                marker=dict(size=4),hovertemplate=hover("🇧🇷 Brasil")))
        if show_ar and far is not None and "precio_ars" in far.columns:
            y=far["precio_ars"].apply(lambda v: conv(v,"ARS"))
            fig.add_trace(go.Scatter(x=far["fecha"],y=y,name="🇦🇷 Argentina",
                line=dict(color="#60a5fa",width=2),mode="lines+markers",
                marker=dict(size=4),hovertemplate=hover("🇦🇷 Argentina")))
        if show_cl and fcl is not None:
            y=fcl["precio_clp"].apply(lambda v: conv(v,"CLP"))
            fig.add_trace(go.Scatter(x=fcl["fecha"],y=y,name="🇨🇱 Chile",
                line=dict(color="#4ade80",width=2,dash="dot"),mode="lines+markers",
                marker=dict(size=4),hovertemplate=hover("🇨🇱 Chile")))
        if show_us and fus is not None:
            y=fus["precio_usd"].apply(lambda v: conv(v,"USD"))
            fig.add_trace(go.Scatter(x=fus["fecha"],y=y,name="🇺🇸 USA",
                line=dict(color="#e879f9",width=2,dash="dashdot"),mode="lines+markers",
                marker=dict(size=4),hovertemplate=hover("🇺🇸 USA")))
        fig.update_layout(**LAYOUT,yaxis_title=f"{m_lbl}/huevo",height=440,
            title=dict(text=f"Precio por huevo · {m_lbl} · ARS a tipo MEP",font=dict(size=12,color="#4a5568")))
        st.plotly_chart(fig,use_container_width=True)
        st.markdown(
            '<div class="nota">'
            '🇧🇷 Procon-SP · Ovos Brancos dúzia · varejo São Paulo · con impuestos · '
            '🇦🇷 INDEC IPC · Huevos de gallina docena · GBA · retail consumidor con IVA · tipo cambio MEP · '
            '🇨🇱 ODEPA · huevo grande blanco · feria libre · consumidor con IVA 19% · '
            '🇺🇸 FRED/BLS · Grade A Large · retail con impuestos'
            '</div>',
            unsafe_allow_html=True)
        st.download_button("📥 Descargar precios históricos (Excel)",
            data=make_excel(df_br,df_ar,df_cl,df_us),
            file_name=f"monitor_huevos_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with tab2:
        d1,d2=st.columns(2)
        with d1:
            fuente_br_lbl=(e_br if df_br is not None and e_br not in (None,"Sin datos Brasil") else "Procon-SP")
            st.markdown(f"**🇧🇷 Brasil (BRL/huevo · {fuente_br_lbl})**")
            if df_br is not None:
                st.dataframe(df_br[["mes","precio_brl"]].set_index("mes").round(4),use_container_width=True)
            st.markdown("**🇨🇱 Chile (CLP/huevo · ODEPA)**")
            if df_cl is not None:
                st.dataframe(df_cl[["mes","precio_clp"]].set_index("mes").round(2),use_container_width=True)
        with d2:
            st.markdown("**🇦🇷 Argentina (ARS/huevo · INDEC)**")
            if df_ar is not None:
                st.dataframe(df_ar[["mes","precio_ars"]].set_index("mes").round(4),use_container_width=True)
            st.markdown("**🇺🇸 USA (USD/huevo · USDA AMS/FRED)**")
            if df_us is not None:
                st.dataframe(df_us[["mes","precio_usd"]].set_index("mes").round(4),use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN: IMPORTACIONES
# ══════════════════════════════════════════════════════════════════════════════
def scrape_produccion_cl(on_status=None):
    """Chilehuevos — producción mensual total de huevos Chile (boletines PDF)"""
    import pickle as _pickle, time as _time
    _cache_path = os.path.join(os.path.dirname(__file__), "_prod_cl_cache.pkl")
    def _log(msg):
        if on_status: on_status(msg)
    # ── Cache manual (24 h) ────────────────────────────────────────────────────
    if os.path.exists(_cache_path):
        try:
            with open(_cache_path, "rb") as _cf:
                _cached = _pickle.load(_cf)
            if _time.time() - _cached.get("ts", 0) < 86400:
                _log("✅ Usando datos en caché (menos de 24 h)")
                return _cached["data"]
        except Exception:
            pass
    MES = {'ene':1,'feb':2,'mar':3,'abr':4,'may':5,'jun':6,
           'jul':7,'ago':8,'sep':9,'sept':9,'oct':10,'nov':11,'dic':12}
    NOMBRES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
               'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

    _ocr_reader = [None]  # lazy singleton inside cached function

    def _get_ocr_reader():
        if _ocr_reader[0] is None:
            try:
                import easyocr
                _ocr_reader[0] = easyocr.Reader(['es'], gpu=False, verbose=False)
            except Exception:
                pass
        return _ocr_reader[0]

    def parse_pdf_ocr(content):
        """Fallback OCR para PDFs con tablas como imagen (Chilehuevos 2026+)."""
        result = {}
        try:
            import fitz as _fitz
            import numpy as _np
            from PIL import Image as _PILImg
            import time as _t
            reader = _get_ocr_reader()
            if reader is None:
                return result
            doc = _fitz.open(stream=content, filetype="pdf")
            n_pages = min(3, len(doc))
            month_pat = re.compile(
                r'^(ene|feb|mar|abr|may|jun|jul|ago|sept?|oct|nov|dic)[\s\-](\d{2})$',
                re.IGNORECASE)
            _ocr_page_times = []
            for pg_idx in range(n_pages):
                # Estimate remaining time from previous pages
                if _ocr_page_times:
                    avg = sum(_ocr_page_times) / len(_ocr_page_times)
                    remaining = avg * (n_pages - pg_idx)
                    _log(f"   🔬 OCR página {pg_idx+1}/{n_pages}… (~{remaining:.0f}s restantes)")
                else:
                    _log(f"   🔬 OCR página {pg_idx+1}/{n_pages}… (estimando tiempo…)")
                _page_t0 = _t.time()
                page = doc[pg_idx]
                pix = page.get_pixmap(matrix=_fitz.Matrix(2.5, 2.5))
                img = _PILImg.open(BytesIO(pix.tobytes('png')))
                items = reader.readtext(_np.array(img), detail=1)
                _elapsed = _t.time() - _page_t0
                _ocr_page_times.append(_elapsed)
                _log(f"   ✅ Página {pg_idx+1}/{n_pages} lista — {_elapsed:.0f}s — {len(items)} textos detectados")
                for _bbox, _text, _conf in items:
                    if _conf < 0.5:
                        continue
                    clean = _text.strip().replace(' ', '-').replace('–', '-')
                    mm = month_pat.match(clean)
                    if not mm:
                        continue
                    mes_num = MES.get(mm.group(1).lower(), 0)
                    if not mes_num:
                        continue
                    anio = int('20' + mm.group(2))
                    if not (2018 <= anio <= 2035):
                        continue
                    lx, ly = _bbox[0][0], _bbox[0][1]
                    # First large number strictly to the right at same row
                    candidates = []
                    for _b2, _t2, _c2 in items:
                        ix, iy = _b2[0][0], _b2[0][1]
                        if ix > lx and abs(iy - ly) < 28 and _c2 > 0.3:
                            num_s = re.sub(r'[^0-9]', '', _t2)
                            if len(num_s) >= 8:
                                try:
                                    val = int(num_s)
                                    if 50_000_000 < val < 800_000_000:
                                        candidates.append((ix, val))
                                except ValueError:
                                    pass
                    if candidates:
                        candidates.sort(key=lambda c: c[0])
                        key = f"{anio}-{mes_num:02d}"
                        if key not in result:
                            result[key] = candidates[0][1]
                # -- Tabla cruzada: Mes-fila x Año-columna (valores en miles) --
                # Captura proyecciones de produccion para meses futuros del año actual
                try:
                    yr_cols = [(int(_tt.strip()), (_bb[0][0]+_bb[1][0])/2)
                               for _bb, _tt, _cc in items
                               if _cc > 0.5 and re.match(r'^20\d{2}$', _tt.strip())]
                    if yr_cols:
                        latest_yr = max(x[0] for x in yr_cols)
                        if 2021 <= latest_yr <= 2035:
                            cx_list = list(set(x[1] for x in yr_cols if x[0] == latest_yr))
                            MES_FULL = {'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,
                                        'junio':6,'julio':7,'agosto':8,'septiembre':9,
                                        'octubre':10,'noviembre':11,'diciembre':12}
                            for _bb, _tt, _cc in items:
                                if _cc < 0.4:
                                    continue
                                mn = _tt.strip().lower()
                                if mn not in MES_FULL:
                                    continue
                                mes_num_f = MES_FULL[mn]
                                my = (_bb[0][1] + _bb[2][1]) / 2
                                for cx in cx_list:
                                    bv, bdx = None, 999
                                    for _b2, _t2, _c2 in items:
                                        if _c2 < 0.3:
                                            continue
                                        y2 = (_b2[0][1] + _b2[2][1]) / 2
                                        if abs(y2 - my) > 20:
                                            continue
                                        x2 = (_b2[0][0] + _b2[1][0]) / 2
                                        dx = abs(x2 - cx)
                                        if dx > 60:
                                            continue
                                        ns = re.sub(r'[^0-9]', '', _t2)
                                        if 4 <= len(ns) <= 7 and dx < bdx:
                                            v = int(ns) * 1000
                                            if 100_000_000 < v < 600_000_000:
                                                bv, bdx = v, dx
                                    if bv is not None:
                                        k2 = f"{latest_yr}-{mes_num_f:02d}"
                                        if k2 not in result:
                                            result[k2] = bv
                except Exception:
                    pass
                # Early-exit: la tabla está en la página 1; si ya hay datos,
                # no gastamos OCR en las páginas restantes (~20-30s c/u)
                if result:
                    if pg_idx + 1 < n_pages:
                        _log(f"   ⏭️ Datos hallados en página {pg_idx+1} — omito {n_pages-(pg_idx+1)} página(s) restante(s)")
                    break
        except Exception:
            pass
        return result

    def parse_pdf(content):
        """Extrae {YYYY-MM: total_huevos} de un boletín PDF.
        Intenta extracción de texto primero; si falla usa OCR."""
        result = {}
        try:
            with pdfplumber.open(BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    for line in text.split("\n"):
                        m = re.match(
                            r'(ene|feb|mar|abr|may|jun|jul|ago|sept?|oct|nov|dic)'
                            r'-(\d{2})\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)',
                            line.strip(), re.IGNORECASE)
                        if m:
                            mes_num = MES.get(m.group(1).lower(), 0)
                            anio = int('20' + m.group(2))
                            total = int(m.group(6).replace('.',''))
                            if mes_num and 50_000_000 < total < 800_000_000:
                                result[f"{anio}-{mes_num:02d}"] = total
        except Exception:
            pass
        # Fallback: tabla en imagen → OCR (PDFs Chilehuevos 2026+)
        if not result:
            _log("⚡ Texto no encontrado — usando OCR (puede tardar 1-2 min)…")
            result = parse_pdf_ocr(content)
            if result:
                _log(f"✅ OCR completado — {len(result)} mes(es) extraídos")
            else:
                _log("⚠️ OCR no encontró datos en este PDF")
        return result

    def try_urls(year, month):
        nombre = NOMBRES[month-1]
        base = "https://www.chilehuevos.cl/storage"
        _log(f"🔍 Buscando PDF: {nombre} {year}…")
        paths = [
            # acento pre-compuesto (UTF-8 normal): Boletín
            f"{base}/boletines/Bolet%C3%ADn%20Chilehuevos%20-%20{nombre}%20{year}.pdf",
            # acento descompuesto (i + combining accent): Boletín — usado en algunos 2026
            f"{base}/boletines/Boleti%CC%81n%20Chilehuevos%20-%20{nombre}%20{year}.pdf",
            f"{base}/Bolet%C3%ADn%20Chilehuevos%20-%20{nombre}%20{year}.pdf",
        ]
        for url in paths:
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                if r.status_code == 200 and len(r.content) > 10_000:
                    _log(f"📥 PDF encontrado: {nombre} {year} — {len(r.content)//1024} KB")
                    return r.content
            except Exception:
                pass
        return None

    data = {}
    now = datetime.now()

    def fetch_pdf_near(target_yr, target_mo, window=9):
        """Busca el PDF más cercano a (target_yr, target_mo) en ventana ±window meses."""
        for delta in range(0, window + 1):
            for sign in ([0] if delta == 0 else [-1, 1]):
                mo = target_mo + sign * delta
                yr = target_yr
                while mo < 1:  mo += 12; yr -= 1
                while mo > 12: mo -= 12; yr += 1
                content = try_urls(yr, mo)
                if content:
                    parsed = parse_pdf(content)
                    if parsed:
                        return parsed
        return {}

    # Anclas en now, now-2, now-4 para cubrir ~5 años.
    # Buscar en ventana ±9 meses alrededor de cada ancla (no solo hacia atrás)
    # para no perderse PDFs publicados después del mes ancla.
    _anchors = [0, 1, 2, 4]
    for _i, offset in enumerate(_anchors):
        anchor_yr = now.year - offset
        anchor_mo = now.month
        _log(f"📅 Bloque {_i+1}/{len(_anchors)}: buscando datos de {anchor_yr}…")
        pdf_data = fetch_pdf_near(anchor_yr, anchor_mo, window=9)
        for k, v in pdf_data.items():
            if k not in data:
                data[k] = v
        if pdf_data:
            _first = min(pdf_data.keys()); _last = max(pdf_data.keys())
            _log(f"   ↳ {len(pdf_data)} meses extraídos ({_first} → {_last})")
        else:
            _log(f"   ↳ Sin datos para {anchor_yr}")

    _log(f"💾 Guardando caché ({len(data)} meses en total)…")
    try:
        with open(_cache_path, "wb") as _cf:
            _pickle.dump({{"ts": _time.time(), "data": data}}, _cf)
    except Exception:
        pass
    return data

def render_importaciones():
    if st.button("← Volver al menú", key="back_imp"):
        st.session_state.seccion = "menu"
        st.rerun()

    st.markdown("""
    <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.8rem;letter-spacing:-1px;margin-bottom:16px;">
        🚢 Importaciones de huevos a Chile
    </div>
    """, unsafe_allow_html=True)

    html_path = os.path.join(os.path.dirname(__file__), "importaciones.html")
    if not os.path.exists(html_path):
        st.error("⚠️ No se encontró el archivo `importaciones.html` en la misma carpeta que `app.py`.")
        st.info("Asegúrate de que ambos archivos estén en la misma carpeta.")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Datos de producción nacional (Chilehuevos) — inyectados como variable JS
    import json as _json
    with st.status("🐔 Cargando producción nacional (Chilehuevos)…", expanded=True) as _st:
        _prog = st.progress(0, text="Iniciando…")
        # Etapas esperadas: 4 bloques año + mensajes intermedios
        # Usamos contadores simples para estimar avance
        _step_state = {"block": 0, "total_blocks": 4}

        def _on_status(msg):
            _st.write(msg)
            msg_l = msg.lower()
            if "↳" in msg:
                _step_state["block"] += 1
                pct = min(_step_state["block"] / _step_state["total_blocks"], 0.92)
                _prog.progress(pct, text=f"Bloque {_step_state['block']}/{_step_state['total_blocks']} completado…")
            elif "caché" in msg_l:
                _prog.progress(1.0, text="Datos listos desde caché")
            elif "guardando" in msg_l:
                _prog.progress(0.98, text="Guardando caché…")
            elif "🔬" in msg:
                # OCR processing a page — show block base + page fraction
                import re as _re
                _m = _re.search(r'(\d+)/(\d+)', msg)
                if _m:
                    _pg, _tot = int(_m.group(1)), int(_m.group(2))
                    # base: current block progress; add fractional page within 15% band
                    _base = _step_state["block"] / _step_state["total_blocks"]
                    _band = 0.15
                    _pct = min(_base + (_pg - 1) / _tot * _band + 0.02, 0.94)
                    _prog.progress(_pct, text=f"OCR página {_pg}/{_tot}…")
            elif "✅" in msg and "página" in msg_l:
                # Page finished — advance to that page's completion
                import re as _re
                _m = _re.search(r'(\d+)/(\d+)', msg)
                if _m:
                    _pg, _tot = int(_m.group(1)), int(_m.group(2))
                    _base = _step_state["block"] / _step_state["total_blocks"]
                    _band = 0.15
                    _pct = min(_base + _pg / _tot * _band, 0.94)
                    _prog.progress(_pct, text=f"OCR página {_pg}/{_tot} lista")

        prod_data = scrape_produccion_cl(on_status=_on_status)
        _last = max(prod_data.keys()) if prod_data else "sin datos"
        _prog.progress(1.0, text=f"Listo — {len(prod_data)} meses cargados")
        _st.update(
            label=f"✅ Producción cargada — {len(prod_data)} meses (hasta {_last})",
            state="complete", expanded=False
        )
    prod_script = f'<script>var PRODUCCION_CL={_json.dumps(prod_data)};</script>'

    # Borrar caché antiguo si existe
    for _f in ["html_b64.txt"]:
        _p = os.path.join(os.path.dirname(__file__), _f)
        if os.path.exists(_p):
            try: os.remove(_p)
            except: pass

    # Inyectar datos de producción e servir el HTML directamente
    # (el HTML incluye meta CSP que permite los scripts CDN desde el iframe)
    html_content = html_content.replace("</head>", prod_script + "</head>", 1)
    components.html(html_content, height=1150, scrolling=True)

# ══════════════════════════════════════════════════════════════════════════════
# ROUTER PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.seccion == "menu":
    render_menu()
elif st.session_state.seccion == "precios":
    render_precios()
elif st.session_state.seccion == "importaciones":
    render_importaciones()
