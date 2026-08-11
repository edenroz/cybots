import argparse
import math
import os
import platform
import queue
import random
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import wave
from pathlib import Path

from screeninfo import get_monitors


# ============================================================
# SET DI CARATTERI ASR-33 (solo maiuscole)
# ============================================================
# La vera Model 33 ASR usava un sottoinsieme ASCII a 7 bit
# senza minuscole: la ruota tipografica aveva solo 64 caratteri
# incisi. Per restare fedeli, il testo viene convertito in
# maiuscolo (le accentate italiane vengono normalizzate perche'
# non esistevano sulla ruota).

_ASR33_CASEFOLD = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzàèéìòù",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZAEEIOU"
)


def to_asr33_charset(text, preserve_case=False):

    if preserve_case:
        return text

    return text.translate(_ASR33_CASEFOLD)


# ============================================================
# SUONI MECCANICI (sintetizzati, nessuna dipendenza esterna)
# ============================================================

class MechanicalSound:
    """
    Genera al volo brevi suoni (colpo del martelletto, campanello
    di margine, ritorno del carrello) usando solo il modulo
    'wave' della libreria standard.

    La riproduzione avviene tramite UNA SOLA coda sequenziale
    (un solo thread worker che consuma la coda): questo garantisce
    che i suoni vengano riprodotti nello stesso ordine in cui i
    caratteri vengono stampati, senza sovrapposizioni o "gare"
    tra thread concorrenti che chiamano winsound/aplay/afplay in
    parallelo — che e' la causa piu' comune di audio "sfasato" o
    silenzioso su Windows.
    """

    SAMPLE_RATE = 22050

    def __init__(self, enabled=True):

        self.enabled = enabled
        self.status = "disattivato"
        self.last_error = None
        self._tmp_dir = None
        self._sounds = {}
        self._queue = queue.Queue()
        self._worker = None
        self._player = self._detect_player()

        if not self.enabled:
            self.status = "disattivato (--no-sound)"
            return

        if not self._player:
            self.enabled = False
            self.status = "nessun player audio trovato"
            return

        try:
            self._tmp_dir = tempfile.mkdtemp(prefix="asr33_snd_")
            self._sounds["key"] = self._render_click()
            self._sounds["bell"] = self._render_bell()
            self._sounds["cr"] = self._render_carriage()
        except Exception as exc:
            print(f"[ASR-33] Audio disattivato: errore nella generazione dei suoni ({exc}).")
            self.enabled = False
            self.status = f"errore generazione: {exc}"
            return

        # Test di riproduzione VERO e SINCRONO all'avvio: se il
        # player fallisce lo scopriamo subito, prima di avviare
        # la coda per la stampa.
        try:
            self._play_blocking("bell")
            self.status = f"attivo ({self._player_label()})"
        except Exception as exc:
            self.enabled = False
            self.last_error = str(exc)
            self.status = f"errore riproduzione: {exc}"
            return

        self._worker = threading.Thread(
            target=self._worker_loop,
            daemon=True
        )
        self._worker.start()

    # --------------------------------------------------------

    def _player_label(self):

        if isinstance(self._player, list):
            return self._player[0]

        return self._player

    # --------------------------------------------------------
    # PLAYER
    # --------------------------------------------------------

    def _detect_player(self):

        system = platform.system()

        if system == "Windows":
            try:
                import winsound
                return "winsound"
            except ImportError:
                return None

        if system == "Darwin":
            player = shutil.which("afplay")
            if not player:
                print(
                    "[ASR-33] Audio disattivato: 'afplay' non trovato "
                    "(dovrebbe essere preinstallato su macOS)."
                )
            return player

        # Linux e altri: proviamo diversi player in ordine di
        # probabilita'; basta che uno sia installato.
        candidates = ["paplay", "aplay", "play", "ffplay", "mpv"]

        for name in candidates:
            player = shutil.which(name)
            if player:
                return [player, "-nodisp", "-autoexit"] if name == "ffplay" else player

        print(
            "[ASR-33] Audio disattivato: nessun player trovato tra "
            + ", ".join(candidates) +
            ". Installa 'alsa-utils' (aplay), 'pulseaudio-utils' "
            "(paplay) o 'sox' (play) per sentire i suoni meccanici."
        )
        return None

    # --------------------------------------------------------
    # CODA SEQUENZIALE — un solo suono in riproduzione per volta
    # --------------------------------------------------------

    def _worker_loop(self):

        while True:
            name = self._queue.get()

            if name is None:
                break

            try:
                self._play_blocking(name)
            except Exception as exc:
                self.last_error = str(exc)

    # --------------------------------------------------------

    def _play_blocking(self, name):

        path = self._sounds[name]

        if self._player == "winsound":
            import winsound
            # Niente SND_ASYNC: la chiamata resta bloccante
            # dentro il worker thread, cosi' il suono successivo
            # in coda parte solo quando il precedente e' finito.
            winsound.PlaySound(path, winsound.SND_FILENAME)
        else:
            cmd = (
                self._player + [path]
                if isinstance(self._player, list)
                else [self._player, path]
            )
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode != 0:
                raise RuntimeError(
                    result.stderr.decode(errors="replace").strip()
                    or f"'{cmd[0]}' uscito con codice {result.returncode}"
                )

    # --------------------------------------------------------

    def play(self, name):

        if not self.enabled or name not in self._sounds:
            return

        # Backpressure: se la coda si sta accumulando (perche' il
        # player e' piu' lento della velocita' di stampa), i
        # click meno importanti vengono scartati per non far
        # sfasare l'audio dal testo. Campanello e ritorno
        # carrello restano sempre in coda perche' sono eventi
        # rari e significativi.
        if name == "key" and self._queue.qsize() > 2:
            return

        self._queue.put_nowait(name)

    # --------------------------------------------------------
    # ENVELOPE
    # --------------------------------------------------------

    def _envelope(self, n, attack=0.05, decay=1.0):

        env = []
        a = max(1, int(n * attack))

        for i in range(n):
            if i < a:
                env.append(i / a)
            else:
                env.append(math.exp(-decay * (i - a) / n * 8))

        return env

    # --------------------------------------------------------
    # WRITE WAV
    # --------------------------------------------------------

    def _write_wav(self, name, samples):

        path = os.path.join(self._tmp_dir, f"{name}.wav")

        with wave.open(path, "wb") as f:

            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(self.SAMPLE_RATE)

            frames = b"".join(
                struct.pack("<h", max(-32768, min(32767, int(s))))
                for s in samples
            )

            f.writeframes(frames)

        return path

    # --------------------------------------------------------
    # KEY
    # --------------------------------------------------------

    def _render_click(self):

        # Colpo secco del martelletto sulla ruota tipografica:
        # rumore filtrato + una componente tonale metallica.
        n = int(self.SAMPLE_RATE * 0.018)
        env = self._envelope(n, attack=0.03, decay=1.6)

        samples = [
            (
                random.uniform(-1, 1) * 0.6
                + math.sin(2 * math.pi * 1800 * i / self.SAMPLE_RATE) * 0.4
            ) * env[i] * 14000
            for i in range(n)
        ]

        return self._write_wav("key", samples)

    # --------------------------------------------------------
    # BELL
    # --------------------------------------------------------

    def _render_bell(self):

        # Campanello di margine (colonna 64): tono a due
        # armoniche con decadimento lungo, come una vera
        # campanella elettrica.
        n = int(self.SAMPLE_RATE * 0.35)
        env = self._envelope(n, attack=0.01, decay=2.5)

        samples = [
            (
                math.sin(2 * math.pi * 2100 * i / self.SAMPLE_RATE)
                + 0.35 * math.sin(2 * math.pi * 2800 * i / self.SAMPLE_RATE)
            ) * env[i] * 9000
            for i in range(n)
        ]

        return self._write_wav("bell", samples)

    # --------------------------------------------------------
    # CARRIAGE RETURN
    # --------------------------------------------------------

    def _render_carriage(self):

        # Ritorno carrello: "kerchunk" grave e più lungo del
        # semplice colpo di stampa.
        n = int(self.SAMPLE_RATE * 0.09)
        env = self._envelope(n, attack=0.05, decay=1.1)

        samples = [
            (
                random.uniform(-1, 1) * 0.5
                + math.sin(2 * math.pi * 250 * i / self.SAMPLE_RATE) * 0.5
            ) * env[i] * 15000
            for i in range(n)
        ]

        return self._write_wav("cr", samples)

    # --------------------------------------------------------

    def cleanup(self):

        if self._worker and self._worker.is_alive():
            self._queue.put_nowait(None)
            self._worker.join(timeout=1.0)

        if self._tmp_dir and os.path.isdir(self._tmp_dir):
            shutil.rmtree(self._tmp_dir, ignore_errors=True)



