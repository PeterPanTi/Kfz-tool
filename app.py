import datetime
import mimetypes
import re
import ssl
import smtplib
from typing import List, Optional

import streamlit as st
from email import encoders
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- SEITEN KONFIGURATION ---
st.set_page_config(page_title="Kfz-Datenbermittlung", page_icon="", layout="centered")

# --- CSS FR BESSERE OPTIK ---
st.markdown(
    """
    <style>
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-size: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _get_secret(path: str, key: str) -> Optional[str]:
    try:
        return st.secrets[path][key]
    except Exception:
        return None


EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def _format_date(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    try:
        return str(value)
    except Exception:
        return ""


def send_email_with_attachments(data: dict, files: Optional[List]) -> bool:
    sender_email = _get_secret("email", "sender")
    receiver_email = _get_secret("email", "receiver")
    password = _get_secret("email", "password")
    smtp_server = _get_secret("email", "server")
    port = _get_secret("email", "port")

    if not (sender_email and receiver_email and password and smtp_server and port):
        st.error("E-Mail-Konfiguration fehlt in st.secrets['email']. Bitte konfigurieren.")
        return False

    try:
        port = int(port)
    except Exception:
        st.error("Ungtiger SMTP-Port in den Secrets.")
        return False

    subject = f"Neues Kfz-Angebot: {data.get('nachname','')}, {data.get('vorname','')}".strip(", ")
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    body = (
        "NEUE KUNDENANFRAGE KFZ\n"
        "======================\n\n"
        "KUNDENDATEN:\n"
        "----------------------------\n"
        f"Name: {data.get('vorname','')} {data.get('nachname','')}\n"
        f"Geburtsdatum: {data.get('geb_datum','')}\n"
        f"Anschrift: {data.get('strasse','')}, {data.get('plz','')} {data.get('ort','')}\n"
        f"Email: {data.get('email','')}\n"
        f"Telefon: {data.get('telefon','')}\n\n"
        "FAHRZEUGDATEN:\n"
        "----------------------------\n"
        f"HSN: {data.get('hsn','')}\n"
        f"TSN: {data.get('tsn','')}\n"
        f"Amtl. Kennzeichen: {data.get('kennzeichen','')}\n"
        f"Fahrgestellnummer (FIN): {data.get('fin','')}\n"
        f"Erstzulassung: {data.get('erstzulassung','')}\n"
        f"Halter = VN?: {data.get('halter_ist_vn','')}\n\n"
        "NUTZUNG & TARIFMERKMALE:\n"
        "----------------------------\n"
        f"KM pro Jahr: {data.get('km_jahr','')}\n"
        f"Nutzung: {data.get('nutzung','')}\n"
        f"Stellplatz: {data.get('stellplatz','')}\n"
        f"Finanzierung: {data.get('finanzierung','')}\n"
        f"Wohneigentum: {data.get('wohneigentum','')}\n\n"
        "FAHRER & VORVERSICHERUNG:\n"
        "----------------------------\n"
        f"Fhrerschein seit: {data.get('fuehrerschein_datum','')}\n"
        f"Fahrerkreis: {data.get('fahrerkreis','')}\n"
        f"Geburtsdatum jngster Fahrer: {data.get('juengster_fahrer','')}\n"
        f"Aktuelle SF-Klasse: {data.get('sf_klasse','')}\n"
        f"Vorversicherer: {data.get('vorversicherer','')}\n\n"
        "BEMERKUNGEN:\n"
        f"{data.get('bemerkung','')}\n"
    )

    msg.attach(MIMEText(body, "plain"))

    if files:
        for uploaded_file in files:
            try:
                file_bytes = uploaded_file.getvalue()
                filename = uploaded_file.name or "attachment"
                ctype, encoding = mimetypes.guess_type(filename)
                if ctype is None:
                    part = MIMEApplication(file_bytes, Name=filename)
                else:
                    maintype, subtype = ctype.split("/", 1)
                    if maintype == "text":
                        part = MIMEText(file_bytes.decode("utf-8", errors="ignore"), _subtype=subtype)
                    else:
                        part = MIMEBase(maintype, subtype)
                        part.set_payload(file_bytes)
                        encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=filename)
                msg.attach(part)
            except Exception:
                st.error(f"Fehler beim Anhngen von {getattr(uploaded_file, 'name', 'einer Datei')}.")
                return False

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.send_message(msg)
        return True
    except Exception:
        st.error("Fehler beim Senden der E-Mail. Bitte prfen Sie die SMTP-Konfiguration und versuchen Sie es spter.")
        return False


# --- UI START ---
st.title(" Daten fr Kfz-Versicherung")
st.markdown("Bitte fllen Sie das Formular aus. Am Ende knnen Sie Fotos vom **Fahrzeugschein** oder der **Vorpolice** hochladen.")

with st.form("insurance_form"):
    st.markdown("### 1. Persnliche Daten")
    col1, col2 = st.columns(2)
    vorname = col1.text_input("Vorname")
    nachname = col2.text_input("Nachname")

    geb_datum = st.date_input(
        "Geburtsdatum",
        value=datetime.date(1990, 1, 1),
        min_value=datetime.date(1930, 1, 1),
        max_value=datetime.date(2006, 1, 1),
    )

    col3, col4 = st.columns([3, 1])
    strasse = col3.text_input("Strae & Hausnummer")
    plz = col4.text_input("PLZ")
    ort = st.text_input("Wohnort")

    col5, col6 = st.columns(2)
    email = col5.text_input("E-Mail Adresse")
    telefon = col6.text_input("Handynummer")

    st.markdown("---")
    st.markdown("### 2. Fahrzeugdaten")
    st.info("💡 Tipp: Wenn Sie unten ein Foto vom Fahrzeugschein hochladen, reichen HSN, TSN und Erstzulassung oft aus.")

    f_col1, f_col2 = st.columns(2)
    hsn = f_col1.text_input("HSN (zu 2.1)", placeholder="z.B. 0603")
    tsn = f_col2.text_input("TSN (zu 2.2)", placeholder="z.B. AYC")

    erstzulassung = st.date_input("Erstzulassung (Datum)", value=datetime.date(2015, 1, 1))
    fin = st.text_input("Fahrgestellnummer (E)", help="Wichtig, falls HSN/TSN nicht eindeutig sind")
    kennzeichen = st.text_input("Amtliches Kennzeichen (falls vorhanden)")
    halter_ist_vn = st.selectbox("Ist der Fahrzeughalter auch der Versicherungsnehmer?", ["Ja", "Nein, abweichender Halter"])

    st.markdown("---")
    st.markdown("### 3. Nutzung & Fahrer")

    km_jahr = st.selectbox("Fahrleistung pro Jahr (km)", ["bis 6.000", "9.000", "12.000", "15.000", "20.000", "25.000", "ber 30.000"])
    nutzung = st.selectbox("Nutzung", ["Ausschlielich privat", "Privat und Arbeitsweg", "Gewerblich"])
    stellplatz = st.selectbox("Nhtlicher Abstellplatz", ["Einzelgarage", "Tiefgarage/Sammelgarage", "Carport", "Privatgrundstck", "Strae (öffentlich)"])
    wohneigentum = st.selectbox("Wohneigentum", ["Kein Wohneigentum", "Einfamilienhaus (selbstbewohnt)", "Wohnung (selbstbewohnt)"])
    finanzierung = st.selectbox("Finanzierung", ["Eigenfinanziert / Barkauf", "Kredit", "Leasing"])

    st.markdown("#### Fahrerkreis")
    fahrerkreis = st.selectbox("Wer fhrt das Auto?", ["Nur Versicherungsnehmer", "VN und Partner/in", "VN, Partner und Kinder", "Beliebige Fahrer"])
    juengster_fahrer = st.text_input("Geburtsdatum des jngsten Fahrers (falls abweichend vom VN)", placeholder="TT.MM.JJJJ")
    fuehrerschein_datum = st.date_input("Fhrerscheinerwerb (Datum)", value=datetime.date(2010, 1, 1))

    st.markdown("---")
    st.markdown("### 4. Vorversicherung")
    sf_klasse = st.text_input("Aktuelle SF-Klasse (z.B. SF 10)", help="Oder 'Ersteinstufung' eintragen")
    vorversicherer = st.text_input("Name der aktuellen Versicherung")

    st.markdown("---")
    st.markdown("### 5. Dokumenten-Upload")
    uploaded_files = st.file_uploader(
        "Bitte laden Sie hier Fotos vom Fahrzeugschein (Vorder- & Rckseite) hoch",
        accept_multiple_files=True,
        type=["png", "jpg", "jpeg", "pdf"],
    )

    bemerkung = st.text_area("Sonstige Anmerkungen")

    st.markdown("---")
    st.markdown("### Datenschutz")
    dsgvo = st.checkbox("Ich willige ein, dass meine Daten zur Erstellung eines Versicherungsangebots gespeichert und verarbeitet werden. Ich habe die Datenschutzerklrung gelesen.")

    submit_button = st.form_submit_button("Kostenloses Angebot anfordern")

    if submit_button:
        if not dsgvo:
            st.error("⚠️ Bitte besttigen Sie die Datenschutzbestimmungen, um fortzufahren.")
        elif not vorname or not nachname or not telefon:
            st.error("⚠️ Bitte geben Sie mindestens Vor- und Nachname sowie Telefonnummer an.")
        elif email and not EMAIL_REGEX.match(email):
            st.error("⚠️ Bitte geben Sie eine gltige E-Mail-Adresse an.")
        else:
            form_data = {
                "vorname": vorname,
                "nachname": nachname,
                "geb_datum": _format_date(geb_datum),
                "strasse": strasse,
                "plz": plz,
                "ort": ort,
                "email": email,
                "telefon": telefon,
                "hsn": hsn,
                "tsn": tsn,
                "kennzeichen": kennzeichen,
                "fin": fin,
                "erstzulassung": _format_date(erstzulassung),
                "halter_ist_vn": halter_ist_vn,
                "km_jahr": km_jahr,
                "nutzung": nutzung,
                "stellplatz": stellplatz,
                "wohneigentum": wohneigentum,
                "finanzierung": finanzierung,
                "fahrerkreis": fahrerkreis,
                "juengster_fahrer": juengster_fahrer,
                "fuehrerschein_datum": _format_date(fuehrerschein_datum),
                "sf_klasse": sf_klasse,
                "vorversicherer": vorversicherer,
                "bemerkung": bemerkung,
            }

            with st.spinner("Daten werden sicher bertragen..."):
                if send_email_with_attachments(form_data, uploaded_files):
                    st.success("✅ Vielen Dank! Ihre Daten wurden erfolgreich bermittelt. Wir melden uns in Krze mit einem Angebot.")
                    st.balloons()
