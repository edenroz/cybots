import argparse
import io
import math
import os
import platform
import queue
import random
import shutil
import struct
import subprocess
import sys
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
    Audio ASR-33 precomputato in un unico WAV per la stampa "batch".

    Il punto importante e' che NON viene avviato un suono per ogni
    carattere in quel caso. Tutti i colpi (key, carriage return, bell)
    vengono posizionati in anticipo sulla stessa timeline usata dalla
    stampa e mixati in un unico file.

    In piu', per la modalita' interattiva (dove il testo non e'
    conosciuto in anticipo) vengono tenuti pronti anche i tre singoli
    campioni ("key", "bell", "cr") come piccoli WAV a se stanti, cosi'
    da poterli riprodurre al volo con play_one_shot().
    """

    SAMPLE_RATE = 44100
    LEAD_IN_SECONDS = 0.12

    def __init__(self, enabled=True):
        self.enabled = enabled
        self._raw_samples = {}
        self._event_wav_bytes = {}
        self._event_wav_paths = {}
        self._wav_bytes = None
        self._full_pcm_bytes = None
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

        # Piccoli WAV singoli pronti all'uso per la riproduzione
        # immediata (modalita' interattiva).
        for name, samples in self._raw_samples.items():
            pcm = self._encode_pcm16(samples)
            self._event_wav_bytes[name] = self._write_wav_bytes(pcm)

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

    def _encode_pcm16(self, samples):
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

        pcm = self._encode_pcm16(mix)

        self._full_pcm_bytes = pcm
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
        # Prefer simpleaudio because it can play il flusso PCM completo
        # dalla memoria con una singola richiesta di playback.
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
        if not self.enabled:
            return False

        self._backend = self._setup_backend()

        if self._backend is None:
            print(
                "[ASR33 AUDIO] Nessun backend audio disponibile. "
                "Installa 'simpleaudio' con: pip install simpleaudio"
            )
            return False

        # winsound ed external non sanno riprodurre bytes in memoria:
        # servono dei piccoli file temporanei per i suoni singoli usati
        # dalla riproduzione immediata (play_one_shot).
        if self._backend in ("winsound", "external"):
            for name, wav_bytes in self._event_wav_bytes.items():
                fd, path = tempfile.mkstemp(
                    prefix=f"asr33_{name}_",
                    suffix=".wav",
                )
                os.close(fd)
                Path(path).write_bytes(wav_bytes)
                self._event_wav_paths[name] = path

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
        Avvia UNA SOLA riproduzione dell'intero WAV precomputato
        (modalita' batch, con testo/timeline noti in anticipo).
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
                    self._full_pcm_bytes,
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

    def play_one_shot(self, name):
        """
        Riproduce immediatamente un singolo suono ("key", "bell" o "cr").
        Usato dalla modalita' interattiva, dove il testo non e' noto in
        anticipo e quindi non esiste un'unica timeline precomputata.

        NB: rispetto alla riproduzione batch questa via reintroduce una
        piccola latenza per-carattere (soprattutto sui backend winsound
        ed external), che nella modalita' batch era stata volutamente
        eliminata. E' il compromesso necessario per stampare dal vivo
        testo che non si conosce in anticipo.
        """
        if not self.enabled or self._backend is None:
            return

        try:
            path = self._event_wav_paths.get(name)
            if not path:
                return

            if self._backend == "winsound":
                self._winsound.PlaySound(
                    path,
                    self._winsound.SND_FILENAME
                    | self._winsound.SND_ASYNC,
                )
                return

            if self._backend == "external":
                if self._external_player and os.path.basename(self._external_player) == "ffplay":
                    command = [
                        self._external_player,
                        "-nodisp",
                        "-autoexit",
                        "-loglevel",
                        "quiet",
                        path,
                    ]
                else:
                    command = [self._external_player, path]

                subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

        except Exception as e:
            print(f"[ASR33 AUDIO] Errore playback immediato: {e}")

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

        for path in self._event_wav_paths.values():
            if path.startswith(tempfile.gettempdir()) and os.path.isfile(path):
                try:
                    os.remove(path)
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
        columns=49,
        preserve_case=False,
        sound=True,
        ribbon_wear=False,
        margin_bell=True,
        audio_file="asr33_output.wav",
        interactive=False,
        save_png_on_finish=True,
        png_path=None,
    ):
        self.text = to_asr33_charset(text, preserve_case=preserve_case)
        self.chars_per_second = chars_per_second
        self.font_size = font_size
        self.mechanical_jitter = mechanical_jitter
        self.columns = max(10, columns)
        self.ribbon_wear = True
        self.margin_bell_enabled = margin_bell
        self.margin_bell_column = max(1, self.columns - 8)

        self.running = False
        self.current_column = 0
        self.bell_rung_this_line = False
        self.last_line_length = 0

        self.interactive = interactive
        self._preserve_case_flag = preserve_case
        self._save_png_on_finish = True
        self._png_path = png_path
        self._live_queue = queue.Queue()
        self._live_after_id = None
        self._watchdog_after_id = None

        self.sound = MechanicalSound(enabled=sound)
        self.audio_file = audio_file
        self._visual_events = []
        self._audio_events = []
        self._timeline_duration = 0.0
        self._timeline_index = 0
        self._timeline_start = None
        self._after_id = None

        # In modalita' interattiva il testo completo non e' noto in
        # anticipo, quindi non si puo' costruire un'unica timeline/WAV:
        # il backend audio viene comunque preparato per la riproduzione
        # "a colpo singolo" (play_one_shot).
        if sound and not interactive:
            self._build_timeline()
            self.sound.build_audio(
                self._audio_events,
                self._timeline_duration,
                output_path=self.audio_file,
            )

        if sound:
            self.sound.prepare()

        # ----------------------------------------------------
        # WINDOW
        # ----------------------------------------------------

        self.root = tk.Tk()

        #self.root.title("CYENERGY™ CORPORATION // MODEL 33 ASR")

        # ----------------------------------------------------
        # MONITOR
        # ----------------------------------------------------
        # BUGFIX: il monitor va rilevato e la finestra posizionata PRIMA
        # di attivare il fullscreen. Il fullscreen "vero" del sistema
        # operativo si aggancia al monitor su cui la finestra si trova
        # nel momento in cui viene attivato — che di default e' sempre
        # il monitor primario, dato che e' li' che Tk crea la finestra.
        # Se prima si attiva il fullscreen e solo dopo si sposta la
        # finestra col monitor giusto, su Windows la stampa resta
        # comunque sul monitor primario (e in piu' Windows puo'
        # minimizzare automaticamente le app in fullscreen esclusivo
        # quando la configurazione dei monitor cambia, es. collegandone
        # uno nuovo — dando l'impressione che la finestra "si chiuda").

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

        print(
            f"[ASR33 DEBUG] Monitor rilevati: {len(monitors)} -> "
            + ", ".join(
                f"[{i}] {m.width}x{m.height}+{m.x}+{m.y}"
                for i, m in enumerate(monitors)
            )
            if monitors
            else "[ASR33 DEBUG] Nessun monitor rilevato da screeninfo"
        )
        print(
            f"[ASR33 DEBUG] Monitor scelto: "
            f"{monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}"
        )

        self.root.geometry(
            f"{monitor.width}x{monitor.height}"
            f"+{monitor.x}+{monitor.y}"
        )

        self.screen_width = monitor.width
        self.screen_height = monitor.height

        # ----------------------------------------------------
        # FULLSCREEN / BORDERLESS
        # ----------------------------------------------------
        # Su Windows e Linux non serve il fullscreen "vero" del sistema:
        # la finestra e' gia' senza bordi (overrideredirect) e ha
        # esattamente le dimensioni del monitor scelto, quindi appare
        # comunque a schermo intero senza gli effetti collaterali del
        # vero fullscreen esclusivo (minimizzazione automatica al
        # cambio di configurazione monitor, aggancio al monitor
        # primario, ecc).
        #
        # Su macOS, invece, l'overrideredirect e' saltato perche' quelle
        # finestre spesso non ricevono correttamente il focus tastiera
        # dal window manager nativo: qui serve il fullscreen "vero",
        # ma solo ORA che la finestra e' gia' posizionata sul monitor
        # corretto, cosi' il sistema la rende fullscreen su quello e
        # non sul primario.

        self._use_overrideredirect = platform.system() != "Darwin"

        if self._use_overrideredirect:
            self.root.overrideredirect(True)
        else:
            self.root.attributes("-fullscreen", True)

        # BUGFIX: senza "topmost" la finestra (essendo priva di bordi e
        # assente da taskbar/Alt-Tab) puo' finire coperta da un'altra
        # finestra non appena l'attivita' di stampa si ferma, dando
        # l'impressione che si sia chiusa da sola mentre in realta' e'
        # ancora aperta ma irraggiungibile con ESC perche' non ha piu'
        # il focus tastiera. La riaffermiamo anche periodicamente con un
        # "watchdog" piu' sotto, perche' alcuni window manager/compositor
        # possono farla scendere di piano col tempo comunque.
        self.root.attributes("-topmost", True)

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

        self.print_margin_left = 55
        self.print_margin_right = 55

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
        # Rilegato anche sul canvas: alcune combinazioni di window
        # manager/piattaforma spostano il focus tastiera sul widget
        # figlio invece che sulla finestra root.
        self.canvas.bind(
            "<Escape>",
            lambda event: self.stop()
        )

        # Esportazione PNG on-demand con un tasto rapido.
        self.root.bind("<KeyPress-p>", lambda event: self.save_png())
        self.root.bind("<KeyPress-P>", lambda event: self.save_png())

        # BUGFIX: forza focus e "lift" poco dopo la creazione della
        # finestra, cosi' che ESC funzioni davvero da subito e la
        # finestra non resti nascosta dietro al terminale da cui e'
        # stata lanciata.
        self.root.after(50, self._claim_focus)

        # Diagnostica: se la finestra dovesse ancora "sparire" da sola,
        # questi messaggi in console dicono se e' stata nascosta
        # (Unmap), ha solo perso il focus, oppure e' stata davvero
        # distrutta — informazione preziosa per capire la vera causa.
        self.root.bind("<Unmap>", self._on_debug_unmap)
        self.root.bind(
            "<Map>",
            lambda event: print("[ASR33 DEBUG] Finestra visibile (Map)")
        )
        self.root.bind(
            "<FocusOut>",
            lambda event: print("[ASR33 DEBUG] Focus tastiera perso")
        )
        self.root.bind(
            "<FocusIn>",
            lambda event: print("[ASR33 DEBUG] Focus tastiera riacquisito")
        )
        self.root.bind(
            "<Destroy>",
            lambda event: print("[ASR33 DEBUG] Finestra distrutta")
        )

        # Watchdog: riafferma periodicamente piano/topmost/focus per
        # tutta la durata dell'esecuzione, non solo all'avvio — cosi'
        # se qualcosa la fa scendere di piano col tempo viene rimessa
        # a posto in continuazione, non solo nei primi 50ms.
        self._watchdog_after_id = self.root.after(500, self._watchdog)

        print(
            "[ASR33] Finestra pronta sul monitor selezionato. "
            "Premi ESC in qualsiasi momento per uscire "
            "(resta aperta anche a fine stampa)."
        )

    # ========================================================
    # FOCUS / VISIBILITA'
    # ========================================================

    def _claim_focus(self):
        try:
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.focus_force()
        except Exception:
            pass

    def _on_debug_unmap(self, event):
        print(
            "[ASR33 DEBUG] Finestra nascosta (Unmap) - "
            "provo a riportarla in primo piano"
        )
        self._claim_focus()

    def _watchdog(self):
        try:
            self._claim_focus()
            self._watchdog_after_id = self.root.after(500, self._watchdog)
        except Exception:
            pass

    # ========================================================
    # EXPORT PNG
    # ========================================================
    def save_png(self, path=None):
        """
        Salva il contenuto reale della finestra Tkinter in PNG.
        Su Windows usa PrintWindow, che è molto più affidabile di
        ImageGrab per finestre Tkinter borderless/overrideredirect.
        """
        try:
            from PIL import Image
        except ImportError:
            print(
                "[ASR33] Per esportare in PNG serve Pillow: "
                "pip install pillow"
            )
            return None

        if path is None:
            path = f"asr33_snapshot_{time.strftime('%Y%m%d_%H%M%S')}.png"

        try:
            self.root.update()
            self.root.update_idletasks()

            x = self.root.winfo_rootx()
            y = self.root.winfo_rooty()
            w = self.root.winfo_width()
            h = self.root.winfo_height()

            if w <= 0 or h <= 0:
                print("[ASR33] Dimensioni finestra non valide")
                return None

            if platform.system() == "Windows":
                import ctypes
                from ctypes import wintypes

                hwnd = self.root.winfo_id()

                # DC della finestra
                hwndDC = ctypes.windll.user32.GetWindowDC(hwnd)

                # DC compatibile in memoria
                mfcDC = ctypes.windll.gdi32.CreateCompatibleDC(hwndDC)

                # Bitmap compatibile
                saveBitMap = ctypes.windll.gdi32.CreateCompatibleBitmap(
                    hwndDC,
                    w,
                    h
                )

                ctypes.windll.gdi32.SelectObject(
                    mfcDC,
                    saveBitMap
                )

                # PW_RENDERFULLCONTENT = 0x00000002
                result = ctypes.windll.user32.PrintWindow(
                    hwnd,
                    mfcDC,
                    0x00000002
                )

                if result == 0:
                    print("[ASR33] PrintWindow ha fallito")
                    return None

                # BITMAPINFO
                class BITMAPINFOHEADER(ctypes.Structure):
                    _fields_ = [
                        ("biSize", wintypes.DWORD),
                        ("biWidth", wintypes.LONG),
                        ("biHeight", wintypes.LONG),
                        ("biPlanes", wintypes.WORD),
                        ("biBitCount", wintypes.WORD),
                        ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD),
                        ("biXPelsPerMeter", wintypes.LONG),
                        ("biYPelsPerMeter", wintypes.LONG),
                        ("biClrUsed", wintypes.DWORD),
                        ("biClrImportant", wintypes.DWORD),
                    ]

                class BITMAPINFO(ctypes.Structure):
                    _fields_ = [
                        ("bmiHeader", BITMAPINFOHEADER),
                        ("bmiColors", wintypes.DWORD * 3),
                    ]

                bmi = BITMAPINFO()
                bmi.bmiHeader.biSize = ctypes.sizeof(
                    BITMAPINFOHEADER
                )
                bmi.bmiHeader.biWidth = w
                bmi.bmiHeader.biHeight = -h
                bmi.bmiHeader.biPlanes = 1
                bmi.bmiHeader.biBitCount = 32
                bmi.bmiHeader.biCompression = 0

                buffer_size = w * h * 4
                buffer = ctypes.create_string_buffer(buffer_size)

                ctypes.windll.gdi32.GetDIBits(
                    mfcDC,
                    saveBitMap,
                    0,
                    h,
                    buffer,
                    ctypes.byref(bmi),
                    0
                )

                image = Image.frombuffer(
                    "RGBA",
                    (w, h),
                    buffer,
                    "raw",
                    "BGRA",
                    0,
                    1
                )

                image.save(path)

                # Cleanup GDI
                ctypes.windll.gdi32.DeleteObject(saveBitMap)
                ctypes.windll.gdi32.DeleteDC(mfcDC)
                ctypes.windll.user32.ReleaseDC(hwnd, hwndDC)

                print(f"[ASR33] PNG salvato: {path}")
                return path

            else:
                # Fallback per Linux/macOS
                from PIL import ImageGrab

                image = ImageGrab.grab(
                    bbox=(x, y, x + w, y + h)
                )

                image.save(path)

                print(f"[ASR33] PNG salvato: {path}")
                return path

        except Exception as e:
            print(
                f"[ASR33] Errore salvataggio PNG: "
                f"{type(e).__name__}: {e}"
            )
            return None
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
            jitter_dx = random.uniform(-1.0, 1.0)
            jitter_dy = random.uniform(-0.4, 0.4)
            angle = random.uniform(-2.0, 2.0)

        if self.ribbon_wear and random.random() < 0.15:
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

            font=("Courier New", self.font_size, "bold"),

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
    # PRECOMPUTED TIMELINE (modalita' batch)
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
    # TIMELINE SCHEDULER (modalita' batch)
    # ========================================================

    def _schedule_next(self):
        if not self.running:
            return

        if self._timeline_index >= len(self._visual_events):
            self.running = False
            print(
                "[ASR33] Stampa terminata. "
                "La finestra resta aperta: premi ESC per uscire."
            )

            self._claim_focus()

            if self._save_png_on_finish:
                self.save_png(self._png_path)

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
            print(
                "[ASR33] Stampa terminata. "
                "La finestra resta aperta: premi ESC per uscire."
            )
            self._claim_focus()

            if self._save_png_on_finish:
                self.save_png(self._png_path)

            return

        _, char = self._visual_events[self._timeline_index]
        self._timeline_index += 1

        self.print_character(char)
        self._schedule_next()

    # ========================================================
    # MODALITA' INTERATTIVA
    # ========================================================
    # A differenza della modalita' batch, qui il testo non e'
    # conosciuto in anticipo: un thread separato legge righe da
    # stdin e le accoda; un ciclo "after()" nel thread principale
    # (obbligatorio per toccare la GUI Tk) consuma la coda al
    # ritmo di chars_per_second, come farebbe una vera telescrivente
    # con qualcuno che digita dal vivo.

    def _start_interactive(self):
        for ch in self.text:
            self._live_queue.put(ch)

        thread = threading.Thread(
            target=self._read_stdin_loop,
            daemon=True,
        )
        thread.start()

        self._consume_live_queue()

    def _read_stdin_loop(self):
        print(
            "[ASR33] Modalita' interattiva attiva: scrivi una riga e "
            "premi Invio.\n"
            "         Ctrl+D (Ctrl+Z su Windows) per chiudere l'input "
            "da terminale."
        )
        try:
            for line in sys.stdin:
                line = to_asr33_charset(
                    line,
                    preserve_case=self._preserve_case_flag,
                )
                for ch in line:
                    self._live_queue.put(ch)

                if not line.endswith("\n"):
                    self._live_queue.put("\n")
        except Exception:
            pass

    def _consume_live_queue(self):
        if not self.running:
            return

        delay_ms = 40  # ritmo di polling quando la coda e' vuota

        try:
            char = self._live_queue.get_nowait()
            self.print_character(char)

            if self.sound.enabled and char == "\n":
                self.sound.play_one_shot("cr")
            elif self.sound.enabled and char not in ("\r", "\t", " ", "\x07"):
                self.sound.play_one_shot("key")

            delay_ms = int(self._next_delay() * 1000)

        except queue.Empty:
            pass

        self._live_after_id = self.root.after(
            delay_ms,
            self._consume_live_queue,
        )

    # ========================================================
    # START
    # ========================================================

    def start(self):
        if self.running:
            return

        self.running = True

        if self.interactive:
            self._start_interactive()
            return

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

        if self._live_after_id is not None:
            try:
                self.root.after_cancel(self._live_after_id)
            except Exception:
                pass
            self._live_after_id = None

        if self._watchdog_after_id is not None:
            try:
                self.root.after_cancel(self._watchdog_after_id)
            except Exception:
                pass
            self._watchdog_after_id = None

        self.sound.cleanup()
        self.root.destroy()

    # ========================================================
    # RUN
    # ========================================================

    def run(self):

        try:
            self.root.mainloop()
        except Exception as e:
            # Se il mainloop si interrompe per un'eccezione (invece che
            # per un destroy() volontario da ESC), lo stampiamo: e' la
            # prova che qualcosa di diverso da ESC ha chiuso la finestra.
            print(f"[ASR33 DEBUG] mainloop interrotto da un'eccezione: {e}")
        finally:
            print("[ASR33 DEBUG] mainloop concluso")
            self.sound.cleanup()


# ============================================================
# COMMAND LINE
# ============================================================

def parse_arguments():

    parser = argparse.ArgumentParser(
        description="ASR-33 Teletype Simulator"
    )

    source = parser.add_mutually_exclusive_group(
        required=False
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
        "--interactive",
        action="store_true",
        help=(
            "Modalita' interattiva: stampa dal vivo cio' che scrivi da "
            "terminale (non richiede -t/-f)"
        )
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
        type=int, default=49,
        help="Colonne per riga prima del ritorno a capo automatico (default: 49) per lo schermo verticale"
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

    parser.add_argument(
        "--save-png",
        action="store_true",
        help="Salva automaticamente uno screenshot PNG della carta a fine stampa"
    )

    parser.add_argument(
        "--png-file",
        default=None,
        help=(
            "Percorso del file PNG da salvare (usato con --save-png "
            "e/o con il tasto rapido P durante l'esecuzione)"
        )
    )

    args = parser.parse_args()

    if not args.interactive and not args.text and not args.file:
        parser.error(
            "specifica -t/--text, -f/--file oppure --interactive"
        )

    if args.interactive and (args.text or args.file):
        parser.error(
            "--interactive non si puo' combinare con -t/--text o -f/--file"
        )

    return args


# ============================================================
# MAIN
# ============================================================

def main():

    args = parse_arguments()

    # --------------------------------------------------------
    # ASR-33 HEADER
    # --------------------------------------------------------

    header = "// CY_Sanitation™ // Teletype Model 33 ASR\n// CONNECTING.......\n\n"

    # --------------------------------------------------------
    # INPUT
    # --------------------------------------------------------

    if args.interactive:
        # In interattivo si stampa subito l'header, il resto arriva
        # dal vivo da stdin.
        text = header
    else:
        if args.text is not None:
            text = args.text
        else:
            text = Path(args.file).read_text(
                encoding="utf-8",
                errors="replace"
            )

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
        audio_file=args.audio_file,
        interactive=args.interactive,
        save_png_on_finish=args.save_png,
        png_path=args.png_file,
    )

    printer.start()
    printer.run()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()