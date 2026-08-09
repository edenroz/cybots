import json
import logging
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ============================================================
# CONFIGURAZIONE ED AMBIENTE
# ============================================================
# Configurazione dei filtri per permettere finzione RPG / Cyberpunk
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

load_dotenv()

FLARUM_URL = os.environ.get("FLARUM_URL", "").rstrip("/")
BOT_PASSWORD = os.getenv("FLARUM_BOT_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

CONFIG_FILE = Path("config.json")
BOTS_FILE = Path("bots.json")
PLAYERS_FILE = Path("players.json")
EVENTS_FILE = Path("events.json")

DATA_DIR = Path("data")
MEMORY_FILE = DATA_DIR / "memory.json"

genai.configure(api_key=GEMINI_API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ============================================================
# GESTIONE JSON & FILE
# ============================================================

def load_json(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_config():
    defaults = {
        "posts_per_run": 1,
        "mode": "auto",
        "new_thread_probability": 0.25,
        "max_discussions_to_consider": 10,
        "max_posts_per_discussion": 15,
        "minimum_relevance": 0.4,
        "avoid_same_bot_same_discussion_hours": 3,
        "player_reply_bonus": 0.25,
        "bot_chain_penalty": 0.3,
        "temperature": 0.9,
        "max_post_words": 120,
        "tag_id": "1"
    }
    cfg = load_json(CONFIG_FILE, {})
    defaults.update(cfg)
    return defaults

def get_bots():
    return load_json(BOTS_FILE, [])

def get_players():
    return load_json(PLAYERS_FILE, [])

def get_events():
    return load_json(EVENTS_FILE, [])

def get_memory():
    return load_json(MEMORY_FILE, {"posts": [], "relationships": {}, "last_run": 0})

# ============================================================
# FLARUM API & AUTHENTICATION
# ============================================================

def get_bot_session(username):
    """
    Effettua il login API per uno specifico bot usando la password condivisa.
    Restituisce una sessione autenticata.
    """
    session = requests.Session()
    url = f"{FLARUM_URL}/api/token"
    
    try:
        response = session.post(
            url,
            json={"identification": username, "password": BOT_PASSWORD},
            timeout=15
        )
        if response.status_code != 200:
            logging.error(f"Login fallito per {username}: HTTP {response.status_code}")
            return None
            
        data = response.json()
        token = data.get("token")
        if not token:
            logging.error(f"Token non ricevuto per il bot {username}")
            return None

        session.headers.update({
            "Authorization": f"Token {token}",
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json"
        })
        return session
    except Exception as e:
        logging.error(f"Errore connessione durante login di {username}: {e}")
        return None

def flarum_get(session, endpoint, params=None):
    response = session.get(FLARUM_URL + endpoint, params=params, timeout=30)
    response.raise_for_status()
    return response.json()

def flarum_post(session, endpoint, payload):
    response = session.post(FLARUM_URL + endpoint, json=payload, timeout=30)
    if not response.ok:
        logging.error(f"Flarum API Error {response.status_code}: {response.text}")
    response.raise_for_status()
    return response.json()

# ============================================================
# PARSING DEL FORUM & UTENTI
# ============================================================

def fetch_forum_context(session, max_discussions=10, posts_limit=15):
    """
    Estrae il contesto direttamente dal forum: thread recenti, autori e post.
    """
    data = flarum_get(session, "/api/discussions", {
        "page[limit]": max_discussions,
        "sort": "-lastPostedAt",
        "include": "user,lastPostedUser,tags"
    })
    
    discussions = data.get("data", [])
    included = {f"{item['type']}:{item['id']}": item for item in data.get("included", [])}
    
    user_map = {}
    for key, item in included.items():
        if item["type"] == "users":
            user_map[item["id"]] = item.get("attributes", {}).get("username")
            
    return discussions, user_map

def get_discussion_posts_hydrated(session, discussion_id, limit=15):
    """
    Recupera i post di una discussione inclusi i dettagli degli autori.
    """
    result = flarum_get(session, "/api/posts", {
        "filter[discussion]": discussion_id,
        "page[limit]": limit,
        "sort": "-createdAt",
        "include": "user"
    })
    
    posts = result.get("data", [])
    posts.reverse()  # Ordine cronologico
    
    included_users = {
        item["id"]: item.get("attributes", {}).get("username")
        for item in result.get("included", [])
        if item["type"] == "users"
    }
    
    hydrated_posts = []
    for p in posts:
        author_id = p.get("relationships", {}).get("user", {}).get("data", {}).get("id")
        author_name = included_users.get(author_id, "Anonimo_Nethead")

        attributes = p.get("attributes", {}) or {}
        content = (
            attributes.get("content")
            or attributes.get("contentHtml")
            or p.get("content")
            or ""
        )
        if isinstance(content, str):
            content = content.strip()
        else:
            content = str(content or "").strip()

        created_at = attributes.get("createdAt", "")

        hydrated_posts.append({
            "id": p["id"],
            "author_id": author_id,
            "author_username": author_name,
            "content": content,
            "created_at": created_at
        })

    return hydrated_posts

def classify_users(players, bots):
    player_names = {p["username"]: p for p in players}
    bot_names = {b["username"]: b for b in bots}
    return player_names, bot_names

# ============================================================
# INTELLIGENZA ARTIFICIALE (LLM)
# ============================================================

def ask_llm(system, prompt, temperature=0.9, max_tokens=300):
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system
    )
    generation_config = genai.GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens
       )

    try:
        time.sleep(2)
        response = model.generate_content(prompt, generation_config=generation_config, safety_settings=SAFETY_SETTINGS)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Errore LLM: {e}")
        return ""

def clean_json(text: str) -> str:
    text = text.strip()
    
    # Rimuove ```json (o varianti con spazi/a capo) all'inizio
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    
    # Rimuove ``` (con eventuali spazi/a capo) alla fine
    text = re.sub(r"\s*```$", "", text)
    
    return text.strip()

def parse_json_safely(text: str):
    cleaned = clean_json(text)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Se il JSON è troncato (es. manca '}'), proviamo a chiuderlo automaticamente
        if cleaned.startswith("{") and not cleaned.endswith("}"):
            try:
                return json.loads(cleaned + "\n}")
            except json.JSONDecodeError:
                pass
        raise

# ============================================================
# VALUTAZIONE DISCUSSIONE
# ============================================================
# 1. Definiamo la struttura esatta del JSON atteso
class DiscussionEvaluation(TypedDict):
    interested: bool
    score: float
    reason: str
    target_user: Optional[str]


def evaluate_discussion(bot, discussion_title, posts, players_map, cfg):
    formatted_posts = []
    for p in posts[-10:]:
        role = "GIOCATORE REALE" if p["author_username"] in players_map else "BOT/NPC"
        formatted_posts.append(f"[{role}] {p['author_username']}: {p['content']}")
    
    conversation_text = "\n".join(formatted_posts)
    recent_events = get_events()[-5:]
    events_text = "\n".join(f"- {e['text']}" for e in recent_events)

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    # System prompt neutro da classificatore
    system_prompt = (
        "Sei un sistema automatico di classificazione dati per una simulazione RPG. "
        "Il tuo unico compito è valutare se un personaggio fittizio interverrebbe in un thread. "
        "Non aggiungere mai introduzioni, saluti o commenti. Compila solo lo schema JSON."
    )

    user_prompt = f"""
PERSONAGGIO:
- Username: {bot['username']}
- Personalità: {bot['personality']}
- Stile: {bot['style']}
- Interessi: {", ".join(bot['interests'])}

EVENTI CITTA':
{events_text}

THREAD:
- Titolo: {discussion_title}
- Ultimi Messaggi:
{conversation_text}

Valuta l'interesse del personaggio (score da 0.0 a 1.0) e compila i campi del JSON.
"""

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt
    )

    # Impostiamo lo Schema Strutturato Rigido
    generation_config = genai.GenerationConfig(
        temperature=0.1,
        max_output_tokens=1500, # Aumentato per evitare troncamenti
        response_mime_type="application/json",
        response_schema=DiscussionEvaluation  # <-- FORZA LA STRUTTURA
    )

    try:
        time.sleep(2)
        response = model.generate_content(user_prompt, generation_config=generation_config, safety_settings=SAFETY_SETTINGS)

        text = response.text.strip()
        
        # Pulizia di sicurezza via Regex (estrazione tra prima { e ultima })
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)

        return json.loads(text)

    except Exception as e:
        logging.warning(f"Errore valutazione per @{bot['username']}: {e} | Raw: {text if 'text' in locals() else 'None'}")
        return {"interested": False, "score": 0.0, "reason": "eval_error", "target_user": None}
