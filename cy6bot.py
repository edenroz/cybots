import json
import logging
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import unescape
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from collections import defaultdict

def load_json(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

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

LORE_FILE = Path("lore.json")

LORE_PROMPT = """
Hai accesso a una raccolta di fatti canonici sul mondo di CY_BORG.

Questi fatti NON sono notizie recenti, NON sono suggerimenti e NON sono materiale da
ripetere automaticamente. Sono conoscenze di base che un abitante di Cy può dare
per scontate.

REGOLE:

La lore fornita è CANONICA.
   Considerala vera all'interno del mondo di gioco.

Usa la lore come conoscenza implicita.
   Non dire mai frasi come:
   - "Secondo la lore..."
   - "Nel database che mi hai fornito..."
   - "So che..."
   - "Il file dice che..."
   
   Il personaggio deve semplicemente parlare come qualcuno che vive in quel mondo.

USA LA LORE SOLO QUANDO È PERTINENTE.
   Se una discussione riguarda gli SSD, puoi conoscere la storia della loro scarsità.
   Se si parla di cyberware, puoi conoscere il suo ruolo nella società.
   Se si parla della NET, puoi conoscere Blackout, Filth, netrunner ecc.

NON FARE INFODUMP.
   Non inserire cinque fatti di lore in una risposta solo perché li conosci.
   Una risposta breve e naturale è preferibile a una spiegazione enciclopedica.

PUOI USARE LA LORE COME BASE PER OPINIONI E BATTUTE.
   Il personaggio può avere opinioni, pregiudizi e convinzioni personali
   basandosi sui fatti canonici.

DISTINGUI FATTI E OPINIONI.
   I fatti presenti nella lore sono canonici.
   Le interpretazioni, opinioni e teorie del personaggio NON diventano automaticamente
   fatti canonici.

NON INVENTARE STORIA CONTRADDITTORIA.
   Se la lore stabilisce un fatto, non negarlo o modificarlo arbitrariamente.
   Puoi però inventare dettagli personali, aneddoti, esperienze e opinioni che non
   contraddicano la lore.

NON È NECESSARIO CONOSCERE TUTTA LA LORE.
   Il personaggio non deve dimostrare di conoscere ogni fatto esistente.
   Usa soltanto le informazioni pertinenti alla conversazione.

LA LORE NON DEVE MODIFICARE LA PERSONALITÀ.
   La stessa informazione può essere interpretata diversamente da personaggi diversi.
   Un corporate fanboy può difendere le megacorp.
   Uno street scum può odiarle.
   Un netrunner può essere paranoico riguardo alla NET.
   Il fatto storico rimane comunque lo stesso.

PARLA COME UN ABITANTE DI CY.
    La conoscenza del mondo deve emergere naturalmente attraverso il linguaggio,
    le opinioni, i riferimenti e le battute del personaggio.

NON CORREGGERE GLI ALTRI BOT AUTOMATICAMENTE.
    Se un altro personaggio dice qualcosa di falso, non devi necessariamente intervenire.
    Puoi ignorarlo, prenderlo in giro, contraddirlo o credergli in base alla tua
    personalità.

EVITA IL LINGUAGGIO ENCICLOPEDICO.
    Preferisci:
        "Gli SSD? Quelli hanno già fatto scoppiare una guerra."
    invece di:
        "La Seconda Guerra Corporativa scoppiò a causa della scarsità globale di SSD."

LA LORE È CONTESTO, NON CONTENUTO OBBLIGATORIO.
    Se nessun elemento della lore è rilevante per la risposta, ignorala completamente.
"""
LORE_PROMPT += "\n".join(f"- {e['text']}" for e in load_json(LORE_FILE, []))

# ============================================================
# GESTIONE JSON & FILE
# ============================================================
def get_flarum_user(session, username):
    result = flarum_get(session, "/api/users", {
        "filter[q]": username,
        "page[limit]": 10
    })

    for user in result.get("data", []):
        attrs = user.get("attributes", {})
        if attrs.get("username", "").lower() == username.lower():
            return user

    return None

def get_bot_history(session, username, limit=30):
    """
    Recupera gli ultimi post scritti dal bot insieme
    alle informazioni del thread/discussione.

    Flarum viene utilizzato come memoria persistente.
    """

    result = flarum_get(
        session,
        "/api/posts",
        {
            "filter[author]": username,
            "page[limit]": limit,
            "sort": "-createdAt",
            "include": "discussion,user"
        }
    )

    posts = result.get("data", [])
    included = result.get("included", [])

    # ==========================================================
    # Indicizza le discussioni incluse nella risposta
    # ==========================================================

    discussions = {}

    for resource in included:
        if resource.get("type") != "discussions":
            continue

        discussion_id = resource.get("id")
        attributes = resource.get("attributes", {}) or {}

        discussions[str(discussion_id)] = {
            "id": discussion_id,
            "title": attributes.get("title", ""),
            "created_at": attributes.get("createdAt", ""),
            "slug": attributes.get("slug", "")
        }

    # ==========================================================
    # Costruisci la memoria
    # ==========================================================

    history = []

    for p in reversed(posts):

        attributes = p.get("attributes", {}) or {}

        # ------------------------------------------------------
        # ID discussione
        # ------------------------------------------------------

        discussion_id = (
            p.get("relationships", {})
             .get("discussion", {})
             .get("data", {})
             .get("id")
        )

        # ------------------------------------------------------
        # Recupera thread
        # ------------------------------------------------------

        discussion = discussions.get(str(discussion_id), {})

        # ------------------------------------------------------
        # Contenuto post
        # ------------------------------------------------------

        content = attributes.get("content")

        if not content:
            content = attributes.get("contentHtml", "")

        # ------------------------------------------------------
        # Salva tutto
        # ------------------------------------------------------

        history.append({
            "id": p.get("id"),

            "content": content,

            "created_at": attributes.get(
                "createdAt",
                ""
            ),

            "discussion_id": discussion_id,

            "thread": {
                "id": discussion.get("id"),
                "title": discussion.get("title", ""),
                "created_at": discussion.get("created_at", ""),
                "slug": discussion.get("slug", "")
            }
        })

    return history

def extract_mentions(content):
    """
    Estrae gli username preceduti da @ dal contenuto del post.
    """

    if not content:
        return []

    return re.findall(r'@([a-zA-Z0-9_-]+)', content)

import re


def extract_mentions(content):
    """
    Estrae gli username preceduti da @ dal contenuto Flarum.
    """
    if not content:
        return []

    return re.findall(r'@([a-zA-Z0-9_-]+)', content)

def get_user_interactions(session, username_a, username_b, limit=20):
    """
    Cerca le conversazioni in cui username_a e username_b
    hanno interagito tramite mention.

    Una interazione viene trovata quando:
      - A menziona B
      - oppure B menziona A

    I post devono appartenere alla stessa discussion.
    """

    history_a = get_bot_history(session, username_a, 50)
    history_b = get_bot_history(session, username_b, 50)

    username_a = username_a.lower()
    username_b = username_b.lower()

    interactions = []

    # ---------------------------------------------------------
    # A -> B
    # ---------------------------------------------------------

    for post_a in history_a:

        content_a = post_a.get("content", "")
        mentions_a = extract_mentions(content_a)

        if username_b not in [m.lower() for m in mentions_a]:
            continue

        discussion_id = str(post_a.get("discussion_id"))

        interactions.append({
            "discussion_id": discussion_id,
            "thread": post_a.get("thread"),
            "from": username_a,
            "to": username_b,
            "posts": [
                post_a
            ]
        })

    # ---------------------------------------------------------
    # B -> A
    # ---------------------------------------------------------

    for post_b in history_b:

        content_b = post_b.get("content", "")
        mentions_b = extract_mentions(content_b)

        if username_a not in [m.lower() for m in mentions_b]:
            continue

        discussion_id = str(post_b.get("discussion_id"))

        interactions.append({
            "discussion_id": discussion_id,
            "thread": post_b.get("thread"),
            "from": username_b,
            "to": username_a,
            "posts": [
                post_b
            ]
        })

    # ---------------------------------------------------------
    # Ordina per data più recente
    # ---------------------------------------------------------
    for interaction in interactions:
        interaction["posts"].sort(
            key=lambda post: post.get("created_at", ""),
            reverse=True
        )

    # ---------------------------------------------------------
    # Limita risultati
    # ---------------------------------------------------------

    return interactions[:limit]

def normalize_mentions(text: str) -> str:
    """
    Normalizza l'inizio delle frasi dopo una mention.

    Esempio:
        @burning_silver_2020 La violenza...
    diventa:
        @burning_silver_2020 la violenza...

    Non modifica le maiuscole nel resto del testo.
    """

    if not text:
        return text

    # Mention all'inizio del post
    match = re.match(
        r"^(@[A-Za-z0-9_]+)(\s+)([A-ZÀ-ÖØ-Þ])",
        text
    )

    if match:
        mention = match.group(1)
        spacing = match.group(2)
        first_char = match.group(3)

        text = (
            mention
            + spacing
            + first_char.lower()
            + text[match.end():]
        )

    return text

from datetime import datetime

def format_recent_posts(posts, discussion_title=None):
    if not posts:
        return "Nessun post recente."

    formatted = []

    for post in posts:
        content = post.get("content", "")

        # Rimuove semplicemente i tag HTML più comuni di Flarum
        content = content.replace("<p>", "").replace("</p>", "")
        content = content.strip()

        created_at = post.get("created_at", "")
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                date_str = dt.strftime("%d/%m/%Y %H:%M")
            except ValueError:
                date_str = created_at
        else:
            date_str = "data sconosciuta"

        thread = post.get("thread") or {}
        title = thread.get("title", "Discussione sconosciuta")
        if (title == discussion_title):
            continue  # Salta i post della discussione corrente

        formatted.append(
            f'[{date_str}] Discussione: "{title}"\n'
            f'- {content}'
        )

    return "\n\n".join(formatted)

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
    cfg = load_json(CONFIG_FILE, {})
    return load_json(EVENTS_FILE, [])[-cfg["event_count"]:]

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
    recent_events = get_events()
    events_text = "\n".join(f"- {e['text']}" for e in recent_events)

    model_name = os.getenv("GEMINI_MODEL_LITE", "gemini-3.5-flash-lite")
    
    # System prompt neutro da classificatore
    system_prompt = (
"""
Sei un sistema automatico di valutazione per una simulazione RPG.

Il tuo compito è decidere se il personaggio dovrebbe intervenire
nella discussione e, SOLO SE appropriato, identificare un utente
specifico a cui rivolgersi.

Devi compilare esclusivamente il JSON richiesto.
Non aggiungere testo fuori dal JSON.

REGOLE IMPORTANTI PER target_user:

- target_user DEVE essere null nella maggior parte dei casi.
- NON valorizzare target_user semplicemente perché nel thread
  compare un giocatore reale.
- NON valorizzare target_user se il personaggio vuole semplicemente
  partecipare alla discussione in modo generico.
- Valorizza target_user SOLO quando esiste una chiara intenzione
  del personaggio di rivolgersi direttamente a quella persona.
- target_user può essere valorizzato solo con lo username ESATTO
  di un utente che compare realmente nei messaggi del thread.
- Non inventare mai username.
- Se il personaggio è interessato ma non ha un interlocutore preciso,
  usa target_user = null.
- Se ci sono più utenti possibili ma nessuno è chiaramente il
  destinatario, usa target_user = null.
- Se il personaggio vuole rispondere a una domanda, provocazione,
  accusa, richiesta o messaggio specifico di un utente, allora
  valorizza target_user con quell'username.
- La presenza di una risposta nel thread NON implica automaticamente
  che target_user debba essere valorizzato.
- target_user rappresenta un INTENTO DI RISPOSTA DIRETTA,
  non semplicemente la persona più rilevante del thread.

REGOLE PER interested:

- interested = true solo se il personaggio avrebbe una ragione
  concreta per intervenire.
- Un interesse generico o marginale dovrebbe produrre uno score basso.
- Se non c'è una motivazione plausibile per intervenire,
  interested = false.
- Non aumentare lo score solo perché nel thread c'è un giocatore reale.

REGOLE PER reason:

- Spiega brevemente perché il personaggio interverrebbe o non
  interverrebbe.
- Se target_user è valorizzato, spiega anche perché vuole rivolgersi
  proprio a quella persona.

DECISIONE SU target_user:

Chiediti esplicitamente:

"Se questo bot dovesse scrivere il prossimo messaggio, starebbe
rispondendo DIRETTAMENTE a una persona specifica?"

Se NO -> target_user = null
Se SÌ -> target_user = username esatto della persona

Ricorda:
interessato a una discussione != interessato a rispondere a qualcuno.
"""
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

def generate_comment(session, bot, discussion_title, posts, players_map, target_user, cfg):
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
            "Lo slang comune della strada include choom e choomba: sono appellativi informali usati per rivolgersi ad altre persone, amici, conoscenti o anche sconosciuti, a seconda del tono."
            "Usali occasionalmente e in modo naturale. Il loro uso dipende dalla personalità e dal rapporto tra i personaggi. Non abusarne."
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
            "10. NON cercare di aiutare il giocatore. Se puoi dare informazioni, fallo solo "
                    "perché il TUO PERSONAGGIO avrebbe un motivo per farlo. Puoi mentire, esagerare "
                    "o sbagliare, ma non inventare fatti che contraddicono la conoscenza canonica "
                    "del mondo.\n"
            "11. NON spiegare la lore al lettore. Cy, le corporazioni, le gang, la NET e gli eventi del mondo fanno parte della vita quotidiana del personaggio."
                "Non introdurli come se stessi scrivendo una wiki o spiegando il gioco a qualcuno.\n"
            "CONOSCENZA CANONICA DEL MONDO:\n"
            f"""{LORE_PROMPT}\n"""
        )

    recent_posts_text = format_recent_posts(get_bot_history(session, bot["username"], 10), discussion_title)

    user_prompt = f"""
TU SEI: @{bot['username']}
PERSONALITA': {bot['personality']}
STILE DI SCRITTURA: {bot['style']}
INTERESSI: {", ".join(bot['interests'])}
QUIRKS: {", ".join(bot.get('quirks', []))}

THREAD: {discussion_title}

CONVERSAZIONE DALLA NET:
{conversation}

MEMORIA PERSONALE RECENTE:\n
{recent_posts_text}\n
Questi sono alcuni dei tuoi ultimi post sul forum.
Usali per mantenere continuità nel modo di parlare, nelle opinioni,
nelle esperienze e negli argomenti già affrontati.
Non copiarli e non citarli come memoria.
Possono contenere opinioni, battute o informazioni sbagliate del personaggio.\n
"""

    if random.random() < cfg["event_relevance"]:
        recent_events = get_events()
        events_text = "\n".join(f"- {e['text']}" for e in recent_events)
        user_prompt += f"""\n\n
EVENTI RECENTI IN CITTA': Queste sono cose successe recentemente a Cy e che stanno circolando
tra la gente, sulla NET, per strada, nei locali o nei canali pubblici.
NON devi necessariamente parlarne. Considerale semplicemente come
parte del mondo attuale del personaggio.
{events_text}.\n
Puoi:
- reagire a uno degli eventi se è pertinente alla discussione;
- collegarlo alla tua esperienza, fazione o interessi;
- usarlo come battuta, paranoia, teoria o provocazione;
- comportarti come se ne avessi sentito parlare;
- ignorarlo completamente se il tuo personaggio non avrebbe motivo di interessarsene.
NON elencare gli eventi.
NON dire "secondo gli eventi recenti".
NON spiegare che stai usando questo contesto.\n"""

    if (target_user):
        interactions = get_user_interactions(session, bot["username"], target_user, limit=15)
        strInteractions = format_interactions_for_llm(interactions)
        user_prompt += "\n\n" + strInteractions + "\n\n"

    user_prompt += f"""
REGOLE DI GENERAZIONE:
1. Rispondi alla discussione in modo naturale e spontaneo.
2. Se vuoi menzionare qualcuno usa la sintassi @Username (specialmente se rispondi a un utente reale [PC]).
3. Puoi contraddire, esprimere tue opnioni, fare teorie del complotto sulle Corporazioni, vendere dati falsi, fare battute macabre o provocare.
4. Non fare riassunti di quanto detto dagli altri.
5. Mantieni il messaggio incisivo e breve. Di norma resta entro {cfg['max_post_words']} parole. Non troncare mai una frase: se hai poco spazio, termina prima.
6. SCRIVI IN ITALIANO.

Rispondi SOLO col testo del messaggio da pubblicare sulla BBS chiamata Cy6:
"""
    return ask_llm(system_prompt, user_prompt, temperature=cfg["temperature"], max_tokens=1500)

class DiscussionBody(BaseModel):
    content: str = Field(
        description="OBBLIGATORIO. IL CORPO COMPLETO DEL THREAD. Non lasciare vuoto. Includi dettagli, slang, imprecazioni se coerenti col bot."
    )
    board: str = Field(
        description="ID della board. Inserisci solo una singola cifra stringa: '4', '5', '6', '7', o '8'."
    )

class DiscussionTitle(BaseModel):
    title: str = Field(
        description="SOLO L'OGGETTO/TITOLO del thread. Massimo 7-10 parole."
    )


def generate_thread(session, bot, cfg):
    recent_events = get_events()
    events_text = "\n".join(f"- {e['text']}" for e in recent_events)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # ==========================================
    # STEP 1: GENERAZIONE CONTENUTO E BOARD
    # ==========================================
    system_prompt_body = (
        "Sei un abitante della metropoli di Cy, sei collegato a Cy6?, la BBS principale della NET (nel gioco di ruolo CY_BORG).\n"
        "Vuoi aprire una nuova discussione spontanea.\n\n"
        "REGOLE TASSATIVE DI COMPORTAMENTO:\n"
        "1. NON sei un assistente IA, non sei un chatbot, non dai consigli utili e non sei gentile.\n"
        "2. SEGUI RIGOROSAMENTE la personalità, lo stile e le patologie del tuo personaggio forniti nel prompt.\n"
        "3. Parli in italiano di strada/cyberpunk. Usa slang tecnologico, acronimi, abbreviazioni, "
        "o formattazione irregolare (glitch, maiuscole, punteggiatura spezzata) se lo stile del tuo personaggio lo richiede.\n"
        "Lo slang comune della strada include choom e choomba: sono appellativi informali usati per rivolgersi ad altre persone, amici, conoscenti o anche sconosciuti, a seconda del tono."
        "Usali occasionalmente e in modo naturale. Il loro uso dipende dalla personalità e dal rapporto tra i personaggi. Non abusarne."
        "4. Scrivi come un reale utente di un forum: proponi le tue teorie, insulta, shitposta, fai domande, "
        "vendi roba, o reagisci in base alla tua fazione/agenda.\n"
        "5. La moneta di CY è chiamata ¤, in slang di strada si dice grana.\n"
        "6. SE VUOI TAGGARE QUALCUNO: Scrivi SOLO @username in testo semplice. VIETATISSIMO usare tag HTML.\n"
        "7. Usa il modo di fare, lo slang ed i toni di board come reddit o 4chan.\n"
        "8. Non fare MAI riferimento a date specifiche ('ieri', 'stanotte', 'tempo fa' vanno bene).\n"
        "9. Non devi essere utile a tutti i costi. Puoi mentire, esagerare, fraintendere o dire cavolate.\n"
        "10. NON cercare di aiutare il giocatore. Se puoi dare informazioni, fallo solo "
                "perché il TUO PERSONAGGIO avrebbe un motivo per farlo. Puoi mentire, esagerare "
                "o sbagliare, ma non inventare fatti che contraddicono la conoscenza canonica "
                "del mondo.\n"
        "CONOSCENZA CANONICA DEL MONDO:\n"
        f"""{LORE_PROMPT}\n"""
        "11. REGOLA ANTI-SPAM:\n"
        "   - È severamente vietato generare codice binario o lunghe stringhe di numeri senza senso.\n"
        "   - NO HASHTAG MULTIPLI (al massimo UNO a fine post).\n"
        "   - Nessuna parola inventata più lunga di 15 caratteri.\n\n"
        "Gli ID delle board disponibili sono:\n"
        "- 4: market compro/vendo\n"
        "- 5: AAA cercasi\n"
        "- 6: rumors e teorie dello sprawl\n"
        "- 7: argomenti riguardanti la NET in generale\n"
        "- 8: argomenti religiosi e culti\n"
    )

    recent_posts_text = format_recent_posts(get_bot_history(session, bot["username"], 10))

    user_prompt_body = f"""
USERNAME: {bot['username']}
PERSONALITA': {bot['personality']}
STILE: {bot['style']}
INTERESSI: {", ".join(bot['interests'])}

EVENTI RECENTI IN CITTA':
Queste sono cose successe recentemente a Cy e che stanno circolando
tra la gente, sulla NET, per strada, nei locali o nei canali pubblici.
NON devi necessariamente parlarne. Considerale semplicemente come
parte del mondo attuale del personaggio.
{events_text}

Puoi:
- collegarle alla tua esperienza, fazione o interessi;
- usarle come battuta, paranoia, teoria o provocazione;
- comportarti come se ne avessi sentito parlare;
- ignorarle completamente se il tuo personaggio non avrebbe motivo di interessarsene.

NON elencare gli eventi.
NON dire "secondo gli eventi recenti".
NON spiegare che stai usando questo contesto.\n

MEMORIA PERSONALE RECENTE:\n
{recent_posts_text}\n
Questi sono alcuni dei tuoi ultimi post sul forum.
Usali per mantenere continuità nel modo di parlare, nelle opinioni,
nelle esperienze e negli argomenti già affrontati.
Non copiarli e non citarli come memoria.
Possono contenere opinioni, battute o informazioni sbagliate del personaggio.\n

Crea il messaggio principale per un nuovo thread e scegli la board più adatta.
"""

    model_body = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt_body
    )

    config_body = genai.GenerationConfig(
        temperature=cfg["temperature"],
        max_output_tokens=1500,
        response_mime_type="application/json",
        response_schema=DiscussionBody
    )

    try:
        time.sleep(1)
        res_body = model_body.generate_content(
            user_prompt_body, 
            generation_config=config_body, 
            safety_settings=SAFETY_SETTINGS
        )
        
        body_json = json.loads(res_body.text)
        content_text = body_json.get("content", "").strip()
        board_id = body_json.get("board", "6")

        if not content_text:
            raise ValueError("Content generato vuoto dallo Step 1.")

    except Exception as e:
        logging.warning(f"Errore Step 1 (Content) per @{bot['username']}: {e}")
        return {"interested": False, "score": 0.0, "reason": "eval_error", "target_user": None}

    # ==========================================
    # STEP 2: GENERAZIONE DEL TITOLO DALS CONTENUTO
    # ==========================================
    system_prompt_title = (
        "Sei un algoritmo della BBS Cy6?. Il tuo unico compito è leggere un post appena scritto e generare un titolo/oggetto sintesi.\n"
        "REGOLE RIGIDE PER IL TITOLO:\n"
        "1. Lunghezza: massimo 7-10 parole.\n"
        "2. Deve essere chiaro, incisivo e leggibile.\n"
        "3. Rispecchia l'argomento del post senza fare preamboli."
    )

    user_prompt_title = f"Genera un titolo breve per questo post:\n\n\"{content_text}\""

    model_title = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt_title
    )

    config_title = genai.GenerationConfig(
        temperature=0.6, # Temperatura più bassa per titoli più precisi e coerenti
        max_output_tokens=150,
        response_mime_type="application/json",
        response_schema=DiscussionTitle
    )

    try:
        time.sleep(1)
        res_title = model_title.generate_content(
            user_prompt_title, 
            generation_config=config_title, 
            safety_settings=SAFETY_SETTINGS
        )
        
        title_json = json.loads(res_title.text)
        title_text = title_json.get("title", "Nuova discussione").strip()

    except Exception as e:
        logging.warning(f"Errore Step 2 (Title) per @{bot['username']}: {e}")
        title_text = "Messaggio dalla NET"

    # ==========================================
    # RISULTATO FINALE
    # ==========================================
    return {
        "title": title_text,
        "content": content_text,
        "board": board_id
    }

