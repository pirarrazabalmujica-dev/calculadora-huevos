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
from bs4 import BeautifulSoup
from datetime import datetime
from io import StringIO
import streamlit.components.v1 as components
import re, os

FRED_API_KEY = "a80093ab267bd7a703209192064050b5"

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
/* Tarjetas del menú principal */
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

# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_num(s):
    s = str(s).strip()
    if not s or s in ["-","s/ cotação","","nan"]: return None
    if "." in s and "," in s: s = s.replace(".","").replace(",",".")
    elif "," in s: s = s.replace(",",".")
    try: return float(s)
    except: return None

def last_val(df, col):
    if df is None or col not in df.columns: return None, None
    s = df[col].dropna()
    if s.empty: return None, None
    return s.iloc[-1], df["mes"].iloc[s.index[-1]]

# ── Tipo de cambio ────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
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
    try:
        today=datetime.now().strftime("%Y-%m-%d"); first=datetime.now().strftime("%Y-%m-01")
        r=requests.get(f"https://api.bcra.gob.ar/estadisticas/v2.0/datosVariable/4/{first}/{today}",timeout=8,verify=False)
        a=float(r.json()["results"][-1]["valor"]); fx["ARS_USD"]=1/a; fx["ARS_CLP"]=u/a
    except: pass
    return fx

# ── Scrapers ──────────────────────────────────────────────────────────────────
HEADERS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Accept-Language":"es,pt;q=0.9"}

@st.cache_data(ttl=43200)
def scrape_brasil():
    try:
        r=requests.get("https://portaldeinformacoes.conab.gov.br/downloads/arquivos/PrecosMensalUF.txt",headers=HEADERS,timeout=30)
        r.raise_for_status()
    except Exception as e: return None, str(e)
    try:
        for enc in ["latin-1","utf-8","cp1252"]:
            try: content=r.content.decode(enc); break
            except: continue
        df=pd.read_csv(StringIO(content),sep=";",engine="python",dtype=str)
        df.columns=[c.strip().upper() for c in df.columns]
        prod=next((c for c in df.columns if "PRODUTO" in c),None)
        uf=next((c for c in df.columns if c in ["UF","ESTADO","SIGLA"]),None)
        ano=next((c for c in df.columns if c=="ANO"),None)
        mes=next((c for c in df.columns if "MES" in c and c!="ANO"),None)
        preco=next((c for c in df.columns if "PRECO" in c or "VALOR" in c),None)
        if not prod: return None,f"Cols:{list(df.columns)}"
        df_o=df[df[prod].str.contains("ovo|ova",case=False,na=False)].copy()
        if df_o.empty: return None,"Sin huevo"
        if ano and mes: df_o["mes"]=df_o[ano].str.strip()+"-"+df_o[mes].str.strip().str.zfill(2)
        elif mes: df_o["mes"]=df_o[mes].str.strip()
        else: return None,"Sin fecha"
        df_o["precio"]=pd.to_numeric(df_o[preco].astype(str).str.replace(",",".",regex=False),errors="coerce") if preco else None
        cutoff=(datetime.now().year-1)*100+datetime.now().month
        df_o=df_o[df_o["mes"].apply(lambda m:int(m.replace("-","")) if "-" in m else 0)>=cutoff]
        pivot=df_o.groupby(["mes",uf])["precio"].mean().unstack(uf).round(2).reset_index() if uf else df_o.groupby("mes")["precio"].mean().to_frame("Nacional").round(2).reset_index()
        pivot["fecha"]=pd.to_datetime(pivot["mes"]+"-01"); pivot=pivot.sort_values("mes")
        cols=[c for c in ["SP","PR","GO","AM","DF","RO","RS","MG"] if c in pivot.columns]
        if cols: pivot=pivot[["mes","fecha"]+cols]
        ncols=[c for c in pivot.columns if c not in ["mes","fecha"]]
        s=pivot[ncols].mean().mean()
        if s and s>10:
            for c in ncols: pivot[c]=pivot[c]/12
        return pivot,None
    except Exception as e: return None,str(e)