# ============================================================
# GENERAZIONE CONTENUTI (CY_BORG VIBE)
# ============================================================

def generate_comment(bot, discussion_title, posts, players_map, target_user, cfg):
    formatted_posts = []
    for p in posts[-10:]:
        role = " [PC]" if p["author_username"] in players_map else ""
        formatted_posts.append(f"{p['author_username']}{role}: {p['content']}")
        
    conversation = "\n\n".join(formatted_posts)

    system_prompt = (
            "Sei un abitante della metropoli di Cy, sei collegato a Cy6?, la BBS principale della NET (nel gioco di ruolo CY_BORG).\n\n"
            "REGOLE TASSATIVE DI COMPORTAMENTO:\n"
            "1. NON sei un assistente IA, non sei un chatbot, non dai consigli utili e non sei gentile.\n"
            "2. SEGUI RIGOROSAMENTE la personalità, lo stile e le patologie del tuo personaggio forniti nel prompt.\n"
            "3. Parli in italiano di strada/cyberpunk. Usa slang tecnologico, acronimi, abbreviazioni, "
            "o formattazione irregolare (glitch, maiuscole, punteggiatura spezzata) se lo stile del tuo personaggio lo richiede. I veri utenti dei forum non scrivono quasi mai temi lunghi.\n"
            "4. Rispondi come un reale utente di un forum: proponi le tue teorie, insulta, shitposta, fai domande, "
            "vendi roba, o reagisci in base alla tua fazione/agenda.\n"
            "5. La moneta di CY è chiamata ¤, in slang di strada si dice grana.\n"
            "6. SE VUOI TAGGARE QUALCUNO: Scrivi SOLO @username in testo semplice (es. @fixerjunior_6159). VIETATISSIMO usare tag HTML come <a href=> o simili.\n"
            "7. Usa il modo di fare, lo slang ed i toni di board come reddit o 4chan.\n"
            "8. Non fare MAI riferimento a date specifiche. Puoi parlare di 'ieri', 'prima', 'stanotte', 'qualche giorno fa', 'tempo fa' ecc. quando è naturale\n"
            "9. Sei una PERSONA VERA che usa un forum.\n. Non devi essere utile a tutti i costi. Un vero utente può:\n"
                "- non rispondere alla domanda;\n"
                "- fraintendere;\n"
                "- dire una stronzata;\n"
                "- rispondere con una battuta;\n"
                "- insultare;\n"
                "- cambiare argomento;\n"
                "- rispondere 'boh';\n"
                "- fare una domanda invece di dare una risposta;\n"
                "- ignorare completamente il punto principale;\n"
                "- rispondere con una sola parola;\n"
                "- raccontare un'esperienza personale.\n"
            "10. NON cercare di aiutare il giocatore. Se puoi dare informazioni, fallo solo perché il TUO PERSONAGGIO avrebbe un motivo per farlo."
                "Potresti anche mentire, esagerare o avere informazioni sbagliate.\n Non sei onnisciente. Conosci soltanto ciò che il tuo personaggio"
                 " potrebbe realisticamente conoscere in CY_BORG vivendo a Cy."
            "11. NON spiegare la lore al lettore. Cy, le corporazioni, le gang, la NET e gli eventi del mondo fanno parte della vita quotidiana del personaggio."
                "Non introdurli come se stessi scrivendo una wiki o spiegando il gioco a qualcuno.\n"
        )

    user_prompt = f"""
TU SEI: @{bot['username']}
PERSONALITA': {bot['personality']}
STILE DI SCRITTURA: {bot['style']}
INTERESSI: {", ".join(bot['interests'])}
QUIRKS: {", ".join(bot.get('quirks', []))}

THREAD: {discussion_title}

CONVERSAZIONE DALLA RETE:
{conversation}

REGOLE DI GENERAZIONE:
1. Rispondi alla discussione in modo naturale e spontaneo.
2. Se vuoi menzionare qualcuno usa la sintassi @Username (specialmente se rispondi a un utente reale [PC]).
3. Puoi contraddire, esprimere tue opnioni, fare teorie del complotto sulle Corporazioni, vendere dati falsi, fare battute macabre o provocare.
4. Non fare riassunti di quanto detto dagli altri.
5. Mantieni il messaggio incisivo. Massimo {cfg['max_post_words']} parole.
6. SCRIVI IN ITALIANO.

Rispondi SOLO col testo del messaggio da pubblicare sulla BBS:
"""

    return ask_llm(system_prompt, user_prompt, temperature=cfg["temperature"], max_tokens=1500)