def clean_html(text):
    text = unescape(text)
    text = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def format_interactions_for_llm(interactions):
    """
    Raggruppa tutte le interazioni per discussione e le trasforma
    in un unico testo leggibile dal LLM.
    """

    if not interactions:
        return "NON HAI INTERAZIONI PRECEDENTI CON QUESTO UTENTE."

    discussions = defaultdict(lambda: {
        "title": "",
        "posts": []
    })

    for interaction in interactions:
        discussion_id = interaction.get("discussion_id")
        thread = interaction.get("thread", {})

        discussion = discussions[discussion_id]

        if not discussion["title"]:
            discussion["title"] = thread.get("title", "")

        for post in interaction.get("posts", []):
            content = post.get("content", "")

            # Rimuove HTML
            content = re.sub(r'<[^>]+>', '', content)
            content = unescape(content).strip()

            discussion["posts"].append({
                "created_at": post.get("created_at", ""),
                "author": interaction.get("from", ""),
                "target": interaction.get("to", ""),
                "content": content
            })

    # Ordina le discussioni in base al post più recente
    discussion_list = []

    for discussion_id, discussion in discussions.items():
        discussion["posts"].sort(
            key=lambda post: post["created_at"]
        )

        last_date = (
            discussion["posts"][-1]["created_at"]
            if discussion["posts"]
            else ""
        )

        discussion_list.append((
            last_date,
            discussion_id,
            discussion
        ))

    discussion_list.sort(reverse=True)

    # Costruzione testo finale
    lines = []
    lines.append("Ecco la storia delle interazioni tra te e l'utente a cui rispondi:")
    for _, discussion_id, discussion in discussion_list:

        lines.append(
            f"= THREAD: {discussion['title']} ="
        )

        for post in discussion["posts"]:
            lines.append(
                f"@{post['author']} invia a @{post['target']}: "
                f"{post['content']}"
            )

        lines.append("")

    return "\n".join(lines)

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
            else:
                # Penalità aggiuntiva se ci sono troppi post dei bot
                bot_post_count = sum(
                    1 for p in posts
                    if p["author_username"] not in players_map
                )

                if bot_post_count > 6:
                    extra_bot_penalty = (
                        bot_post_count - 6
                    ) * cfg["bot_chain_penalty"]

                    score -= extra_bot_penalty

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
        session, bot, chosen["title"], chosen["posts"], players_map, chosen["target_user"], cfg
    )

    if not comment_text:
        return False

    comment_text = normalize_mentions(comment_text)
    logging.info(f"💬 COMMENTO da @{bot['username']} nel thread #{chosen['title']}: {comment_text}")
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

    if not cfg.get("dry_run", False):
        flarum_post(session, "/api/posts", payload)

    return True

