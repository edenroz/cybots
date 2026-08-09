import json
import logging
import os
import random
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
import google.generativeai as genai


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

FLARUM_URL = os.environ["FLARUM_URL"].rstrip("/")
FLARUM_TOKEN = os.environ["FLARUM_API_TOKEN"]

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-1.5-flash"
)

CONFIG_FILE = Path("config.json")
BOTS_FILE = Path("bots.json")
PLAYERS_FILE = Path("players.json")
EVENTS_FILE = Path("events.json")
BOT_PASSWORD = os.getenv("FLARUM_BOT_PASSWORD")

DATA_DIR = Path("data")
MEMORY_FILE = DATA_DIR / "memory.json"

# Inizializza il client di Gemini
genai.configure(api_key=GEMINI_API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# ============================================================
# JSON
# ============================================================

def login(session, USERNAME, PASSWORD):
    """
    Effettua il login del bot e conserva il cookie/token
    nella requests.Session().
    """

    url = f"{FLARUM_URL}/api/token"

    response = session.post(
        url,
        json={
            "identification": USERNAME,
            "password": PASSWORD
        },
        timeout=REQUEST_TIMEOUT
    )

    if response.status_code != 200:
        print("\nERRORE: impossibile effettuare il login.")
        print(f"HTTP {response.status_code}")
        print(response.text)
        sys.exit(1)

    data = response.json()

    token = data.get("token")

    if not token:
        print("ERRORE: Flarum non ha restituito un token.")
        print(data)
        sys.exit(1)

    session.headers.update({
        "Authorization": f"Token {token}"
    })

    print("Login Flarum: OK")

def load_json(path, default):

    if not path.exists():
        return default

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save_json(path, data):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with path.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


def get_config():
    return load_json(
        CONFIG_FILE,
        {}
    )


def get_bots():
    return load_json(
        BOTS_FILE,
        []
    )


def get_players():
    return load_json(
        PLAYERS_FILE,
        []
    )


def get_events():
    return load_json(
        EVENTS_FILE,
        []
    )


def get_memory():

    return load_json(
        MEMORY_FILE,
        {
            "posts": [],
            "relationships": {},
            "last_run": 0
        }
    )


# ============================================================
# FLARUM API
# ============================================================

def flarum_headers(user_id=None):

    authorization = (
        f"Token {FLARUM_TOKEN}"
    )

    if user_id is not None:
        authorization += (
            f"; userId={user_id}"
        )

    return {
        "Authorization": authorization,
        "Content-Type": "application/vnd.api+json",
        "Accept": "application/vnd.api+json"
    }


def flarum_get(
    endpoint,
    params=None
):

    response = requests.get(
        FLARUM_URL + endpoint,
        headers=flarum_headers(),
        params=params,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def flarum_post(
    endpoint,
    payload,
    user_id
):

    response = requests.post(
        FLARUM_URL + endpoint,
        headers=flarum_headers(user_id),
        json=payload,
        timeout=30
    )

    if not response.ok:

        logging.error(
            "Flarum error %s: %s",
            response.status_code,
            response.text
        )

    response.raise_for_status()

    return response.json()


# ============================================================
# USERS
# ============================================================

def get_users():

    result = flarum_get(
        "/api/users",
        {
            "page[limit]": 100
        }
    )

    return result.get(
        "data",
        []
    )


def build_user_map():

    users = get_users()

    result = {}

    for user in users:

        username = (
            user
            .get("attributes", {})
            .get("username")
        )

        if username:
            result[username] = str(
                user["id"]
            )

    return result


# ============================================================
# DISCUSSIONS
# ============================================================

def get_discussions(limit):

    result = flarum_get(
        "/api/discussions",
        {
            "page[limit]": limit,
            "sort": "-created"
        }
    )

    return result.get(
        "data",
        []
    )


def get_discussion_posts(
    discussion_id,
    limit
):

    result = flarum_get(
        "/api/posts",
        {
            "filter[discussion]": discussion_id,
            "page[limit]": limit,
            "sort": "created"
        }
    )

    return result.get(
        "data",
        []
    )


# ============================================================
# USER CLASSIFICATION
# ============================================================

def classify_users(
    players,
    bots,
    user_map
):

    result = {}

    for player in players:

        username = player["username"]

        if username in user_map:

            result[user_map[username]] = {
                "type": "player",
                "username": username,
                "character": player.get(
                    "character",
                    username
                ),
                "description": player.get(
                    "description",
                    ""
                )
            }

    for bot in bots:

        username = bot["username"]

        if username in user_map:

            result[user_map[username]] = {
                "type": "bot",
                "username": username
            }

    return result


# ============================================================
# POST INFORMATION
# ============================================================

def post_author_id(post):

    return (
        post
        .get("relationships", {})
        .get("user", {})
        .get("data", {})
        .get("id")
    )


def post_content(post):

    return (
        post
        .get("attributes", {})
        .get("content", "")
        .strip()
    )


def post_created_at(post):

    return (
        post
        .get("attributes", {})
        .get("createdAt", "")
    )


def describe_post(
    post,
    user_map
):

    author_id = post_author_id(post)

    author = user_map.get(
        str(author_id),
        {}
    )

    content = post_content(post)

    if author.get("type") == "player":

        name = author["username"]

        character = author.get(
            "character",
            ""
        )

        label = (
            f"PLAYER {name} "
            f"(personaggio: {character})"
        )

    elif author.get("type") == "bot":

        label = (
            f"BOT {author['username']}"
        )

    else:

        label = (
            f"UTENTE {author_id}"
        )

    return (
        f"{label}:\n{content}"
    )


# ============================================================
# LLM
# ============================================================

def ask_llm(
    system,
    prompt,
    temperature=1.0,
    max_tokens=300
):
    
    # Inizializziamo il modello con le istruzioni di sistema
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system
    )
    
    # Configuriamo i parametri di generazione
    generation_config = genai.GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        return response.text.strip()
    except Exception as e:
        logging.error(f"Errore durante la chiamata LLM: {e}")
        return ""


def clean_json(text):

    text = text.strip()

    if text.startswith("```"):

        text = re.sub(
            r"^```(?:json)?",
            "",
            text
        )

        text = re.sub(
            r"```$",
            "",
            text
        )

    return text.strip()


# ============================================================
# BOT MEMORY
# ============================================================

def bot_history(
    memory,
    username
):

    return [
        x
        for x in memory["posts"]
        if x["username"] == username
    ]


def relationship_key(
    bot_username,
    other_username
):

    return (
        f"{bot_username}:"
        f"{other_username}"
    )


def get_relationship(
    memory,
    bot_username,
    other_username
):

    key = relationship_key(
        bot_username,
        other_username
    )

    return memory[
        "relationships"
    ].get(
        key,
        {
            "sentiment": 0,
            "interactions": 0,
            "notes": []
        }
    )


def update_relationship(
    memory,
    bot_username,
    other_username,
    sentiment,
    note
):

    key = relationship_key(
        bot_username,
        other_username
    )

    relationship = (
        memory["relationships"]
        .setdefault(
            key,
            {
                "sentiment": 0,
                "interactions": 0,
                "notes": []
            }
        )
    )

    relationship["sentiment"] = max(
        -1,
        min(
            1,
            relationship["sentiment"]
            + sentiment
        )
    )

    relationship["interactions"] += 1

    if note:

        relationship["notes"].append(
            note
        )

        relationship["notes"] = (
            relationship["notes"][-10:]
        )


# ============================================================
# BOT SELECTION
# ============================================================

def choose_bot(
    bots,
    memory
):

    weighted = []

    now = time.time()

    for bot in bots:

        history = bot_history(
            memory,
            bot["username"]
        )

        if not history:

            weight = 5

        else:

            last = max(
                x["timestamp"]
                for x in history
            )

            hours = (
                now - last
            ) / 3600

            weight = min(
                max(hours, 0.5),
                24
            )

        weighted.append(
            (bot, weight)
        )

    total = sum(
        weight
        for _, weight in weighted
    )

    choice = random.uniform(
        0,
        total
    )

    current = 0

    for bot, weight in weighted:

        current += weight

        if choice <= current:
            return bot

    return weighted[-1][0]


# ============================================================
# DISCUSSION EVALUATION
# ============================================================

def evaluate_discussion(
    bot,
    discussion,
    posts,
    user_info,
    memory,
    cfg
):

    title = (
        discussion
        .get("attributes", {})
        .get("title", "")
    )

    conversation = "\n\n".join(
        describe_post(
            post,
            user_info
        )
        for post in posts[-12:]
    )

    recent_events = get_events()[-10:]

    events_text = "\n".join(
        f"- {event['text']}"
        for event in recent_events
    )

    own_history = bot_history(
        memory,
        bot["username"]
    )[-5:]

    history_text = "\n".join(
        f"- {x['content']}"
        for x in own_history
    )

    prompt = f"""
Sei il sistema che decide se un personaggio
fittizio di una community cyberpunk dovrebbe
partecipare a una discussione.

PERSONAGGIO:

username:
{bot["username"]}

personalità:
{bot["personality"]}

stile:
{bot["style"]}

interessi:
{", ".join(bot["interests"])}

conoscenze:
{", ".join(bot.get("knowledge", []))}

quirks:
{", ".join(bot.get("quirks", []))}

EVENTI RECENTI:

{events_text}

DISCUSSIONE:

TITOLO:
{title}

MESSAGGI:

{conversation}

ULTIMI POST DEL PERSONAGGIO:

{history_text}

Devi decidere se questo personaggio
avrebbe spontaneamente qualcosa da dire.

È particolarmente interessante se:

- un giocatore ha detto qualcosa che lo riguarda;
- qualcuno ha parlato di un suo interesse;
- qualcuno ha espresso un'opinione che detesta;
- ha competenza sull'argomento;
- può raccontare un'esperienza;
- può collegare la discussione a un evento;
- c'è un'opportunità naturale per una battuta;
- conosce o ha già interagito con l'autore.

NON deve rispondere solo perché il post
è stato scritto da un giocatore.

NON deve partecipare a tutte le discussioni.

Restituisci SOLO:

{{
  "interested": true,
  "score": 0.0,
  "reason": "perché",
  "target_user": "username se rilevante oppure null"
}}

score da 0 a 1.
"""

    result = ask_llm(
        system=(
            "Sei un classificatore di rilevanza. "
            "Restituisci esclusivamente JSON valido."
        ),
        prompt=prompt,
        temperature=0.15,
        max_tokens=200
    )

    try:

        return json.loads(
            clean_json(result)
        )

    except Exception:

        logging.warning(
            "Invalid classifier response: %s",
            result
        )

        return {
            "interested": False,
            "score": 0,
            "reason": "invalid",
            "target_user": None
        }


# ============================================================
# DISCUSSION SELECTION
# ============================================================

def choose_discussion(
    bot,
    discussions,
    user_info,
    memory,
    cfg
):

    candidates = []

    for discussion in discussions:

        discussion_id = str(
            discussion["id"]
        )

        recent_bot_posts = [
            x
            for x in memory["posts"]
            if (
                x["username"]
                == bot["username"]
                and x["discussion_id"]
                == discussion_id
            )
        ]

        if recent_bot_posts:

            latest = max(
                x["timestamp"]
                for x in recent_bot_posts
            )

            hours = (
                time.time() - latest
            ) / 3600

            if hours < cfg[
                "avoid_same_bot_same_discussion_hours"
            ]:
                continue

        posts = get_discussion_posts(
            discussion_id,
            cfg[
                "max_posts_per_discussion"
            ]
        )

        if not posts:
            continue

        evaluation = evaluate_discussion(
            bot,
            discussion,
            posts,
            user_info,
            memory,
            cfg
        )

        score = float(
            evaluation.get(
                "score",
                0
            )
        )

        if not evaluation.get(
            "interested",
            False
        ):
            continue

        # ----------------------------------------------------
        # PLAYER BONUS
        # ----------------------------------------------------

        player_present = any(
            user_info.get(
                str(post_author_id(post)),
                {}
            ).get("type") == "player"
            for post in posts
        )

        if player_present:

            score += cfg.get(
                "player_reply_bonus",
                0.12
            )

        # ----------------------------------------------------
        # BOT CHAIN PENALTY
        # ----------------------------------------------------

        if cfg.get(
            "avoid_immediate_bot_chain",
            True
        ):

            if posts:

                last_author = user_info.get(
                    str(
                        post_author_id(
                            posts[-1]
                        )
                    ),
                    {}
                )

                if (
                    last_author.get(
                        "type"
                    ) == "bot"
                ):

                    score -= cfg.get(
                        "bot_chain_penalty",
                        0.25
                    )

        if score < cfg[
            "minimum_relevance"
        ]:
            continue

        candidates.append(
            {
                "discussion": discussion,
                "posts": posts,
                "score": score,
                "reason": evaluation.get(
                    "reason",
                    ""
                )
            }
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # Evita comportamento troppo deterministico.
    top = candidates[:3]

    return random.choice(top)


# ============================================================
# GENERATE COMMENT
# ============================================================

def generate_comment(
    bot,
    discussion,
    posts,
    user_info,
    memory,
    cfg
):

    title = (
        discussion
        .get("attributes", {})
        .get("title", "")
    )

    conversation = "\n\n".join(
        describe_post(
            post,
            user_info
        )
        for post in posts[-12:]
    )

    own_history = bot_history(
        memory,
        bot["username"]
    )[-5:]

    previous = "\n".join(
        x["content"]
        for x in own_history
    )

    relationships = []

    for post in posts:

        author_id = post_author_id(
            post
        )

        author = user_info.get(
            str(author_id),
            {}
        )

        username = author.get(
            "username"
        )

        if not username:
            continue

        relationship = get_relationship(
            memory,
            bot["username"],
            username
        )

        if relationship["interactions"]:

            relationships.append(
                f"{username}: "
                f"sentimento={relationship['sentiment']:.2f}; "
                f"note={relationship['notes'][-2:]}"
            )

    relationship_text = "\n".join(
        relationships
    )

    prompt = f"""
Sei un utente fittizio di una messageboard
cyberpunk italiana.

Stai scrivendo una risposta.

NON sei un assistente.
NON sei un narratore.
NON spiegare il mondo al lettore.
NON dire che sei una IA.

IDENTITÀ:

{bot["username"]}

PERSONALITÀ:

{bot["personality"]}

STILE:

{bot["style"]}

INTERESSI:

{", ".join(bot["interests"])}

CONOSCENZE:

{", ".join(bot.get("knowledge", []))}

QUIRKS:

{", ".join(bot.get("quirks", []))}

DISCUSSIONE:

{title}

CONVERSAZIONE:

{conversation}

RELAZIONI CON GLI ALTRI:

{relationship_text}

ULTIMI POST TUOI:

{previous}

Scrivi UNA risposta.

Deve sembrare una cosa che questo
personaggio scriverebbe davvero.

Puoi:

- concordare
- contraddire
- insultare
- scherzare
- fare una domanda
- raccontare qualcosa
- correggere qualcuno
- diffondere una voce
- ignorare il punto principale
- rispondere direttamente a un giocatore
- fare shitposting

Non essere necessariamente utile.

Non devi necessariamente rispondere
all'ultimo messaggio.

Non ripetere informazioni già dette.

Massimo {cfg["max_post_words"]} parole.

SCRIVI IN ITALIANO.

Restituisci SOLO il testo.
"""

    return ask_llm(
        system=(
            "Sei un membro di una community "
            "cyberpunk italiana fittizia."
        ),
        prompt=prompt,
        temperature=cfg["temperature"],
        max_tokens=220
    )


# ============================================================
# GENERATE NEW THREAD
# ============================================================

def generate_thread(
    bot,
    memory,
    cfg
):

    recent_events = get_events()[-10:]

    events_text = "\n".join(
        f"- {event['text']}"
        for event in recent_events
    )

    history = bot_history(
        memory,
        bot["username"]
    )[-5:]

    previous = "\n".join(
        x["content"]
        for x in history
    )

    prompt = f"""
Sei un utente fittizio di una messageboard
cyberpunk italiana.

Crea una nuova discussione.

USERNAME:
{bot["username"]}

PERSONALITÀ:
{bot["personality"]}

STILE:
{bot["style"]}

INTERESSI:
{", ".join(bot["interests"])}

CONOSCENZE:
{", ".join(bot.get("knowledge", []))}

QUIRKS:
{", ".join(bot.get("quirks", []))}

EVENTI RECENTI:
{events_text}

TUOI POST RECENTI:
{previous}

Il thread deve sembrare spontaneo.

Può essere:

- una voce
- una domanda
- una lamentela
- una storia personale
- una richiesta
- una teoria
- un avvertimento
- un shitpost
- una cosa strana successa per strada

Non citare necessariamente gli eventi.

SCRIVI IN ITALIANO.

Restituisci:

{{
  "title": "titolo",
  "content": "testo"
}}
"""

    result = ask_llm(
        system=(
            "Generi contenuti per una "
            "messageboard cyberpunk italiana. "
            "Restituisci solo JSON valido."
        ),
        prompt=prompt,
        temperature=cfg["temperature"],
        max_tokens=300
    )

    try:

        return json.loads(
            clean_json(result)
        )

    except Exception:

        logging.error(
            "Invalid thread JSON: %s",
            result
        )

        return None


# ============================================================
# CREATE THREAD
# ============================================================

def create_thread(
    user_id,
    title,
    content,
    tag_id
):

    payload = {
        "data": {
            "type": "discussions",

            "attributes": {
                "title": title,
                "content": content
            },

            "relationships": {
                "tags": {
                    "data": [
                        {
                            "type": "tags",
                            "id": str(tag_id)
                        }
                    ]
                }
            }
        }
    }

    return flarum_post(
        "/api/discussions",
        payload,
        user_id
    )


# ============================================================
# CREATE COMMENT
# ============================================================

def create_comment(
    user_id,
    discussion_id,
    content
):

    payload = {
        "data": {
            "type": "posts",

            "attributes": {
                "content": content
            },

            "relationships": {
                "discussion": {
                    "data": {
                        "type": "discussions",
                        "id": str(discussion_id)
                    }
                }
            }
        }
    }

    return flarum_post(
        "/api/posts",
        payload,
        user_id
    )


# ============================================================
# UPDATE MEMORY
# ============================================================

def remember_post(
    memory,
    bot,
    discussion_id,
    post_id,
    content,
    post_type
):

    memory["posts"].append(
        {
            "username": bot["username"],
            "discussion_id": str(
                discussion_id
            ),
            "post_id": str(
                post_id
            ),
            "content": content,
            "type": post_type,
            "timestamp": time.time()
        }
    )

    # Mantiene il database leggero.
    memory["posts"] = (
        memory["posts"][-3000:]
    )


# ============================================================
# LEARN FROM INTERACTION
# ============================================================

def learn_relationship(
    bot,
    posts,
    user_info,
    memory
):

    relevant_authors = []

    for post in posts:

        author_id = post_author_id(
            post
        )

        author = user_info.get(
            str(author_id),
            {}
        )

        if not author:
            continue

        username = author.get(
            "username"
        )

        if not username:
            continue

        if username == bot["username"]:
            continue

        relevant_authors.append(
            username
        )

    relevant_authors = list(
        dict.fromkeys(
            relevant_authors
        )
    )

    for username in relevant_authors:

        # Inizialmente non cambiamo
        # artificialmente l'opinione.
        relationship = get_relationship(
            memory,
            bot["username"],
            username
        )

        if relationship["interactions"] == 0:

            update_relationship(
                memory,
                bot["username"],
                username,
                0,
                "Prima interazione."
            )


# ============================================================
# RUN NEW THREAD
# ============================================================

def run_new_thread(
    bot,
    user_id,
    memory,
    cfg
):

    generated = generate_thread(
        bot,
        memory,
        cfg
    )

    if not generated:
        return False

    title = generated[
        "title"
    ].strip()

    content = generated[
        "content"
    ].strip()

    result = create_thread(
        user_id,
        title,
        content,
        cfg["tag_id"]
    )

    discussion_id = result[
        "data"
    ]["id"]

    post_id = (
        result
        .get("data", {})
        .get("relationships", {})
        .get("posts", {})
        .get("data", [{}])[0]
        .get("id", discussion_id)
    )

    remember_post(
        memory,
        bot,
        discussion_id,
        post_id,
        content,
        "thread"
    )

    logging.info(
        "THREAD #%s by %s: %s",
        discussion_id,
        bot["username"],
        title
    )

    return True


# ============================================================
# RUN COMMENT
# ============================================================

def run_comment(
    bot,
    user_id,
    memory,
    cfg,
    user_info
):

    discussions = get_discussions(
        cfg[
            "max_discussions_to_consider"
        ]
    )

    selected = choose_discussion(
        bot,
        discussions,
        user_info,
        memory,
        cfg
    )

    if not selected:

        logging.info(
            "%s: nessuna discussione "
            "sufficientemente interessante.",
            bot["username"]
        )

        return False

    discussion = selected[
        "discussion"
    ]

    posts = selected[
        "posts"
    ]

    discussion_id = discussion[
        "id"
    ]

    content = generate_comment(
        bot,
        discussion,
        posts,
        user_info,
        memory,
        cfg
    )

    if not content:
        return False

    result = create_comment(
        user_id,
        discussion_id,
        content
    )

    post_id = result[
        "data"
    ]["id"]

    remember_post(
        memory,
        bot,
        discussion_id,
        post_id,
        content,
        "comment"
    )

    learn_relationship(
        bot,
        posts,
        user_info,
        memory
    )

    logging.info(
        "COMMENT #%s by %s -> discussion #%s",
        post_id,
        bot["username"],
        discussion_id
    )

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    cfg = get_config()

    bots = get_bots()
    players = get_players()

    memory = get_memory()

    if not bots:
        raise RuntimeError(
            "bots.json vuoto."
        )

    logging.info(
        "Caricati %d bot e %d giocatori.",
        len(bots),
        len(players)
    )

    # --------------------------------------------------------
    # RISOLUZIONE UTENTI FLARUM
    # --------------------------------------------------------

    user_map = build_user_map()

    user_info = classify_users(
        players,
        bots,
        user_map
    )

    # --------------------------------------------------------
    # ESECUZIONE
    # --------------------------------------------------------

    for _ in range(
        cfg.get(
            "posts_per_run",
            1
        )
    ):

        bot = choose_bot(
            bots,
            memory
        )

        user_id = user_map.get(
            bot["username"]
        )

        if not user_id:

            logging.error(
                "Account Flarum non trovato: %s",
                bot["username"]
            )

            continue

        mode = cfg.get(
            "mode",
            "auto"
        )

        if mode == "new_thread":

            run_new_thread(
                bot,
                user_id,
                memory,
                cfg
            )

        elif mode == "comment":

            run_comment(
                bot,
                user_id,
                memory,
                cfg,
                user_info
            )

        elif mode == "auto":

            if random.random() < cfg[
                "new_thread_probability"
            ]:

                success = run_new_thread(
                    bot,
                    user_id,
                    memory,
                    cfg
                )

            else:

                success = run_comment(
                    bot,
                    user_id,
                    memory,
                    cfg,
                    user_info
                )

            # Se non trova niente di interessante,
            # può creare un nuovo thread.
            if not success:

                run_new_thread(
                    bot,
                    user_id,
                    memory,
                    cfg
                )

        else:

            raise RuntimeError(
                f"Modalità sconosciuta: {mode}"
            )

    memory["last_run"] = time.time()

    save_json(
        MEMORY_FILE,
        memory
    )


if __name__ == "__main__":
    main()