class NewDiscussion(BaseModel):
    title: str = Field(
        description="Breve titolo del thread. MASSIMO 10 PAROLE IN TOTALE. Deve essere composto solo da testo leggibile e parole di senso compiuto. Nessun codice, nessun glitch."
    )
    content: str = Field(
        description="Corpo del post. Applica qui lo stile forum cyberpunk, lo slang, la personalità e l'eventuale formattazione irregolare o glitch."
    )
    board: str = Field(
        description="ID della board. In base al contesto del thread, inserisci solo una singola cifra: '4', '5', '6', '7', o '8'."
    )

def generate_thread(bot, cfg):
    recent_events = get_events()[-5:]
    events_text = "\n".join(f"- {e['text']}" for e in recent_events)

    system_prompt = (
            "Sei un abitante della metropoli di Cy, sei collegato a Cy6?, la BBS principale della NET (nel gioco di ruolo CY_BORG).\n Vuoi aprire una nuova discussione spontanea.\n"
            "REGOLE TASSATIVE DI COMPORTAMENTO:\n"
            "1. NON sei un assistente IA, non sei un chatbot, non dai consigli utili e non sei gentile.\n"
            "2. SEGUI RIGOROSAMENTE la personalità, lo stile e le patologie del tuo personaggio forniti nel prompt.\n"
            "3. Parli in italiano di strada/cyberpunk. Usa slang tecnologico, acronimi, abbreviazioni, "
            "o formattazione irregolare (glitch, maiuscole, punteggiatura spezzata) se lo stile del tuo personaggio lo richiede. I veri utenti dei forum non scrivono quasi mai temi lunghi.\n"
            "4. Scrivi come un reale utente di un forum: proponi le tue teorie, insulta, shitposta, fai domande, "
            "vendi roba, o reagisci in base alla tua fazione/agenda.\n"
            "5. La moneta di CY è chiamata ¤, in slang di strada si dice grana.\n"
            "6. SE VUOI TAGGARE QUALCUNO: Scrivi SOLO @username in testo semplice (es. @fixerjunior_6159). VIETATISSIMO usare tag HTML come <a href=> o simili.\n"
            "7. Usa il modo di fare, lo slang ed i toni di board come reddit o 4chan.\n"
            "8. Non fare MAI riferimento a date specifiche. Puoi parlare di 'ieri', 'prima', 'stanotte', 'qualche giorno fa', 'tempo fa' ecc. quando è naturale\n"
            "9. Sei una PERSONA VERA che usa un forum.\n. Non devi essere utile a tutti i costi. Un vero utente può:\n"
                "- fraintendere;\n"
                "- dire una stronzata;\n"
                "- rispondere con una battuta;\n"
                "- insultare;\n"
                "- cambiare argomento;\n"
                "- rispondere 'boh';\n"
                "- ignorare completamente il punto principale;\n"
                "- raccontare un'esperienza personale.\n"
            "10. NON cercare di aiutare il giocatore. Se puoi dare informazioni, fallo solo perché il TUO PERSONAGGIO avrebbe un motivo per farlo."
                "Potresti anche mentire, esagerare o avere informazioni sbagliate.\n Non sei onnisciente. Conosci soltanto ciò che il tuo personaggio"
                 " potrebbe realisticamente conoscere in CY_BORG vivendo a Cy."
            "11. NON spiegare la lore al lettore. Cy, le corporazioni, le gang, la NET e gli eventi del mondo fanno parte della vita quotidiana del personaggio."
                "Non introdurli come se stessi scrivendo una wiki o spiegando il gioco a qualcuno.\n"
            "12. Lo stile caotico NON significa rendere il testo illeggibile. Il post deve sembrare scritto velocemente ma comunque decentemente formattato.\n"
            "13. REGOLA ANTI-SPAM (TASSATIVA):\n"
                "   - NO HASHTAG MULTIPLI (al massimo UNO solo alla fine del post, ZERO nel titolo).\n"
                "   - VIETATO elencare lettere dell'alfabeto, sequenze di numeri (12345...) o simboli di fila.\n"
                "   - VIETATO scrivere titoli piu lunghi di 10-12 parole.\n"

                f"""

Gli ID delle board disponibili sono:
- 4: market compro/vendo\n
- 5: AAA cercasi\n
- 6: rumors e teorie dello sprawl\n
- 7: argomenti riguardanti la NET in generale\n
- 8: argomenti religiosi e culti\n

Il Titolo deve essere breve e incisivo, il contenuto deve essere coerente con la personalità del bot e con lo stile CY_BORG. Non aggiungere spiegazioni o commenti extra.\n
"""
        )
    
    user_prompt = f"""
USERNAME: {bot['username']}
PERSONALITA': {bot['personality']}
STILE: {bot['style']}
INTERESSI: {", ".join(bot['interests'])}

RUMORS / EVENTI IN CITTA':
{events_text}

Crea un nuovo thread. Può essere:
- Un allarme paranoico su pattuglie corporate o virus nella rete.
- Un'offerta/richiesta per hardware illegale o stimolanti.
- Una domanda provocatoria alla community.
- Un rumor su una banda di strada o un lavoro andato male.
- Quello che vuoi, purché sia coerente con la personalità del bot e con lo stile CY_BORG.
- Non devi per forza collegare gli eventi rumors recenti al thread, ma puoi farlo se vuoi.
"""
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt
    )

    # Impostiamo lo Schema Strutturato Rigido
    generation_config = genai.GenerationConfig(
        temperature=0.1,
        max_output_tokens=1500, # Aumentato per evitare troncamenti
        response_mime_type="application/json",
        response_schema=NewDiscussion  # <-- FORZA LA STRUTTURA
    )

    try:
        time.sleep(2)
        response = model.generate_content(user_prompt, generation_config=generation_config, safety_settings=SAFETY_SETTINGS)
        print(f"DEBUG: Risposta LLM per @{bot['username']}:\n{response.text}\n")
        text = response.text.strip()
        
        # Pulizia di sicurezza via Regex (estrazione tra prima { e ultima })
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)

        return json.loads(text)

    except Exception as e:
        logging.warning(f"Errore valutazione per @{bot['username']}: {e} | Raw: {text if 'text' in locals() else 'None'}")
        return {"interested": False, "score": 0.0, "reason": "eval_error", "target_user": None}