# ============================================================
# ASR-33 TELETYPE SIMULATOR
# ============================================================

class ASR33:

    def __init__(
        self,
        text,
        chars_per_second=10,
        font_size=26,
        mechanical_jitter=True,
        columns=72,
        preserve_case=False,
        sound=True,
        ribbon_wear=False,
        margin_bell=True
    ):
        self.text = to_asr33_charset(text, preserve_case=preserve_case)
        self.chars_per_second = chars_per_second
        self.font_size = font_size
        self.mechanical_jitter = mechanical_jitter
        self.columns = max(10, columns)
        self.ribbon_wear = ribbon_wear
        self.margin_bell_enabled = margin_bell
        self.margin_bell_column = max(1, self.columns - 8)

        self.running = False
        self.current_column = 0
        self.bell_rung_this_line = False
        self.last_line_length = 0

        self.sound = MechanicalSound(enabled=sound)

        # ----------------------------------------------------
        # WINDOW
        # ----------------------------------------------------

        self.root = tk.Tk()

        self.root.title("CYENERGY™ CORPORATION // MODEL 33 ASR")

        self.root.attributes("-fullscreen", True)
        self.root.overrideredirect(True)

        # ----------------------------------------------------
        # MONITOR
        # ----------------------------------------------------

        try:
            monitors = get_monitors()
        except Exception:
            monitors = []

        if len(monitors) >= 2:
            monitor = monitors[1]
        elif len(monitors) == 1:
            monitor = monitors[0]
        else:
            # Nessun monitor rilevato (es. ambiente headless):
            # ricado su una geometria di default ragionevole.
            monitor = type(
                "FallbackMonitor",
                (),
                {"width": 1024, "height": 768, "x": 0, "y": 0}
            )()

        self.root.geometry(
            f"{monitor.width}x{monitor.height}"
            f"+{monitor.x}+{monitor.y}"
        )

        self.screen_width = monitor.width
        self.screen_height = monitor.height

        # ----------------------------------------------------
        # COLORS
        # ----------------------------------------------------

        self.background_color = "#151515"
        self.paper_color = "#e8e0c8"
        self.ink_color = "#181818"
        self.ink_color_faint = "#4a4636"
        self.hole_color = "#b8b09a"
        self.edge_color = "#c8c0a8"

        self.root.configure(
            bg=self.background_color
        )

        # ----------------------------------------------------
        # CANVAS
        # ----------------------------------------------------

        self.canvas = tk.Canvas(
            self.root,
            bg=self.background_color,
            highlightthickness=0,
            borderwidth=0
        )

        self.canvas.pack(
            fill="both",
            expand=True
        )

        # ----------------------------------------------------
        # PAPER DIMENSIONS
        # ----------------------------------------------------

        self.paper_margin_x = 90
        self.paper_width = self.screen_width - (
            self.paper_margin_x * 2
        )

        # ----------------------------------------------------
        # PRINTING AREA
        # ----------------------------------------------------

        self.print_margin_left = 90
        self.print_margin_right = 90

        self.text_x = (
            self.paper_margin_x +
            self.print_margin_left
        )

        self.text_y = 70

        # ----------------------------------------------------
        # FONT — deve essere davvero a spaziatura fissa
        # ----------------------------------------------------
        # "Courier New" esiste su Windows ma non sempre su
        # Linux/macOS: se manca, Tk lo sostituisce con un font
        # qualsiasi (spesso non monospace), e allora avanzare
        # di un passo fisso per carattere manda tutto storto.
        # Qui si sceglie il primo font davvero disponibile tra
        # i candidati, e si MISURA la sua larghezza/altezza
        # reali invece di stimarle a occhio.

        self.font_family = self._pick_monospace_font()
        self._font = tkfont.Font(
            family=self.font_family,
            size=self.font_size
        )

        self.char_width = self._font.measure("0")
        self.line_height = int(self._font.metrics("linespace") * 1.15)

        # ----------------------------------------------------
        # ROTOLO DI CARTA CONTINUO
        # ----------------------------------------------------
        # Invece di disegnare la carta una sola volta (che
        # lascerebbe uno sfondo vuoto una volta scorsa oltre lo
        # schermo), la carta viene estesa a "segmenti" man mano
        # che la stampa avanza, e i segmenti che sono scorsi
        # fuori dallo schermo vengono eliminati per non
        # accumulare oggetti sul canvas all'infinito.

        self.paper_bottom_y = 0
        self._segment_id = 0
        self._segments = []

        self.extend_paper()
        self.extend_paper()  # un buffer extra oltre il primo schermo

        # ----------------------------------------------------
        # DIAGNOSTICA AUDIO — visibile anche senza terminale
        # ----------------------------------------------------
        # Se lo script viene lanciato con doppio click su
        # Windows non c'e' nessuna console dove leggere i
        # messaggi stampati: questa etichetta mostra lo stato
        # reale dell'audio direttamente nella finestra.

        self.canvas.create_text(
            10, 10,
            anchor="nw",
            text=f"AUDIO: {self.sound.status}",
            fill="#666666",
            font=("Consolas", 11)
        )

        # ----------------------------------------------------
        # KEYBOARD
        # ----------------------------------------------------

        self.root.bind(
            "<Escape>",
            lambda event: self.stop()
        )

    # ========================================================
    # SELEZIONE FONT MONOSPACE
    # ========================================================

    def _pick_monospace_font(self):

        candidates = [
            "Courier New",
            "Courier",
            "Consolas",
            "Menlo",
            "DejaVu Sans Mono",
            "Liberation Mono",
            "Noto Sans Mono",
            "Ubuntu Mono",
            "monospace",
            "TkFixedFont"
        ]

        available = set(tkfont.families(self.root))

        for name in candidates:
            if name in available:
                return name

        # Nessuno dei candidati e' installato: usiamo comunque
        # il font fisso di sistema di Tk, che e' sempre presente
        # ed e' garantito a spaziatura fissa.
        return "TkFixedFont"

    # ========================================================
    # CARTA CONTINUA
    # ========================================================

    def extend_paper(self):

        target = self.text_y + self.screen_height * 1.5

        while self.paper_bottom_y < target:
            self._draw_paper_segment(
                self.paper_bottom_y,
                self.paper_bottom_y + self.screen_height
            )
            self.paper_bottom_y += self.screen_height

    # --------------------------------------------------------

    def _draw_paper_segment(self, y_top, y_bottom):

        tag = f"paper_seg_{self._segment_id}"
        self._segment_id += 1

        # PAPER
        self.canvas.create_rectangle(
            self.paper_margin_x,
            y_top,
            self.screen_width - self.paper_margin_x,
            y_bottom,
            fill=self.paper_color,
            outline="",
            tags=(tag, "papersheet")
        )

        # EDGES
        self.canvas.create_line(
            self.paper_margin_x, y_top,
            self.paper_margin_x, y_bottom,
            fill=self.edge_color,
            tags=(tag, "papersheet")
        )

        self.canvas.create_line(
            self.screen_width - self.paper_margin_x, y_top,
            self.screen_width - self.paper_margin_x, y_bottom,
            fill=self.edge_color,
            tags=(tag, "papersheet")
        )

        # PERFORATION LINES
        self.canvas.create_line(
            self.paper_margin_x + 45, y_top,
            self.paper_margin_x + 45, y_bottom,
            fill=self.edge_color,
            dash=(2, 5),
            tags=(tag, "papersheet")
        )

        self.canvas.create_line(
            self.screen_width - self.paper_margin_x - 45, y_top,
            self.screen_width - self.paper_margin_x - 45, y_bottom,
            fill=self.edge_color,
            dash=(2, 5),
            tags=(tag, "papersheet")
        )

        # TRACTOR HOLES
        hole_radius = 5
        hole_spacing = 18

        hole_x_left = self.paper_margin_x + 27
        hole_x_right = self.screen_width - self.paper_margin_x - 27

        # allinea i fori a una griglia globale (y % spacing == 12)
        # cosi' il pattern resta continuo tra un segmento e l'altro
        y = y_top + ((12 - y_top) % hole_spacing)

        while y < y_bottom:

            self.canvas.create_oval(
                hole_x_left - hole_radius, y - hole_radius,
                hole_x_left + hole_radius, y + hole_radius,
                fill=self.hole_color, outline="",
                tags=(tag, "papersheet")
            )

            self.canvas.create_oval(
                hole_x_right - hole_radius, y - hole_radius,
                hole_x_right + hole_radius, y + hole_radius,
                fill=self.hole_color, outline="",
                tags=(tag, "papersheet")
            )

            y += hole_spacing

        self._segments.append(tag)
        # tieni i tag in ordine per poterli scartare dal fondo
        self.canvas.tag_lower(tag)

    # --------------------------------------------------------

    def cleanup_offscreen_paper(self):

        for tag in list(self._segments):

            bbox = self.canvas.bbox(tag)

            if bbox and bbox[3] < -200:
                self.canvas.delete(tag)
                self._segments.remove(tag)

    # ========================================================
    # PRINT CHARACTER
    # ========================================================

    def print_character(self, char):

        # ----------------------------------------------------
        # BEL — campanello esplicito nel testo (0x07)
        # ----------------------------------------------------

        if char == "\x07":
            self.sound.play("bell")
            return

        # ----------------------------------------------------
        # New line
        # ----------------------------------------------------

        if char == "\n":

            self.sound.play("cr")

            self.text_y += self.line_height

            self.text_x = (
                self.paper_margin_x +
                self.print_margin_left
            )

            self.current_column = 0
            self.bell_rung_this_line = False
            self.last_line_length = 0

            self.extend_paper()
            self.cleanup_offscreen_paper()

            if self.text_y > self.screen_height - 100:
                self.scroll_paper()

            return

        # ----------------------------------------------------
        # Carriage return
        # ----------------------------------------------------

        if char == "\r":
            return

        # ----------------------------------------------------
        # TAB
        # ----------------------------------------------------

        if char == "\t":

            self.text_x += (self.char_width * 4)
            self.current_column += 4

            return

        # ----------------------------------------------------
        # CHARACTER — colpo del martelletto
        # ----------------------------------------------------
        # La testina batte sempre nella stessa posizione: niente
        # jitter di posizione o rotazione, altrimenti la riga
        # perde l'allineamento verticale. La variabilita'
        # meccanica reale sta nel TEMPO tra un colpo e l'altro
        # (gia' gestita in delay()) e nella pressione del
        # martelletto (ink_color_faint con --ribbon-wear).

        fill = self.ink_color

        if self.ribbon_wear and random.random() < 0.03:
            # colpo debole per nastro usurato
            fill = self.ink_color_faint

        self.canvas.create_text(
            self.text_x,
            self.text_y,

            text=char,
            anchor="nw",

            font=self._font,

            fill=fill
        )

        if char != " ":
            self.sound.play("key")

        self.text_x += self.char_width
        self.current_column += 1
        self.last_line_length += 1

        # ----------------------------------------------------
        # CAMPANELLO DI MARGINE (8 colonne prima del limite)
        # ----------------------------------------------------

        if (
            self.margin_bell_enabled and
            not self.bell_rung_this_line and
            self.current_column >= self.margin_bell_column
        ):
            self.sound.play("bell")
            self.bell_rung_this_line = True

        # ----------------------------------------------------
        # LINE WRAP — a colonna fissa, come l'hardware reale
        # ----------------------------------------------------

        if self.current_column >= self.columns:

            self.text_y += self.line_height

            self.text_x = (
                self.paper_margin_x +
                self.print_margin_left
            )

            self.current_column = 0
            self.bell_rung_this_line = False
            self.last_line_length = 0

        # ----------------------------------------------------
        # SCROLL PAPER + ESTENSIONE ROTOLO
        # ----------------------------------------------------

        self.extend_paper()
        self.cleanup_offscreen_paper()

        if self.text_y > self.screen_height - 100:
            self.scroll_paper()

    # ========================================================
    # SCROLL PAPER
    # ========================================================

    def scroll_paper(self):

        amount = self.line_height

        self.canvas.move("all", 0, -amount)

        self.text_y -= amount
        self.paper_bottom_y -= amount

    # ========================================================
    # MECHANICAL DELAY
    # ========================================================

    def delay(self, char):

        delay = 1.0 / self.chars_per_second

        if self.mechanical_jitter:
            delay *= random.uniform(0.75, 1.30)

        time.sleep(delay)

        # Il ritorno carrello di una macchina elettromeccanica
        # non e' istantaneo: piu' lunga era la riga, piu' tempo
        # ci metteva il carrello a tornare a sinistra.
        if char == "\n":
            carriage_time = 0.03 + 0.0025 * self.last_line_length
            time.sleep(min(carriage_time, 0.35))

    # ========================================================
    # PRINTER THREAD
    # ========================================================

    def _printer_thread(self):

        self.running = True

        for char in self.text:

            if not self.running:
                break

            self.root.after(
                0,
                self.print_character,
                char
            )

            self.delay(char)

        self.running = False

    # ========================================================
    # START
    # ========================================================

    def start(self):

        if self.running:
            return

        threading.Thread(
            target=self._printer_thread,
            daemon=True
        ).start()

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        self.running = False
        self.sound.cleanup()
        self.root.destroy()

    # ========================================================
    # RUN
    # ========================================================

    def run(self):

        try:
            self.root.mainloop()
        finally:
            self.sound.cleanup()


