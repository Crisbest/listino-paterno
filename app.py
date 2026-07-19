import streamlit as st
import pandas as pd
from fpdf import FPDF
import base64
import os
import re

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Paterno Daniel SRL - Würth Listino", page_icon="wurth-logo-8.png", layout="centered")

# Nomi dei file delle immagini nella tua cartella
bg_filename = "Carpenteria-in-legno-Würth-costruzioni-in-legno.jpg"
logo_filename = "wurth-logo-8.png"

# Funzione sicura per codificare l'immagine in Base64
def get_base64_image(image_path):
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
    except Exception:
        pass
    return None

bg_base64 = get_base64_image(bg_filename)

# 2. PERSONALIZZAZIONE ESTETICA SICURA
if bg_base64:
    css_code = f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(248, 249, 250, 0.90), rgba(248, 249, 250, 0.90)), url("data:image/jpeg;base64,{bg_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    """
else:
    css_code = """
    <style>
    .stApp {
        background-color: #f8f9fa;
    }
    """

css_code += """
    .titolo-principale {
        font-family: 'Arial Black', sans-serif;
        color: #cc0000;
        font-size: 38px;
        font-weight: 900;
        text-align: center;
        margin-top: 10px;
        margin-bottom: 5px;
        letter-spacing: 1px;
    }
    
    .sottotitolo {
        text-align: center;
        color: #222222;
        font-family: Arial, sans-serif;
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 30px;
    }
    
    .stAlert, .stSelectbox, .stTextInput, .stNumberInput {
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 8px;
    }
    
    .stAlert {
        border-left: 5px solid #cc0000;
    }
    </style>
"""
st.markdown(css_code, unsafe_allow_html=True)

# 3. MOSTRA IL LOGO IN ALTO
if os.path.exists(logo_filename):
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image(logo_filename, use_container_width=True)

# 4. TITOLI
st.markdown('<div class="titolo-principale">PATERNO DANIEL SRL</div>', unsafe_allow_html=True)
st.markdown('<div class="sottotitolo">📋 Catalogo Prezzi & Configuratore Ordini Rapido</div>', unsafe_allow_html=True)

# 5. CARICAMENTO DATI (INSERISCI IL TUO LINK CONDIVISO)
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1FA7faje3UDk28aQ3CtQi4k6bkHiYpFg8oyVELK4o48o/export?format=csv"

def pulisci_prezzo(valore):
    """Funzione per pulire stringhe sporche tipo '118.50.00' o con spazi"""
    val_str = str(valore).strip().replace(',', '.')
    # Se ci sono più punti, tiene solo i numeri e il primo punto utile
    parti = val_str.split('.')
    if len(parti) > 2:
        val_str =  parti[0] + '.' + ''.join(parti[1:])
    # Rimuove qualsiasi carattere che non sia numero o punto
    val_str = re.sub(r'[^0-9.]', '', val_str)
    try:
        return float(val_str)
    except ValueError:
        return 0.0

@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
    df['Codice Articolo'] = df['Codice Articolo'].astype(str).str.strip()
    
    # Applica la pulizia di sicurezza su tutta la colonna dei prezzi (CORRETTO CON UNA SOLA 'I')
    df['Prezzo (€)'] = df['Prezzo (€)'].apply(pulisci_prezzo)
    
    if 'Parole Chiave' not in df.columns:
        df['Parole Chiave'] = ""
    else:
        df['Parole Chiave'] = df['Parole Chiave'].fillna("").astype(str)
    return df

try:
    df_prodotti = load_data()
except Exception as e:
    st.error(f"Errore tecnico nel caricamento: {e}")
    st.stop()

if 'carrello' not in st.session_state:
    st.session_state.carrello = []

# 6. INTERFACCIA DI RICERCA
search_query = st.text_input("🔍 Cosa stai cercando? (Inserisci codice, descrizione o nome comune come 'turbovite'):", "").strip().lower()

if search_query:
    risultati = df_prodotti[
        df_prodotti['Codice Articolo'].str.lower().str.contains(search_query) | 
        df_prodotti['Descrizione'].str.lower().str.contains(search_query) |
        df_prodotti['Parole Chiave'].str.lower().str.contains(search_query)
    ]
    
    if not risultati.empty:
        opzioni = risultati.apply(lambda r: f"{r['Codice Articolo']} - {r['Descrizione']}", axis=1).tolist()
        scelta = st.selectbox("Seleziona l'articolo esatto:", opzioni)
        
        codice_sel = scelta.split(" - ")[0]
        prodotto = risultati[risultati['Codice Articolo'] == codice_sel].iloc[0]
        
        st.info(f"**Articolo:** {prodotto['Descrizione']}")
        if prodotto['Parole Chiave']:
            st.caption(f"*(Nomi commerciali associati: {prodotto['Parole Chiave']})*")
            
        st.write(f"**Prezzo di listino:** {prodotto['Prezzo (€)']} € ({prodotto['Unità Prezzo']})")
        
        # Recupera la quantità minima per confezione (usa 1 se vuota)
        q_minima = int(prodotto['Quantità Minima']) if 'Quantità Minima' in prodotto and pd.notna(prodotto['Quantità Minima']) else 1
        
        st.warning(f"📦 **Confezionamento:** Questo articolo viene venduto solo in confezioni da **{q_minima} pezzi**.")
        
        # L'utente seleziona quante confezioni desidera
        confezioni = st.number_input("Inserisci il numero di confezioni da ordinare:", min_value=1, value=1, step=1)
        
        # Calcolo automatico dei pezzi singoli effettivi
        quantita_effettiva = confezioni * q_minima
        st.info(f"🔢 **Quantità totale che verrà ordinata:** {quantita_effettiva} pezzi singoli")
        
        is_per_100 = "100" in str(prodotto['Unità Prezzo'])
        if is_per_100:
            prezzo_totale = (prodotto['Prezzo (€)'] / 100) * quantita_effettiva
            st.success(f"💰 **Prezzo Totale:** {prezzo_totale:.2f} € *(Calcolato su base 100 pz)*")
        else:
            prezzo_totale = prodotto['Prezzo (€)'] * quantita_effettiva
            st.success(f"💰 **Prezzo Totale:** {prezzo_totale:.2f} €")
            
        if st.button("🛒 Aggiungi all'ordine"):
            st.session_state.carrello.append({
                "Codice": prodotto['Codice Articolo'],
                "Descrizione": prodotto['Descrizione'],
                "Prezzo Listino": f"{prodotto['Prezzo (€)']} € / {prodotto['Unità Prezzo']}",
                "Quantità": quantita_effettiva,
                "Totale (€)": round(prezzo_totale, 2)
            })
            st.toast("Aggiunto al riepilogo!")
    else:
        st.warning("Nessun articolo trovato. Modifica il termine di ricerca.")

# 7. CARRELLO E DOWNLOAD PDF
if st.session_state.carrello:
    st.write("---")
    st.subheader("📋 Il tuo ordine attuale")
    
    df_carrello = pd.DataFrame(st.session_state.carrello)
    st.dataframe(df_carrello, use_container_width=True)
    
    totale_ordine = df_carrello["Totale (€)"].sum()
    st.metric(label="Totale complessivo (IVA esc.)", value=f"{totale_ordine:.2f} €")
    
    col_svuota, col_pdf = st.columns([1, 1])
    
    with col_svuota:
        if st.button("❌ Svuota ordine"):
            st.session_state.carrello = []
            st.rerun()
            
    # GENERATORE PDF CORRETTO (SENZA CARATTERI SPECIALI CHE MANDANO IN CRASH)
    def genera_pdf(carrello, totale):
        pdf = FPDF()
        pdf.add_page()
        
        pdf.set_fill_color(204, 0, 0)
        pdf.rect(0, 0, 210, 30, "F")
        
        pdf.set_font("Arial", "B", 16)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(190, 15, "PATERNO DANIEL SRL - MODULO ORDINE", ln=True, align="C")
        pdf.ln(15)
        
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(50, 50, 50)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(30, 8, "Codice", border=1, fill=True)
        pdf.cell(95, 8, "Descrizione", border=1, fill=True)
        pdf.cell(15, 8, "Q.ta", border=1, fill=True, align="C")
        pdf.cell(25, 8, "Listino (cad)", border=1, fill=True, align="R")
        pdf.cell(25, 8, "Totale", border=1, fill=True, ln=True, align="R")
        
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(0, 0, 0)
        for item in carrello:
            # Puliamo la descrizione tagliandola se troppo lunga
            desc = str(item['Descrizione'])[:45]
            # Estraggo solo il numero del prezzo senza il simbolo €
            prezzo_singolo = str(item['Prezzo Listino']).split(" ")[0]
            
            pdf.cell(30, 8, str(item['Codice']), border=1)
            pdf.cell(95, 8, desc, border=1)
            pdf.cell(15, 8, str(item['Quantità']), border=1, align="C")
            pdf.cell(25, 8, f"{prezzo_singolo} EUR", border=1, align="R")
            pdf.cell(25, 8, f"{item['Totale (EUR)'] if 'Totale (EUR)' in item else item['Totale (ê)'] if 'Totale (ê)' in item else item.get('Totale (€)', 0):.2f} EUR", border=1, align="R", ln=True)
            
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(140, 10, "", border=0)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(50, 10, f"Totale: {totale:.2f} EUR", border=1, align="C", ln=True, fill=True)
        
        # Usiamo l'encoding corretto per l'output di testo
        return pdf.output(dest="S").encode('latin1', errors='replace')

    with col_pdf:
        try:
            pdf_bytes = genera_pdf(st.session_state.carrello, totale_ordine)
            st.download_button(
                label="📄 Scarica Ordine in PDF",
                data=pdf_bytes,
                file_name="ordine_paterno_wurth.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error("Errore di compilazione del PDF.")