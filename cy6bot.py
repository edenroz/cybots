import json
import logging
import os
import random
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
import google.generativeai as genai

# ============================================================
# CONFIGURAZIONE ED AMBIENTE
# ============================================================

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
        "include": "user,lastPostedUser"
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
        max_output_tokens=max_tokens,
        response_mime_type="application/json"
    )

    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        time.sleep(2)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Errore LLM: {e}")
        return ""

def clean_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text)
        text = re.sub(r"```$", "", text)
    return text.strip()

# ============================================================
# VALUTAZIONE DISCUSSIONE
# ============================================================

def evaluate_discussion(bot, discussion_title, posts, players_map, cfg):
    formatted_posts = []
    for p in posts[-10:]:
        role = "GIOCATORE REALE" if p["author_username"] in players_map else "UTENTE RETE"
        formatted_posts.append(f"[{role}] {p['author_username']}: {p['content']}")
    
    conversation_text = "\n".join(formatted_posts)
    recent_events = get_events()[-5:]
    events_text = "\n".join(f"- {e['text']}" for e in recent_events)

    system_prompt = (
        "Sei il modulo cognitivo di un abitante di Cy (metropoli cyberpunk decadente). "
        "Devi decidere se il personaggio interverrà in una discussione della BBS locale. "
        "Rispondi ESCLUSIVAMENTE in formato JSON valido."
    )

    user_prompt = f"""
PERSONAGGIO:
Handle: {bot['username']}
Personalità: {bot['personality']}
Stile: {bot['style']}
Interessi: {", ".join(bot['interests'])}
Quirks: {", ".join(bot.get('quirks', []))}

EVENTI IN CITTA':
{events_text}

THREAD CORRENTE:
Titolo: {discussion_title}
Messaggi recenti:
{conversation_text}

Valuta se questo personaggio ha un motivo reale per rispondere (es: insultare, difendere la propria fazione, dare info sbagliate, commentare un evento, rispondere a un utente reale).

Restituisci SOLO:
{{
  "interested": true/false,
  "score": 0.0,
  "reason": "motivo sintetico",
  "target_user": "username a cui vuole rispondere o null"
}}
Score da 0.0 a 1.0.
"""

    result = ask_llm(system_prompt, user_prompt, temperature=0.2, max_tokens=200)
    try:
        return json.loads(clean_json(result))
    except Exception:
        return {"interested": False, "score": 0.0, "reason": "parsing_error", "target_user": None}

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
        "Sei un utente cinico, paranoico o degenere di una messageboard cyberpunk clandestina (Net-BBS). "
        "NON sei un'IA, NON sei gentile, NON offri assistenza da chatbot. "
        "Parli in italiano di strada, usando slang tecnologico, acronimi, o formattazione frammentata "
        "tipica di chi si connette con cyberware di seconda mano o sotto l'effetto di stimolanti sintotici."
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
3. Puoi contraddire, fare teorie del complotto sulle Corporazioni, vendere dati falsi, fare battute macabre o provocare.
4. Non fare riassunti di quanto detto dagli altri.
5. Mantieni il messaggio incisivo. Massimo {cfg['max_post_words']} parole.
6. SCRIVI IN ITALIANO.

Rispondi SOLO col testo del messaggio da pubblicare sulla BBS:
"""

    return ask_llm(system_prompt, user_prompt, temperature=cfg["temperature"], max_tokens=250)

def generate_thread(bot, cfg):
    recent_events = get_events()[-5:]
    events_text = "\n".join(f"- {e['text']}" for e in recent_events)

    system_prompt = (
        "Sei un utente di una BBS cyberpunk clandestina in una metropoli decadente. "
        "Vuoi aprire una nuova discussione spontanea. Rispondi SOLO in JSON valido."
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

Restituisci SOLO questo JSON:
{{
  "title": "Titolo d'impatto o grezzo",
  "content": "Corpo del messaggio..."
}}
"""

    result = ask_llm(system_prompt, user_prompt, temperature=cfg["temperature"], max_tokens=300)
    try:
        return json.loads(clean_json(result))
    except Exception:
        return None

# ============================================================
# AZIONI BOT
# ============================================================

def run_comment_action(bot, session, players_map, memory, cfg):
    discussions, _ = fetch_forum_context(session, cfg["max_discussions_to_consider"])
    
    candidates = []
    
    for d in discussions:
        d_id = str(d["id"])
        title = d.get("attributes", {}).get("title", "")
        
        posts = get_discussion_posts_hydrated(session, d_id, cfg["max_posts_per_discussion"])
        if not posts:
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
    logging.info(f"💬 COMMENTO da @{bot['username']} nel thread #{chosen['discussion_id']}")
    return True

def run_thread_action(bot, session, cfg):
    thread_data = generate_thread(bot, cfg)
    if not thread_data:
        return False

    payload = {
        "data": {
            "type": "discussions",
            "attributes": {
                "title": thread_data["title"],
                "content": thread_data["content"]
            },
            "relationships": {
                "tags": {
                    "data": [{"type": "tags", "id": str(cfg["tag_id"])}]
                }
            }
        }
    }

    res = flarum_post(session, "/api/discussions", payload)
    new_id = res.get("data", {}).get("id", "??")
    logging.info(f"🔥 NUOVO THREAD #{new_id} aperto da @{bot['username']}: {thread_data['title']}")
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