# ============================================================
# COMMAND LINE
# ============================================================

def parse_arguments():

    parser = argparse.ArgumentParser(
        description="ASR-33 Teletype Simulator"
    )

    source = parser.add_mutually_exclusive_group(
        required=True
    )

    source.add_argument(
        "-t", "--text",
        help="Testo da stampare"
    )

    source.add_argument(
        "-f", "--file",
        help="File di testo da stampare"
    )

    parser.add_argument(
        "-s", "--speed",
        type=float, default=10,
        help="Caratteri al secondo (default: 10, come l'hardware reale)"
    )

    parser.add_argument(
        "--font-size",
        type=int, default=26,
        help="Dimensione carattere"
    )

    parser.add_argument(
        "--columns",
        type=int, default=72,
        help="Colonne per riga prima del ritorno a capo automatico (default: 72)"
    )

    parser.add_argument(
        "--no-jitter",
        action="store_true",
        help="Disabilita la variazione meccanica di tempo/posizione"
    )

    parser.add_argument(
        "--preserve-case",
        action="store_true",
        help="Mantiene minuscole e accenti (l'ASR-33 reale stampava solo maiuscole)"
    )

    parser.add_argument(
        "--no-sound",
        action="store_true",
        help="Disabilita i suoni meccanici sintetizzati"
    )

    parser.add_argument(
        "--no-margin-bell",
        action="store_true",
        help="Disabilita il campanello di margine (8 colonne prima del limite)"
    )

    parser.add_argument(
        "--ribbon-wear",
        action="store_true",
        help="Simula un nastro inchiostrato usurato con colpi occasionali piu' deboli"
    )

    return parser.parse_args()


# ============================================================
# MAIN
# ============================================================

def main():

    args = parse_arguments()

    # --------------------------------------------------------
    # INPUT
    # --------------------------------------------------------

    if args.text is not None:
        text = args.text
    else:
        text = Path(args.file).read_text(
            encoding="utf-8",
            errors="replace"
        )

    # --------------------------------------------------------
    # ASR-33 HEADER
    # --------------------------------------------------------

    header = "CYENERGY™ CORPORATION // Teletype Model 33 ASR // CONNECTING.......\n\n"

    text = header + text

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    printer = ASR33(
        text=text,
        chars_per_second=args.speed,
        font_size=args.font_size,
        mechanical_jitter=not args.no_jitter,
        columns=args.columns,
        preserve_case=args.preserve_case,
        sound=not args.no_sound,
        margin_bell=not args.no_margin_bell,
        ribbon_wear=args.ribbon_wear
    )

    printer.start()
    printer.run()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()