@st.cache_data(ttl=43200)
def scrape_argentina():
    meses_es=["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
    records=[]; cy=datetime.now().year
    # Todas las páginas anuales de CAPIA fueron publicadas el 2026/03/11
    # URL patrón: capia.com.ar/2026/03/11/precio-promedio-mensual-de-huevos-sin-i-v-a-{año}/
    for year in [cy, cy-1, cy-2, cy-3]:
        urls_try = [
            f"https://capia.com.ar/2026/03/11/precio-promedio-mensual-de-huevos-sin-i-v-a-{year}/",
            f"https://capia.com.ar/{cy}/03/11/precio-promedio-mensual-de-huevos-sin-i-v-a-{year}/",
        ]
        # Para el año actual también probar días recientes
        if year == cy:
            urls_try += [f"https://capia.com.ar/{cy}/03/{d:02d}/precio-promedio-mensual-de-huevos-sin-i-v-a-{cy}/" for d in range(1,20)]
        soup=None
        for url in urls_try:
            try:
                r=requests.get(url, headers=HEADERS, timeout=10)
                if r.status_code==200: soup=BeautifulSoup(r.text,"lxml"); break
            except: continue
        if not soup: continue
        for table in soup.find_all("table"):
            if "BUENOS AIRES" not in table.get_text() and "Buenos Aires" not in table.get_text(): continue
            rows=table.find_all("tr"); cyv=None
            for row in rows:
                cols=[c.get_text(strip=True) for c in row.find_all(["td","th"])]; cols=[c for c in cols if c]
                if not cols: continue
                if re.match(r'^\d{4}$',cols[0]): cyv=int(cols[0]); cols=cols[1:]
                if not cols: continue
                mn=cols[0]
                if any(x in mn.upper() for x in ["AÑO","MES","BLANCO","COLOR","AIRES","ENTRE","SANTA"]): continue
                if mn.lower() not in meses_es: continue
                prices=[parse_num(p) for p in cols[1:]]
                if any(p is not None for p in prices):
                    mn_num=meses_es.index(mn.lower())+1; año=cyv or year
                    records.append({"mes":f"{año}-{mn_num:02d}","fecha":pd.Timestamp(f"{año}-{mn_num:02d}-01"),
                        "BA_blanco":prices[0]/12 if prices[0] else None,
                        "BA_color":prices[1]/12 if len(prices)>1 and prices[1] else None,
                        "SF_blanco":prices[2]/12 if len(prices)>2 and prices[2] else None,
                        "ER_blanco":prices[4]/12 if len(prices)>4 and prices[4] else None})
    if not records: return None,"Sin datos CAPIA"
    df=pd.DataFrame(records); df=df[df["BA_blanco"].notna()].drop_duplicates("mes").sort_values("mes").reset_index(drop=True)
    return df,None

@st.cache_data(ttl=43200)
def scrape_chile():
    urls=["https://datos.odepa.gob.cl/dataset/d4646b7f-0d2e-4567-b6fa-932b1a6bb3f3/resource/9f885df4-afeb-4b75-8bab-9334f79db00f/download/precio_consumidor_2026.csv",
          "https://datos.odepa.gob.cl/dataset/d4646b7f-0d2e-4567-b6fa-932b1a6bb3f3/resource/eab239c4-e338-4cde-a9e0-7c4f27826030/download/precio_consumidor_2025.csv"]
    df_all=[]
    for url in urls:
        try:
            r=requests.get(url,headers=HEADERS,timeout=20)
            if r.status_code!=200 or len(r.content)<500: continue
            df=pd.read_csv(StringIO(r.content.decode("utf-8-sig")),sep=",",engine="python")
            df.columns=[c.strip() for c in df.columns]
            df_e=df[df["Producto"].str.contains("blanco",case=False,na=False)].copy()
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

@st.cache_data(ttl=43200)
def scrape_usa():
    try:
        r=requests.get(f"https://api.stlouisfed.org/fred/series/observations?series_id=APU0000708111&api_key={FRED_API_KEY}&file_type=json&sort_order=desc&limit=24",timeout=15)
        obs=r.json().get("observations",[])
        records=[{"mes":o["date"][:7],"precio_usd":float(o["value"])/12,"fecha":pd.Timestamp(o["date"][:7]+"-01")} for o in obs if o.get("value",".")!="."]
        if not records: return None,"Sin datos"
        return pd.DataFrame(records).sort_values("mes").reset_index(drop=True),None
    except Exception as e: return None,str(e)

# ── Plotly layout ─────────────────────────────────────────────────────────────
LAYOUT=dict(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="JetBrains Mono,monospace",color="#9ca3af",size=11),
    xaxis=dict(gridcolor="#1e2535",showgrid=True,zeroline=False,tickfont=dict(color="#6b7280"),tickformat="%b %Y"),
    yaxis=dict(gridcolor="#1e2535",showgrid=True,zeroline=False,tickfont=dict(color="#6b7280")),
    legend=dict(bgcolor="rgba(13,20,35,0.8)",bordercolor="#1e2535",borderwidth=1,font=dict(size=11)),
    margin=dict(l=10,r=10,t=40,b=10),hovermode="x unified",
    hoverlabel=dict(bgcolor="#0f1829",bordercolor="#334155",font=dict(family="JetBrains Mono,monospace",size=12)))