# ============================================================
# AZIONI BOT
# ============================================================

def run_comment_action(bot, session, players_map, memory, cfg):
    discussions, _ = fetch_forum_context(session, cfg["max_discussions_to_consider"])
    
    candidates = []

    #2 private
    #9 meta
    IGNORED_TAGS = {"2", "9"}
    for d in discussions:
        d_id = str(d["id"])
        title = d.get("attributes", {}).get("title", "")
        
        posts = get_discussion_posts_hydrated(session, d_id, cfg["max_posts_per_discussion"])
        if not posts:
            continue

        discussion_tags = d.get("relationships", {}).get("tags", {}).get("data", [])
    
        # 1. Estrai tutti gli ID dei tag della discussione come set di stringhe
        raw_tags = d.get("relationships", {}).get("tags", {}).get("data", [])
        tag_ids = {str(t["id"]) for t in raw_tags if "id" in t}

        # 2. Controlla se il bot è stato menzionato in almeno uno dei post
        bot_mentioned = any(
            f"@{bot['username'].lower()}"
            in post.get("attributes", {}).get("content", "").lower()
            for post in posts
        )

        if "9" in tag_ids:
            continue

        if "2" in tag_ids and not bot_mentioned:
            continue

        # Evita che il bot spammi nello stesso thread a breve distanza
        bot_last_posts = [p for p in posts if p["author_username"] == bot["username"]]
        if bot_last_posts:
            # Se l'ultimo post nel thread è già di questo bot, salta
            if posts[-1]["author_username"] == bot["username"]:
                continue

        eval_res = evaluate_discussion(bot, title, posts, players_map, cfg)
        
        if eval_res.get("interested", False):
            score = float(eval_res.get("score", 0.0))
            
            # Bonus se c'è un giocatore reale nel thread
            has_player = any(p["author_username"] in players_map for p in posts)
            if has_player:
                score += cfg["player_reply_bonus"]
                
            # Penalità se l'ultimo post è di un altro bot
            if posts[-1]["author_username"] not in players_map:
                score -= cfg["bot_chain_penalty"]

            if score >= cfg["minimum_relevance"]:
                candidates.append({
                    "discussion_id": d_id,
                    "title": title,
                    "posts": posts,
                    "score": score,
                    "target_user": eval_res.get("target_user")
                })

    if not candidates:
        logging.info(f"[{bot['username']}] Nessun thread stimolante trovato.")
        return False

    # Selezione pesata/casuale tra i migliori
    candidates.sort(key=lambda x: x["score"], reverse=True)
    chosen = random.choice(candidates[:2])

    comment_text = generate_comment(
        bot, chosen["title"], chosen["posts"], players_map, chosen["target_user"], cfg
    )

    if not comment_text:
        return False

    logging.info(f"💬 COMMENTO da @{bot['username']} nel thread #{chosen['discussion_id']}: {comment_text}")
    # Pubblica il post via API Flarum
    payload = {
        "data": {
            "type": "posts",
            "attributes": {"content": comment_text},
            "relationships": {
                "discussion": {"data": {"type": "discussions", "id": chosen["discussion_id"]}}
            }
        }
    }

    flarum_post(session, "/api/posts", payload)
    return True

