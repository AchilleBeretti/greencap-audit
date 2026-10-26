import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Configuration générale
st.set_page_config(
    page_title="GreenCap Asset Audit | ESG Capex & Valuation Engine",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injection CSS personnalisé pour un rendu institutionnel / banque d'affaires
st.markdown("""
<style>
    /* Typographie et fond global */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* En-tête principal */
    .brand-title {
        font-size: 24px;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #0F172A;
        margin-bottom: 2px;
    }
    .brand-sub {
        font-size: 13px;
        color: #64748B;
        font-weight: 400;
        margin-bottom: 24px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    
    /* Cartes de métriques personnalisées */
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .metric-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        color: #64748B;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.5px;
    }
    .metric-delta-pos {
        font-size: 12px;
        font-weight: 600;
        color: #059669;
        margin-top: 4px;
    }
    .metric-delta-neg {
        font-size: 12px;
        font-weight: 600;
        color: #DC2626;
        margin-top: 4px;
    }
    
    /* Bannière réglementaire sobre */
    .alert-banner-crit {
        background-color: #FEF2F2;
        border-left: 4px solid #DC2626;
        padding: 14px 18px;
        border-radius: 4px;
        margin-bottom: 20px;
    }
    .alert-banner-warn {
        background-color: #FFFBEB;
        border-left: 4px solid #D97706;
        padding: 14px 18px;
        border-radius: 4px;
        margin-bottom: 20px;
    }
    .alert-banner-ok {
        background-color: #F0FDF4;
        border-left: 4px solid #059669;
        padding: 14px 18px;
        border-radius: 4px;
        margin-bottom: 20px;
    }
    .alert-title {
        font-size: 13px;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 2px;
    }
    .alert-text {
        font-size: 12px;
        color: #475569;
        margin: 0;
    }
</style>
""", unsafe_allow_html=True)

# Barre latérale : Paramètres d'audit
with st.sidebar:
    st.markdown("### PARAMÈTRES DE L'ACTIF")
    
    asset_type = st.selectbox(
        "Typologie d'immeuble",
        ["Résidentiel collectif", "Immeuble de rapport", "Bureaux tertiaires"]
    )
    
    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        surface_m2 = st.number_input("Surface (m²)", min_value=100, max_value=25000, value=1200, step=50)
    with col_sb2:
        loyer_m2_an = st.number_input("Loyer brut (€/m²/an)", min_value=50, max_value=1000, value=240, step=10)
    
    cap_rate_entree = st.slider(
        "Taux de capitalisation initial (%)",
        min_value=3.0, max_value=9.0, value=4.75, step=0.25
    ) / 100.0

    st.markdown("---")
    st.markdown("### BILAN ÉNERGÉTIQUE ACTUEL")
    
    dpe_initial = st.selectbox("Classe DPE actuelle", ["G", "F", "E", "D"], index=0)
    
    st.markdown("---")
    st.markdown("### SCÉNARIO DE VALORISATION (CAPEX)")
    
    dpe_cible = st.selectbox("Classe DPE ciblée post-travaux", ["A", "B", "C"], index=1)
    capex_m2 = st.slider("Budget travaux Capex (€/m²)", min_value=150, max_value=1200, value=450, step=25)
    reval_loyer_pct = st.slider("Revalorisation locative post-travaux (%)", min_value=0.0, max_value=25.0, value=8.0, step=0.5) / 100.0
    compression_cap_rate = st.slider("Compression du taux de sortie (bps)", min_value=0, max_value=100, value=35, step=5) / 10000.0

# Moteur de calcul financier & réglementaire
loyer_initial_total = surface_m2 * loyer_m2_an
capex_total = surface_m2 * capex_m2

# Règles calendaires Loi Climat & Résilience
echeances = {
    "G": {"annee": 2025, "statut": "Interdiction de reconduction immédiate", "severite": "crit"},
    "F": {"annee": 2028, "statut": "Interdiction de location à horizon 2028", "severite": "warn"},
    "E": {"annee": 2034, "statut": "Conformité temporaire (échéance 2034)", "severite": "warn"},
    "D": {"annee": 2050, "statut": "Actif conforme au cadre actuel", "severite": "ok"}
}
reg_info = echeances[dpe_initial]

# Décote passoire thermique (Brown Discount) vs Valeur de base
decotes_dpe = {"G": 0.18, "F": 0.12, "E": 0.05, "D": 0.00}
valeur_venale_theorique = loyer_initial_total / cap_rate_entree
valeur_venale_actuelle = valeur_venale_theorique * (1 - decotes_dpe[dpe_initial])

# Projection post-rénovation
loyer_futur_total = loyer_initial_total * (1 + reval_loyer_pct)
cap_rate_sortie = max(0.025, cap_rate_entree - compression_cap_rate)
valeur_venale_post_travaux = loyer_futur_total / cap_rate_sortie

# Métriques d'arbitrage
gain_valeur_brut = valeur_venale_post_travaux - valeur_venale_actuelle
creation_valeur_nette = gain_valeur_brut - capex_total
multiple_capex = gain_valeur_brut / capex_total if capex_total > 0 else 0
roi_annees = capex_total / (loyer_futur_total - (loyer_initial_total if dpe_initial == "D" else 0)) if capex_total > 0 else 0

# En-tête sobre
st.markdown('<div class="brand-title">OPÉRATEUR D\'ARBITRAGE CAPEX & DÉCOTE ÉNERGÉTIQUE</div>', unsafe_allow_html=True)
st.markdown('<div class="brand-sub">AUDIT INSTITUTIONNEL DE PORTEFEUILLE TERTIAIRE ET RÉSIDENTIEL</div>', unsafe_allow_html=True)

# Bannière de risque réglementaire
banner_class = f"alert-banner-{reg_info['severite']}"
st.markdown(f"""
<div class="{banner_class}">
    <div class="alert-title">Diagnostic réglementaire : Actif classé {dpe_initial}</div>
    <div class="alert-text">{reg_info['statut']} (Cadre d'audit Décret Décence / Loi Climat & Résilience). Risque direct d'obsolescence locative.</div>
</div>
""", unsafe_allow_html=True)

# Grille de 4 indicateurs financiers
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Valeur Vénale Actuelle (Décotée)</div>
        <div class="metric-value">{valeur_venale_actuelle:,.0f} €</div>
        <div class="metric-delta-neg">Décote subie : -{decotes_dpe[dpe_initial]*100:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Investissement Capex Requis</div>
        <div class="metric-value">{capex_total:,.0f} €</div>
        <div class="metric-label" style="margin-top:4px;">Ratio : {capex_m2} €/m²</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Valeur d'Expertise Projetée ({dpe_cible})</div>
        <div class="metric-value">{valeur_venale_post_travaux:,.0f} €</div>
        <div class="metric-delta-pos">Taux de sortie : {cap_rate_sortie*100:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    delta_class = "metric-delta-pos" if creation_valeur_nette > 0 else "metric-delta-neg"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Création de Valeur Nette (NPV)</div>
        <div class="metric-value">{creation_valeur_nette:,.0f} €</div>
        <div class="{delta_class}">Multiplicateur : {multiple_capex:.2f}x Capex</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Corps principal : Graphiques et tableaux d'arbitrage
col_chart1, col_chart2 = st.columns([3, 2])

with col_chart1:
    st.subheader("Décomposition financière de l'arbitrage")
    
    bridge_df = pd.DataFrame({
        "Composante": ["1. Actuel dégradé", "2. Capex injecté", "3. Prime verte nette", "4. Valeur finale"],
        "Montant": [valeur_venale_actuelle, capex_total, max(0, creation_valeur_nette), valeur_venale_post_travaux],
        "Nature": ["Actif existant", "Dépense travaux", "Création nette", "Actif final"]
    })
    
    chart = alt.Chart(bridge_df).mark_bar(cornerRadius=4, size=40).encode(
        x=alt.X("Composante:N", title=None, axis=alt.Axis(labelAngle=0, labelFont='Inter', labelFontSize=11)),
        y=alt.Y("Montant:Q", title="Montant en euros (€)", axis=alt.Axis(format="~s")),
        color=alt.Color("Nature:N", scale=alt.Scale(
            domain=["Actif existant", "Dépense travaux", "Création nette", "Actif final"],
            range=["#94A3B8", "#F59E0B", "#10B981", "#0F172A"]
        ), legend=alt.Legend(title=None, orient="bottom")),
        tooltip=["Composante", alt.Tooltip("Montant:Q", format=",.0f")]
    ).properties(height=320)
    
    st.altair_chart(chart, use_container_width=True)

with col_chart2:
    st.subheader("Synthèse d'expertise & Recommandation")
    
    st.markdown(f"""
    **Analyse du dossier pour le Comité des Engagements :**
    
    * **Surface de plancher :** {surface_m2:,.0f} m²  
    * **Trajectoire environnementale :** Transition du DPE **{dpe_initial}** vers la classe **{dpe_cible}**.
    * **Effort d'investissement :** {capex_total:,.0f} € HT (soit {capex_m2} €/m²).
    * **Gain de survaleur vénale :** +{gain_valeur_brut:,.0f} €.
    """)
    
    if creation_valeur_nette > 0:
        st.success(f"**Avis d'arbitrage : ACCORD CONDITIONNEL (Value-Add)**  \nL'injection de Capex est créatrice de valeur immédiate : chaque euro investi dégage **{multiple_capex:.2f} €** de valeur vénale additionnelle, tout en neutralisant le risque de décote d'obsolescence réglementaire.")
    else:
        st.error(f"**Avis d'arbitrage : ARBITRAGE NÉGATIF / REVENTE EN L'ÉTAT**  \nLe montant des travaux nécessaires excède la revalorisation de marché de l'actif. Recommandation : céder l'actif à un opérateur spécialisé avec décote.")

st.markdown("---")

# Tableau de cash-flows prospectifs sur 10 ans
st.subheader("Projection des flux nets de loyers sur 10 ans (Comparatif Statu Quo vs Travaux)")

annees = [f"Année {i}" for i in range(1, 11)]
interdiction_annee_index = max(1, reg_info["annee"] - 2024)

flux_statu_quo = []
flux_renove = []

for i in range(1, 11):
    # En statu quo, les loyers tombent à zéro à partir de l'année d'interdiction
    if dpe_initial in ["G", "F"] and i >= interdiction_annee_index:
        flux_statu_quo.append(0)
    else:
        flux_statu_quo.append(loyer_initial_total)
    
    # En scénario rénové, loyer valorisé dès l'année 1
    flux_renove.append(loyer_futur_total)

df_cf = pd.DataFrame({
    "Exercice": annees,
    "Flux Statu Quo (€)": flux_statu_quo,
    "Flux Rénové (€)": flux_renove,
    "Écart de trésorerie net (€)": [r - s for r, s in zip(flux_renove, flux_statu_quo)]
})

st.dataframe(
    df_cf.style.format({
        "Flux Statu Quo (€)": "{:,.0f} €",
        "Flux Rénové (€)": "{:,.0f} €",
        "Écart de trésorerie net (€)": "{:,.0f} €"
    }),
    use_container_width=True
)