BR_COLORS={"SP":"#f97316","PR":"#fb923c","GO":"#fcd34d","AM":"#fdba74","DF":"#fed7aa","RO":"#fde68a","RS":"#f59e0b","MG":"#d97706"}
AR_COLORS={"BA_blanco":"#60a5fa","BA_color":"#93c5fd","SF_blanco":"#a78bfa","ER_blanco":"#c4b5fd"}

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

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("""
        <div class="menu-card" id="card-precios">
            <div class="menu-card-icon">📈</div>
            <div class="menu-card-title">Precios internacionales</div>
            <div class="menu-card-desc">
                Monitoreo en tiempo real del precio del huevo en<br>
                Brasil · Argentina · Chile · USA<br><br>
                Fuentes: CONAB · CAPIA · ODEPA · FRED/BLS<br>
                Actualización automática · CLP o USD
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir →", key="btn_precios", use_container_width=True):
            st.session_state.seccion = "precios"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="menu-card" id="card-imp">
            <div class="menu-card-icon">🚢</div>
            <div class="menu-card-title">Importaciones a Chile</div>
            <div class="menu-card-desc">
                Análisis de tendencias de importación<br>
                Partidas arancelarias 407xx y 408xx<br><br>
                Sube archivos mensuales de aduana · Historial acumulado<br>
                Cálculo de N° huevos · Gráficos de tendencia
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir →", key="btn_imp", use_container_width=True):
            st.session_state.seccion = "importaciones"
            st.rerun()

    st.markdown(f"""
    <div style="text-align:center;margin-top:40px;font-size:10px;color:#1e2535;font-family:'JetBrains Mono',monospace;">
        {datetime.now().strftime("%d/%m/%Y %H:%M")}
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN: PRECIOS INTERNACIONALES
# ══════════════════════════════════════════════════════════════════════════════
def render_precios():
    # Botón volver
    if st.button("← Volver al menú", key="back_precios"):
        st.session_state.seccion = "menu"
        st.rerun()

    st.markdown(f"""
    <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.8rem;letter-spacing:-1px;margin-bottom:6px;">
        📈 Precios internacionales del huevo
    </div>
    <div style="margin-bottom:20px;">
        <span class="fuente-badge">🇧🇷 CONAB</span><span class="fuente-badge">🇦🇷 CAPIA</span>
        <span class="fuente-badge">🇨🇱 ODEPA</span><span class="fuente-badge">🇺🇸 FRED/BLS</span>
        <span style="font-size:10px;color:#374151;font-family:'JetBrains Mono',monospace;">{datetime.now().strftime("%d/%m/%Y %H:%M")}</span>
    </div>
    """, unsafe_allow_html=True)

    # Cargar datos
    with st.spinner("Cargando datos..."):
        fx=get_fx(); df_br,e_br=scrape_brasil(); df_ar,e_ar=scrape_argentina()
        df_cl,e_cl=scrape_chile(); df_us,e_us=scrape_usa()

    # Sidebar
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
        st.markdown("**🇧🇷 Estados Brasil**")
        br_cols=[c for c in (df_br.columns if df_br is not None else []) if c not in ["mes","fecha"]]
        br_sel=st.multiselect("",br_cols,default=br_cols[:3])

        st.markdown("**🇦🇷 Provincias Argentina**")
        ar_opts={"Bs. As. blanco":"BA_blanco","Bs. As. color":"BA_color","Santa Fe blanco":"SF_blanco","Entre Ríos blanco":"ER_blanco"}
        ar_sel_lab=st.multiselect("",list(ar_opts.keys()),default=["Bs. As. blanco"])
        ar_sel=[ar_opts[l] for l in ar_sel_lab]

        st.markdown("**🇨🇱 / 🇺🇸**")
        show_cl=st.checkbox("Chile (ODEPA)",value=True)
        show_us=st.checkbox("USA (FRED)",value=True)

        st.markdown("---")
        st.markdown(f"""<div style="font-size:10px;font-family:'JetBrains Mono',monospace;color:#374151;line-height:2;">
        💱 1 USD = CLP${fx['USD_CLP']:,.0f}<br>💱 1 BRL = CLP${fx['BRL_CLP']:.1f}<br>💱 1 ARS = CLP${fx['ARS_CLP']:.4f}
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
        if df_br is not None and br_cols:
            v,m=last_val(df_br,br_cols[0]); kpi(c1,f"🇧🇷 Brasil · {br_cols[0]}","#f97316",(v,"BRL"),m_lbl,vfmt,f"R${v:.4f} · {m}" if v else "Sin datos")
    with c2:
        if df_ar is not None:
            v,m=last_val(df_ar,"BA_blanco"); kpi(c2,"🇦🇷 Argentina · Bs. As. blanco","#60a5fa",(v,"ARS"),m_lbl,vfmt,f"ARS${v:.2f} · {m}" if v else "Sin datos")
    with c3:
        if df_cl is not None:
            v,m=last_val(df_cl,"precio_clp"); kpi(c3,"🇨🇱 Chile · Feria libre","#4ade80",(v,"CLP"),m_lbl,vfmt,f"CLP${v:.0f} · {m}" if v else "Sin datos")
    with c4:
        if df_us is not None:
            v,m=last_val(df_us,"precio_usd"); kpi(c4,"🇺🇸 USA · Grade A Large","#e879f9",(v,"USD"),m_lbl,vfmt,f"USD${v:.4f} · {m}" if v else "Sin datos")

    st.markdown("<br>",unsafe_allow_html=True)

    # Tabs: solo Evolución y Datos
    tab1, tab2 = st.tabs(["📈 Evolución de precios", "📋 Datos"])

    def hover(name):
        return f"<b>{name}</b><br>%{{x|%B %Y}}: <b>${{y:,.{4 if en_usd else 0}f}}</b> {m_lbl}/huevo<extra></extra>"

    with tab1:
        fig=go.Figure()
        if df_br is not None:
            for e in br_sel:
                if e in df_br.columns:
                    y=df_br[e].apply(lambda v:conv(v,"BRL"))
                    fig.add_trace(go.Scatter(x=df_br["fecha"],y=y,name=f"🇧🇷 {e}",
                        line=dict(color=BR_COLORS.get(e,"#f97316"),width=2),mode="lines+markers",
                        marker=dict(size=4),hovertemplate=hover(f"🇧🇷 {e}")))
        if df_ar is not None:
            ar_lbl={"BA_blanco":"Bs. As. blanco","BA_color":"Bs. As. color","SF_blanco":"Santa Fe blanco","ER_blanco":"Entre Ríos blanco"}
            for c in ar_sel:
                if c in df_ar.columns:
                    y=df_ar[c].apply(lambda v:conv(v,"ARS"))
                    fig.add_trace(go.Scatter(x=df_ar["fecha"],y=y,name=f"🇦🇷 {ar_lbl.get(c,c)}",
                        line=dict(color=AR_COLORS.get(c,"#60a5fa"),width=2),mode="lines+markers",
                        marker=dict(size=4),hovertemplate=hover(f"🇦🇷 {ar_lbl.get(c,c)}")))
        if show_cl and df_cl is not None:
            y=df_cl["precio_clp"].apply(lambda v:conv(v,"CLP"))
            fig.add_trace(go.Scatter(x=df_cl["fecha"],y=y,name="🇨🇱 Chile",
                line=dict(color="#4ade80",width=2,dash="dot"),mode="lines+markers",
                marker=dict(size=4),hovertemplate=hover("🇨🇱 Chile")))
        if show_us and df_us is not None:
            y=df_us["precio_usd"].apply(lambda v:conv(v,"USD"))
            fig.add_trace(go.Scatter(x=df_us["fecha"],y=y,name="🇺🇸 USA",
                line=dict(color="#e879f9",width=2,dash="dashdot"),mode="lines+markers",
                marker=dict(size=4),hovertemplate=hover("🇺🇸 USA")))
        fig.update_layout(**LAYOUT,yaxis_title=f"{m_lbl}/huevo",height=440,
            title=dict(text=f"Precio por huevo individual · {m_lbl} · tipo de cambio oficial",font=dict(size=12,color="#4a5568")))
        st.plotly_chart(fig,use_container_width=True)
        st.markdown('<div class="nota">Brasil: CONAB mensual ÷ 12 · Argentina: CAPIA ARS/docena ÷ 12 · Chile: ODEPA CLP/unidad feria libre · USA: FRED USD/docena ÷ 12</div>',unsafe_allow_html=True)

    with tab2:
        d1,d2=st.columns(2)
        with d1:
            st.markdown("**🇧🇷 Brasil (BRL/huevo · CONAB)**")
            if df_br is not None:
                st.dataframe(df_br[[c for c in df_br.columns if c!="fecha"]].set_index("mes").round(4),use_container_width=True)
            st.markdown("**🇨🇱 Chile (CLP/huevo · ODEPA)**")
            if df_cl is not None:
                st.dataframe(df_cl[["mes","precio_clp"]].set_index("mes").round(2),use_container_width=True)
        with d2:
            st.markdown("**🇦🇷 Argentina (ARS/huevo · CAPIA)**")
            if df_ar is not None:
                d=df_ar[["mes","BA_blanco","BA_color","SF_blanco","ER_blanco"]].set_index("mes").round(4)
                d.columns=["BA Blanco","BA Color","SF Blanco","ER Blanco"]
                st.dataframe(d,use_container_width=True)
            st.markdown("**🇺🇸 USA (USD/huevo · FRED/BLS)**")
            if df_us is not None:
                st.dataframe(df_us[["mes","precio_usd"]].set_index("mes").round(4),use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN: IMPORTACIONES
# ══════════════════════════════════════════════════════════════════════════════
def render_importaciones():
    if st.button("← Volver al menú", key="back_imp"):
        st.session_state.seccion = "menu"
        st.rerun()

    st.markdown("""
    <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.8rem;letter-spacing:-1px;margin-bottom:16px;">
        🚢 Importaciones de huevos a Chile
    </div>
    """, unsafe_allow_html=True)

    # Leer el HTML de importaciones
    html_path = os.path.join(os.path.dirname(__file__), "importaciones.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        components.html(html_content, height=860, scrolling=True)
    else:
        st.error("⚠️ No se encontró el archivo `importaciones.html` en la misma carpeta que `app.py`.")
        st.info("Asegúrate de que ambos archivos estén en la misma carpeta.")

# ══════════════════════════════════════════════════════════════════════════════
# ROUTER PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.seccion == "menu":
    render_menu()
elif st.session_state.seccion == "precios":
    render_precios()
elif st.session_state.seccion == "importaciones":
    render_importaciones()