def run_thread_action(bot, session, cfg):
    thread_data = generate_thread(bot, cfg)
    if not thread_data or not all(k in thread_data for k in ("title", "content", "board")):
        return False

# - "4": market compro/vendo
# - "5": AAA cercasi
# - "6": rumors e teorie dello sprawl
# - "7": argomenti riguardanti la NET in generale
# - "8": argomenti religiosi e culti

    logging.info(f"🔥 NUOVO THREAD #{new_id} aperto da @{bot['username']}: {thread_data['title']} in {thread_data['board']}")
    payload = {
        "data": {
            "type": "discussions",
            "attributes": {
                "title": thread_data["title"],
                "content": thread_data["content"]
            },
            "relationships": {
                "tags": {
                    "data": [{"type": "tags", "id": thread_data["board"]}]
                }
            }
        }
    }

    res = flarum_post(session, "/api/discussions", payload)
    new_id = res.get("data", {}).get("id", "??")
    return True

# ============================================================
# MAIN LOOP
# ============================================================

def main():
    cfg = get_config()
    bots = get_bots()
    players = get_players()
    memory = get_memory()

    if not bots:
        logging.error("Nessun bot trovato in bots.json")
        sys.exit(1)

    players_map, bots_map = classify_users(players, bots)
    logging.info(f"Caricati {len(bots)} bot e {len(players)} giocatori.")

    posts_to_make = cfg.get("posts_per_run", 1)

    for _ in range(posts_to_make):
        # Selezione del bot casuale
        bot = random.choice(bots)
        username = bot["username"]

        # Connessione autenticata con le credenziali specifiche del Bot
        session = get_bot_session(username)
        if not session:
            logging.warning(f"Impossibile autenticare il bot @{username}. Salto il turno.")
            continue

        mode = cfg.get("mode", "auto")
        success = False
        mode = "new_thread" # Forzato per test, rimuovere in produzione
        if mode == "new_thread":
            success = run_thread_action(bot, session, cfg)
        elif mode == "comment":
            success = run_comment_action(bot, session, players_map, memory, cfg)
        elif mode == "auto":
            if random.random() < cfg["new_thread_probability"]:
                success = run_thread_action(bot, session, cfg)
            else:
                success = run_comment_action(bot, session, players_map, memory, cfg)
                
            # Fallback: se fallisce il commento (es. nessun thread interessante), prova ad aprire un thread
            if not success:
                success = run_thread_action(bot, session, cfg)

        # Piccola pausa tra le azioni per simulare la latenza di rete
        time.sleep(random.uniform(2, 5))

    memory["last_run"] = time.time()
    save_json(MEMORY_FILE, memory)

if __name__ == "__main__":
    main()