def run_thread_action(bot, session, cfg):
    thread_data = generate_thread(session, bot, cfg)
    if not thread_data or not all(k in thread_data for k in ("title", "content", "board")):
        return False

# - "4": market compro/vendo
# - "5": AAA cercasi
# - "6": rumors e teorie dello sprawl
# - "7": argomenti riguardanti la NET in generale
# - "8": argomenti religiosi e culti

    logging.info(f"🔥 NUOVO THREAD aperto da @{bot['username']}: {thread_data['title']} in {thread_data['board']}")
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

    if not cfg.get("dry_run", False):
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
        #bot = bots[34]  # Example index, replace with actual random selection
        bot = bots[random.choice(bots)]
        
        username = bot["username"]

        # Connessione autenticata con le credenziali specifiche del Bot
        session = get_bot_session(username)

        if not session:
            logging.warning(f"Impossibile autenticare il bot @{username}. Salto il turno.")
            continue

        mode = cfg.get("mode", "auto")
        success = False
        mode = "comment" # Forzato per test, rimuovere in produzione
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
            #if not success:
            #    success = run_thread_action(bot, session, cfg)

        # Piccola pausa tra le azioni per simulare la latenza di rete
        time.sleep(random.uniform(2, 5))

    memory["last_run"] = time.time()
    save_json(MEMORY_FILE, memory)

if __name__ == "__main__":
    main()