import argparse
import io
import math
import os
import platform
import random
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import tkinter as tk
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
    Audio ASR-33 precomputato in un unico WAV.

    Il punto importante e' che NON viene piu' avviato un suono per ogni
    carattere. Tutti i colpi (key, carriage return, bell) vengono
    posizionati in anticipo sulla stessa timeline usata dalla stampa.

    In questo modo Windows deve aprire/riprodurre un solo stream audio,
    eliminando la latenza variabile di winsound.PlaySound()/processi
    avviati carattere per carattere.
    """

    SAMPLE_RATE = 44100
    LEAD_IN_SECONDS = 0.12

    def __init__(self, enabled=True):
        self.enabled = enabled
        self._raw_samples = {}
        self._wav_bytes = None
        self._pcm_bytes = None
        self._wav_path = None
        self._play_object = None
        self._backend = None
        self._external_player = None

        if not self.enabled:
            return

        self._raw_samples = {
            "key": self._render_click(),
            "bell": self._render_bell(),
            "cr": self._render_carriage(),
        }

    # --------------------------------------------------------
    # SYNTH
    # --------------------------------------------------------

    def _envelope(self, n, attack=0.05, decay=1.0):
        env = []
        a = max(1, int(n * attack))

        for i in range(n):
            if i < a:
                env.append(i / a)
            else:
                env.append(
                    math.exp(
                        -decay * (i - a) / n * 8
                    )
                )

        return env

    def _render_click(self):
        n = int(self.SAMPLE_RATE * 0.018)
        env = self._envelope(n, attack=0.03, decay=1.6)

        samples = []
        for i in range(n):
            value = (
                random.uniform(-1, 1) * 0.6
                + math.sin(
                    2 * math.pi * 1800 * i / self.SAMPLE_RATE
                ) * 0.4
            )
            samples.append(value * env[i] * 14000)

        return samples

    def _render_bell(self):
        n = int(self.SAMPLE_RATE * 0.35)
        env = self._envelope(n, attack=0.01, decay=2.5)

        samples = []
        for i in range(n):
            value = (
                math.sin(
                    2 * math.pi * 2100 * i / self.SAMPLE_RATE
                )
                + 0.35
                * math.sin(
                    2 * math.pi * 2800 * i / self.SAMPLE_RATE
                )
            )
            samples.append(value * env[i] * 9000)

        return samples

    def _render_carriage(self):
        n = int(self.SAMPLE_RATE * 0.09)
        env = self._envelope(n, attack=0.05, decay=1.1)

        samples = []
        for i in range(n):
            value = (
                random.uniform(-1, 1) * 0.5
                + math.sin(
                    2 * math.pi * 250 * i / self.SAMPLE_RATE
                ) * 0.5
            )
            samples.append(value * env[i] * 15000)

        return samples

    # --------------------------------------------------------
    # WAV
    # --------------------------------------------------------

    def _pcm_bytes(self, samples):
        return b"".join(
            struct.pack(
                "<h",
                max(-32768, min(32767, int(sample)))
            )
            for sample in samples
        )

    def _write_wav_bytes(self, pcm):
        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(self.SAMPLE_RATE)
            f.writeframes(pcm)

        return buffer.getvalue()

    def build_audio(
        self,
        events,
        duration_seconds,
        output_path=None,
    ):
        """
        events = [(time_seconds, sound_name), ...]

        La timeline audio contiene un piccolo lead-in iniziale. Gli eventi
        restano quindi collocati sullo stesso asse temporale della grafica.
        """
        if not self.enabled:
            return 0.0

        duration_seconds = max(
            duration_seconds,
            self.LEAD_IN_SECONDS
        )

        total_samples = (
            int(
                (duration_seconds + self.LEAD_IN_SECONDS + 0.5)
                * self.SAMPLE_RATE
            )
        )

        mix = [0.0] * total_samples

        for event_time, sound_name in events:
            samples = self._raw_samples.get(sound_name)
            if not samples:
                continue

            start_index = int(
                (self.LEAD_IN_SECONDS + event_time)
                * self.SAMPLE_RATE
            )

            if start_index >= total_samples:
                continue

            max_len = min(
                len(samples),
                total_samples - start_index
            )

            for i in range(max_len):
                mix[start_index + i] += samples[i]

        pcm = b"".join(
            struct.pack(
                "<h",
                max(
                    -32768,
                    min(32767, int(sample))
                )
            )
            for sample in mix
        )

        self._pcm_bytes = pcm
        self._wav_bytes = self._write_wav_bytes(pcm)

        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self._wav_bytes)
            self._wav_path = str(path)

        return duration_seconds + self.LEAD_IN_SECONDS

    # --------------------------------------------------------
    # PLAYBACK
    # --------------------------------------------------------

    def _setup_backend(self):
        # Prefer simpleaudio because it can play the complete precomputed
        # PCM stream from memory with one single playback request.
        try:
            import simpleaudio as sa

            self._sa = sa
            return "simpleaudio"
        except Exception:
            pass

        if platform.system() == "Windows":
            try:
                import winsound

                self._winsound = winsound
                return "winsound"
            except Exception:
                pass

        player = (
            shutil.which("afplay")
            if platform.system() == "Darwin"
            else (
                shutil.which("paplay")
                or shutil.which("aplay")
                or shutil.which("ffplay")
            )
        )

        if player:
            self._external_player = player
            return "external"

        return None

    def prepare(self):
        if not self.enabled or self._wav_bytes is None:
            return False

        self._backend = self._setup_backend()

        if self._backend is None:
            print(
                "[ASR33 AUDIO] Nessun backend audio disponibile. "
                "Installa 'simpleaudio' con: pip install simpleaudio"
            )
            return False

        print(
            f"[ASR33 AUDIO] Backend: {self._backend}"
            + (
                f" | WAV: {self._wav_path}"
                if self._wav_path
                else ""
            )
        )
        return True

    def play(self):
        """
        Avvia UNA SOLA riproduzione dell'intero WAV precomputato.
        Restituisce immediatamente il riferimento/handle del playback.
        """
        if (
            not self.enabled
            or self._wav_bytes is None
            or self._backend is None
        ):
            return

        try:
            if self._backend == "simpleaudio":
                wave_obj = self._sa.WaveObject(
                    self._pcm_bytes,
                    1,
                    2,
                    self.SAMPLE_RATE,
                )

                # L'header WAV viene saltato: WaveObject vuole il PCM puro.
                self._play_object = wave_obj.play()
                return

            if self._backend == "winsound":
                # Qui passiamo il WAV precomputato COMPLETO.
                # Nessun accesso a disco se _wav_bytes e' disponibile.
                # Un'unica riproduzione asincrona del WAV gia' pronto.
                # SND_MEMORY + SND_ASYNC non e' supportato in modo
                # affidabile da Windows, quindi usiamo il file precomputato.
                self._winsound.PlaySound(
                    self._wav_path,
                    self._winsound.SND_FILENAME
                    | self._winsound.SND_ASYNC,
                )
                return

            if self._backend == "external":
                if not self._wav_path:
                    fd, path = tempfile.mkstemp(
                        prefix="asr33_",
                        suffix=".wav",
                    )
                    os.close(fd)
                    Path(path).write_bytes(self._wav_bytes)
                    self._wav_path = path

                if self._external_player and os.path.basename(self._external_player) == "ffplay":
                    command = [
                        self._external_player,
                        "-nodisp",
                        "-autoexit",
                        "-loglevel",
                        "quiet",
                        self._wav_path,
                    ]
                else:
                    command = [self._external_player, self._wav_path]

                subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

        except Exception as e:
            print(f"[ASR33 AUDIO] Errore playback: {e}")

    def cleanup(self):
        if self._play_object is not None:
            try:
                self._play_object.stop()
            except Exception:
                pass

        if (
            self._wav_path
            and self._wav_path.startswith(tempfile.gettempdir())
            and os.path.isfile(self._wav_path)
        ):
            try:
                os.remove(self._wav_path)
            except OSError:
                pass


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
        margin_bell=True,
        audio_file="asr33_output.wav"
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
        self.audio_file = audio_file
        self._visual_events = []
        self._audio_events = []
        self._timeline_duration = 0.0
        self._timeline_index = 0
        self._timeline_start = None
        self._after_id = None

        if sound:
            self._build_timeline()
            self.sound.build_audio(
                self._audio_events,
                self._timeline_duration,
                output_path=self.audio_file,
            )
            self.sound.prepare()

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

        self.line_height = int(
            self.font_size * 1.45
        )

        self.char_width = int(
            self.font_size * 0.65
        )

        # Larghezza utile in pixel disponibile per il testo,
        # coerente con il numero di colonne richiesto: se le
        # colonne "vincono" prima del margine fisico va bene,
        # e' cosi' che si comportava anche l'hardware reale.
        self.usable_width_px = self.screen_width - (
            self.paper_margin_x * 2 +
            self.print_margin_left +
            self.print_margin_right
        )

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
        # KEYBOARD
        # ----------------------------------------------------

        self.root.bind(
            "<Escape>",
            lambda event: self.stop()
        )

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
            return

        # ----------------------------------------------------
        # New line
        # ----------------------------------------------------

        if char == "\n":

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

        jitter_dx = 0
        jitter_dy = 0
        angle = 0
        fill = self.ink_color

        if self.mechanical_jitter:
            jitter_dx = random.uniform(-1.2, 1.2)
            jitter_dy = random.uniform(-0.4, 0.4)
            angle = random.uniform(-2.0, 2.0)

        if self.ribbon_wear and random.random() < 0.03:
            # colpo debole per nastro usurato
            fill = self.ink_color_faint

        # Il suono viene avviato PRIMA del disegno: con il
        # backend in memoria (simpleaudio/winsound) la differenza
        # e' impercettibile, ma con l'eventuale fallback esterno
        # da' al martelletto un margine per compensare la latenza
        # di avvio del processo, invece di sentirsi in ritardo.
        self.canvas.create_text(
            self.text_x + jitter_dx,
            self.text_y + jitter_dy,

            text=char,
            anchor="nw",
            angle=angle,

            font=("Courier New", self.font_size),

            fill=fill
        )

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
    # PRECOMPUTED TIMELINE
    # ========================================================

    def _next_delay(self):
        delay = 1.0 / self.chars_per_second

        if self.mechanical_jitter:
            delay *= random.uniform(0.75, 1.30)

        return delay

    def _build_timeline(self):
        """
        Costruisce prima l'intera timeline della stampa.

        Ogni elemento visuale ha un timestamp assoluto.
        I suoni vengono inseriti sulla stessa timeline e poi
        renderizzati in un unico WAV.
        """
        self._visual_events = []
        self._audio_events = []

        t = 0.0
        current_column = 0
        last_line_length = 0
        bell_rung = False

        for char in self.text:
            self._visual_events.append((t, char))

            if char == "\x07":
                self._audio_events.append((t, "bell"))

            elif char == "\n":
                self._audio_events.append((t, "cr"))

                t += self._next_delay()

                carriage_time = (
                    0.03
                    + 0.0025 * last_line_length
                )
                t += min(carriage_time, 0.35)

                current_column = 0
                bell_rung = False
                last_line_length = 0

                continue

            elif char == "\r":
                t += self._next_delay()
                continue

            elif char == "\t":
                current_column += 4
                t += self._next_delay()
                continue

            else:
                if char != " ":
                    self._audio_events.append((t, "key"))

                current_column += 1
                last_line_length += 1

                if (
                    self.margin_bell_enabled
                    and not bell_rung
                    and current_column >= self.margin_bell_column
                ):
                    self._audio_events.append((t, "bell"))
                    bell_rung = True

                if current_column >= self.columns:
                    current_column = 0
                    bell_rung = False
                    last_line_length = 0

                t += self._next_delay()

        self._timeline_duration = t

    # ========================================================
    # TIMELINE SCHEDULER
    # ========================================================

    def _schedule_next(self):
        if not self.running:
            return

        if self._timeline_index >= len(self._visual_events):
            self.running = False
            return

        event_time, char = self._visual_events[self._timeline_index]

        target = (
            self._timeline_start
            + self.sound.LEAD_IN_SECONDS
            + event_time
        )

        now = time.perf_counter()
        delay_ms = max(
            0,
            int((target - now) * 1000)
        )

        self._after_id = self.root.after(
            delay_ms,
            self._emit_scheduled_character,
        )

    def _emit_scheduled_character(self):
        if not self.running:
            return

        if self._timeline_index >= len(self._visual_events):
            self.running = False
            return

        _, char = self._visual_events[self._timeline_index]
        self._timeline_index += 1

        self.print_character(char)
        self._schedule_next()

    # ========================================================
    # START
    # ========================================================

    def start(self):
        if self.running:
            return

        self.running = True
        self._timeline_index = 0

        # Avviamo prima l'unico stream audio e prendiamo subito dopo
        # il riferimento temporale. Il lead-in nel WAV assorbe la
        # piccola latenza di apertura del dispositivo audio.
        if self.sound.enabled:
            self.sound.play()

        self._timeline_start = time.perf_counter()
        self._schedule_next()

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        self.running = False

        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

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
        type=float, default=15,
        help="Caratteri al secondo (default: 15, 10 l'hardware reale)"
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
        "--audio-file",
        default="asr33_output.wav",
        help="Percorso del WAV precomputato (default: asr33_output.wav)"
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
        ribbon_wear=args.ribbon_wear,
        audio_file=args.audio_file
    )

    printer.start()
    printer.run()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()