import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import requests

# --- CONFIGURAZIONE ---
FILE_INVIATI = "inviati.json"
AFFILIATE_TAG = "maladelbrenta-21"
TELEGRAM_TOKEN = "8466443792:AAGw7c2o_yeB5muEOqMYYHgyBiunXAlP-LI"
CHAT_ID = "-1003728999288"
URL_DEALS = "https://www.amazon.it/deals"

def carica_inviati():
    try:
        with open(FILE_INVIATI, "r") as f: return json.load(f)
    except: return []

def salva_inviati(lista):
    with open(FILE_INVIATI, "w") as f: json.dump(lista, f)

def invia_telegram_foto(caption, img_url):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    data = {"chat_id": CHAT_ID, "photo": img_url, "caption": caption, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"❌ Errore invio Telegram: {e}")

def get_dettagli_prodotto(driver, asin):
    """Entra nella pagina prodotto per recuperare Prezzo Reale, Prezzo Vecchio e Coupon"""
    try:
        driver.get(f"https://www.amazon.it/dp/{asin}?tag={AFFILIATE_TAG}")
        time.sleep(4) # Un po' di attesa per caricare i prezzi dinamici
        
        # Recupero Prezzo Attuale
        try:
            p_whole = driver.find_element(By.CSS_SELECTOR, "span.a-price-whole").text.strip()
            p_frac = driver.find_element(By.CSS_SELECTOR, "span.a-price-fraction").text.strip()
            prezzo_att = f"{p_whole},{p_frac}€"
        except:
            prezzo_att = "N/D"

        # Recupero Prezzo Vecchio (Barrato / Consigliato)
        try:
            prezzo_vec = driver.find_element(By.CSS_SELECTOR, "span.a-text-price span.a-offscreen").get_attribute("innerText").strip()
        except:
            prezzo_vec = ""

        # Controllo presenza Coupon
        ha_coupon = False
        try:
            page_content = driver.page_source.lower()
            if "coupon" in page_content or "risparmia" in page_content:
                ha_coupon = True
        except: pass
            
        return prezzo_att, prezzo_vec, ha_coupon
    except:
        return "N/D", "", False

def get_offerte():
    inviati = carica_inviati()
    print(f"🚀 {datetime.now().strftime('%H:%M:%S')} - Scansione griglia offerte...")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(URL_DEALS)
        time.sleep(7)
        driver.execute_script("window.scrollBy(0, 600);")
        time.sleep(2)

        items = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='product-card']")
        print(f"📦 Prodotti rilevati: {len(items)}")

        for item in items:
            asin = item.get_attribute("data-asin")
            if not asin or asin in inviati:
                continue

            # Dati base dalla griglia
            try:
                titolo = item.find_element(By.CSS_SELECTOR, "span.a-truncate-full.a-offscreen").get_attribute("innerText").strip()
                img_url = item.find_element(By.TAG_NAME, "img").get_attribute("src")
                sconto_raw = item.find_element(By.CSS_SELECTOR, "div[role='presentation'] span.a-size-mini").text
                percentuale = int(''.join(filter(str.isdigit, sconto_raw)))
            except:
                continue

            # Recupero Prezzi Reali
            print(f"🔎 Analizzo pagina prodotto per ASIN: {asin}...")
            prezzo_att, prezzo_vec, ha_coupon = get_dettagli_prodotto(driver, asin)

            if prezzo_att == "N/D":
                continue

            # --- LOGICA CORREZIONE PREZZI (Anti-Errore Amazon) ---
            try:
                # Trasformiamo in numeri per il confronto (es: "27,99€" -> 27.99)
                n_att = float(prezzo_att.replace("€", "").replace(",", ".").strip())
                n_vec = float(prezzo_vec.replace("€", "").replace(",", ".").strip()) if prezzo_vec else 0
            except:
                n_att, n_vec = 0, 0

            # Mostra il prezzo barrato solo se è effettivamente PIÙ ALTO di quello attuale
            if n_vec > n_att:
                riga_prezzo = f"💰 {prezzo_att} anziché <s>{prezzo_vec}</s>!"
            else:
                riga_prezzo = f"💰 {prezzo_att}!"

            # Messaggio Finale
            link_aff = f"https://www.amazon.it/dp/{asin}?tag={AFFILIATE_TAG}"
            bomba = "<b>💣💣 BOMBAAA 💣💣</b>\n\n" if percentuale >= 40 else ""
            avviso_coupon = "\n🎟 <b>ATTIVA IL COUPON IN PAGINA!</b>" if ha_coupon else ""

            caption = (
                f"{bomba}🛒 {titolo}\n\n"
                f"{riga_prezzo}{avviso_coupon}\n\n"
                f"👉🏻 <a href='{link_aff}'>Apri su Amazon</a>\n\n"
                f"🔎 <a href='https://m.media-amazon.com/images/G/29/ACS/Made_in_Italy/New_Lego_Page/Guida_su_come_creare_dei_Coupon.pdf'>Come si usa un coupon</a>"
            )

            invia_telegram_foto(caption, img_url)
            inviati.append(asin)
            salva_inviati(inviati)
            
            print(f"✅ INVIATO: {asin} ({prezzo_att})")
            break # Ne invia uno per ciclo

    except Exception as e:
        print(f"❌ Errore: {e}")
    finally:
        driver.quit()

# --- LOOP ---
if __name__ == "__main__":
    while True:
        get_offerte()
        # Domani ricordati di rimettere 3600 (1 ora) al posto di 10
        print("⏱ Attesa 1 ora..")
        time.sleep(3600) # attesa di un ora 