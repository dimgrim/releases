import os, glob, wave, threading, time, math, random
import tkinter as tk
from tkinter import ttk
import pyaudio
import numpy as np

SOUNDS_DIR = "./sounds"
DEFAULT_NOTE_FOLDER_NAME = 'piano '
NOTE_FOLDER = os.path.join(SOUNDS_DIR, DEFAULT_NOTE_FOLDER_NAME)
RUN_DURATION = 1000.0  # seconds
WIDTH, HEIGHT = 1200, 600
BASE_BALL_RADIUS = 26
BALL_RADIUS = BASE_BALL_RADIUS
BALL_COLOURS = ['blue', 'yellow', 'red', 'pink', 'violet', 'cyan']
BACKGROUND_COLOURS = ['black', 'lightblue', 'blue', 'orange']
BALLQUANTITY = ['1','2','3','4','5','6']
OCTAVE_SELECTION = [2,4,5,6,7,8]  # pre-assign octave preferences for each ball index
HARMONIC_BALLS = [False, False, False, True, True, True]  # which balls are harmonic (play root note on collision)  
BASS_OCTAVE = 2

CHROMATIC = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']
SCALES = {
    "Major": [0,2,4,5,7,9,11],
    "Minor": [0,2,3,5,7,8,10],
    "Pentatonic": [0,2,4,7,9],
    "Minor Pentatonic": [0,3,5,7,10],
    "Chromatic": list(range(12)),
    "Dorian": [0,2,3,5,7,9,10],
    "Phrygian": [0,1,3,5,7,8,10],
    "Lydian": [0,2,4,6,7,9,11],
    "Mixolydian": [0,2,4,5,7,9,10],
    "Locrian": [0,1,3,5,6,8,10],
    "Harmonic Minor": [0,2,3,5,7,8,11],
    "Melodic Minor (Jazz)": [0,2,3,5,7,9,11],
    # "Hungarian Minor": [0,2,3,6,7,8,11],
    # "Phrygian Dominant": [0,1,4,5,7,8,10],
    # "Blues": [0,3,5,6,7,10],
    # "Whole Tone": [0,2,4,6,8,10],
    # "Diminished (Octatonic)": [0,2,3,5,6,8,9,11]
}


# list subfolders in Downloads for the folder selection dropdown
try:
    DOWNLOAD_SUBFOLDERS = [d for d in os.listdir(SOUNDS_DIR) if os.path.isdir(os.path.join(SOUNDS_DIR, d))]
except Exception:
    DOWNLOAD_SUBFOLDERS = [DEFAULT_NOTE_FOLDER_NAME]
# ensure default appears first
if DEFAULT_NOTE_FOLDER_NAME not in DOWNLOAD_SUBFOLDERS:
    DOWNLOAD_SUBFOLDERS.insert(0, DEFAULT_NOTE_FOLDER_NAME)

def load_note_files(folder):
    files = glob.glob(os.path.join(folder, "*.wav"))
    note_map = {}
    for f in files:
        name = os.path.basename(f)
        parts = name.split('.')
        # Expect format like Piano.ff.C4.wav -> token at parts[2], but be robust:
        token = None
        if len(parts) >= 3:
            token = parts[2]
        else:
            token = os.path.splitext(name)[0]
        note_map[token] = f
    return note_map

NOTE_FILES = load_note_files(NOTE_FOLDER)
PA = pyaudio.PyAudio()

BACKGROUND_FOLDER = os.path.join(SOUNDS_DIR, 'background')

def load_background_files(folder):
    try:
        files = glob.glob(os.path.join(folder, "*.wav"))
    except Exception:
        files = []
    # return list of basenames mapped to full path
    bg_map = {}
    for f in files:
        name = os.path.basename(f)
        bg_map[name] = f
    return bg_map

BACKGROUND_FILES = load_background_files(BACKGROUND_FOLDER)

def play_wav_async(path):
    def _play():
        try:
            wf = wave.open(path, 'rb')
        except Exception:
            return
        stream = PA.open(format=PA.get_format_from_width(wf.getsampwidth()),
                         channels=wf.getnchannels(),
                         rate=wf.getframerate(),
                         output=True)
        data = wf.readframes(1024)
        audiodata = np.frombuffer(data, dtype=np.int16)/32768.0  # convert to float32 in range [-1,1]
        #audiodata = audiodata * random.choice([0.25,1])   # random volume variation
        #shimmer_reverb_stereo(audiodata)
        #dattorro_reverb_stereo(audiodata)
        data = (audiodata*32768.0).astype(np.int16).tobytes()
        while data:
            stream.write(data)
            data = wf.readframes(1024)
        stream.stop_stream()
        stream.close()
        wf.close()
    threading.Thread(target=_play, daemon=True).start()

def find_note_file(note_name):  # note_name like C4 or Db3
    # exact match first
    if note_name in NOTE_FILES:
        return NOTE_FILES[note_name]
    # try octave alternatives if exact not found
    for okt in ['2','3','4','5','6']:
        candidate = ''.join([c for c in note_name if not c.isdigit()]) + okt
        if candidate in NOTE_FILES:
            return NOTE_FILES[candidate]
    # fallback random file
    return random.choice(list(NOTE_FILES.values())) if NOTE_FILES else None

def build_scale(root, scale_name):
    if root not in CHROMATIC:
        return []
    intervals = SCALES.get(scale_name, SCALES['Major'])
    start = CHROMATIC.index(root)
    notes = []
    for interval in intervals:
        idx = (start + interval) % 12
        notes.append(CHROMATIC[idx])
    return notes

class Ball:
    def __init__(self, x, y, vx, vy, color, octave, harmonic = False):
        self.x = x; self.y = y
        self.vx = vx; self.vy = vy
        self.color = color
        self.harmonic = harmonic
        self.angle = 0
        self.speed= 0
        self.octave = octave
    def move(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

def choose_note_for_hit(scale_notes, octave, harmonic, collision=False,):
    chosen = []
    if collision:
        # triad: degree 0, 2, 4 cyclic in scale
        if not scale_notes:
            return []
        elif not harmonic and octave == BASS_OCTAVE:
            root_idx = random.randrange(len(scale_notes))
            degrees = [root_idx, (root_idx+2)%len(scale_notes), (root_idx+4)%len(scale_notes)]
            for d in degrees:
                name = scale_notes[d]
                # for variety, allow slight octave shifts
                octv = str(random.choice([octave]))
        else:
            name = scale_notes[0]  # root note for harmonic hits
            octv = str(octave)
        chosen.append(find_note_file(name+octv))

    else:
        if not scale_notes:
            return []
        elif not harmonic:
            name = random.choice(scale_notes)
            octv = str(random.choice([octave,octave+1]))
        else:
            name = scale_notes[0]  # root note for harmonic hits
            octv = str(octave)
        chosen.append(find_note_file(name+octv))
    return [c for c in chosen if c]

     

# Main application
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Note Balls ")
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg=BACKGROUND_COLOURS[0])
        self.canvas.pack()
        ctrl = tk.Frame(root)
        ctrl.pack(fill='x')
        self.key_var = tk.StringVar(value='C')
        self.scale_var = tk.StringVar(value='Major')
        self.numballs_var = tk.StringVar(value='3')
        # ball size control: scale factor from 0.5x to 2.0x of base radius
        self.size_var = tk.DoubleVar(value=1.0)
        # speed controls: melody and bass (bass defaults to half melody)
        self.melody_speed_var = tk.DoubleVar(value=100.0)
        self.bass_speed_var = tk.DoubleVar(value=50.0)
        self.harmonics_speed_var = tk.DoubleVar(value=25.0)
        # notes folder selection
        self.note_folder_var = tk.StringVar(value=DEFAULT_NOTE_FOLDER_NAME)
        keys = CHROMATIC
        ttk.OptionMenu(ctrl, self.key_var, self.key_var.get(), *keys).pack(side='left')
        ttk.OptionMenu(ctrl, self.scale_var, self.scale_var.get(), *list(SCALES.keys())).pack(side='left')
        ttk.OptionMenu(ctrl, self.numballs_var, self.numballs_var.get(), *BALLQUANTITY).pack(side='left')
        ttk.OptionMenu(ctrl, self.note_folder_var, self.note_folder_var.get(), *DOWNLOAD_SUBFOLDERS).pack(side='left')
        # Background dropdown (files from Downloads/sounds/background)
        self.bg_var = tk.StringVar(value='(none)')
        bg_options = ['(none)'] + list(BACKGROUND_FILES.keys())
        ttk.Label(ctrl, text="Background:").pack(side='left')
        self.background_dropdownmenu = ttk.OptionMenu(ctrl, self.bg_var, self.bg_var.get(), *bg_options)
        self.background_dropdownmenu.pack(side='left') 

        # Ball size slider (half to double)
        ttk.Label(ctrl, text="Ball Size:").pack(side='left')
        size_scale = tk.Scale(ctrl, from_=0.5, to=2.0, resolution=0.01, orient='horizontal', variable=self.size_var, command=self.update_ball_size, showvalue=0, length=80)
        size_scale.pack(side='left')
        # Speed sliders for melody and bass
        ttk.Label(ctrl, text="Melody Speed:").pack(side='left')
        melody_scale = tk.Scale(ctrl, from_=20, to=300, resolution=1, orient='horizontal', variable=self.melody_speed_var, showvalue=0, length=80)
        melody_scale.pack(side='left')
        ttk.Label(ctrl, text="Bass Speed:").pack(side='left')
        bass_scale = tk.Scale(ctrl, from_=10, to=300, resolution=1, orient='horizontal', variable=self.bass_speed_var, showvalue=0, length=80)
        bass_scale.pack(side='left')
        ttk.Label(ctrl, text="Harmonics Speed:").pack(side='left')
        harmonics_scale = tk.Scale(ctrl, from_=10, to=300, resolution=1, orient='horizontal', variable=self.harmonics_speed_var, showvalue=0, length=80)
        harmonics_scale.pack(side='left')
        ttk.Button(ctrl, text="Start", command=self.start).pack(side='left')
        ttk.Button(ctrl, text="Stop", command=self.stop).pack(side='left')

        self.balls = []
        self.running = False
        self.last_time = None
        self.scale_notes = build_scale(self.key_var.get(), self.scale_var.get())
        # preview update of scale when menus change
        self.key_var.trace_add('write', self.update_scale)
        self.scale_var.trace_add('write', self.update_scale)
        self.bg_var.trace_add('write', self.update_background_colour)
        # update note files when user selects a different notes folder
        self.note_folder_var.trace_add('write', self.update_note_folder)
        # background play thread control
        self.bg_thread = None
        self.bg_stop_event = None

    def update_note_folder(self, *args):
        global NOTE_FILES, NOTE_FOLDER
        folder_name = self.note_folder_var.get()
        folder_path = os.path.join(SOUNDS_DIR, folder_name)
        NOTE_FOLDER = folder_path
        NOTE_FILES = load_note_files(folder_path)

    def update_ball_size(self, *args):
        global BALL_RADIUS
        try:
            factor = float(self.size_var.get())
        except Exception:
            factor = 1.0
        BALL_RADIUS = max(1, int(BASE_BALL_RADIUS * factor))
        # clamp existing balls inside bounds so they aren't outside walls after resize
        if hasattr(self, 'balls') and self.balls:
            for ball in self.balls:
                ball.x = max(BALL_RADIUS, min(WIDTH - BALL_RADIUS, ball.x))
                ball.y = max(BALL_RADIUS, min(HEIGHT - BALL_RADIUS, ball.y))

    def update_scale(self, *args):
        self.scale_notes = build_scale(self.key_var.get(), self.scale_var.get())

    def update_background_colour(self, *args):
        sel = self.bg_var.get()
        index = self.background_dropdownmenu['menu'].index(sel)
        self.canvas.config(bg = BACKGROUND_COLOURS[index])
        
    def start(self):
        if self.running:
            return
        self.update_scale()
        # initialize two balls at random positions and directions
        r = BALL_RADIUS
        # helper to get a random position inside bounds
        def rand_pos():
            x = random.uniform(r, WIDTH - r)
            y = random.uniform(r, HEIGHT - r)
            return x, y
        
        for n in range(int(self.numballs_var.get())):
            angle = random.uniform(0, 2*math.pi)
            speed = float(self.melody_speed_var.get()) #if not Ball.is_bass else float(self.bass_speed_var.get())
            vx, vy = math.cos(angle) * speed, math.sin(angle) * speed
            # ensure it's not overlapping with other balls    
            attempts = 0
            color = BALL_COLOURS[n]
            while attempts < 50:
                x, y = rand_pos()
                overlap = False
                for m in range(len(self.balls)):
                    if math.hypot(x - self.balls[m].x, y - self.balls[m].y) < 2 * r :
                        overlap = True
                        break
                if not overlap:
                    self.balls.append(Ball(x, y, vx, vy, color, OCTAVE_SELECTION[n], HARMONIC_BALLS[n]))
                    break
                attempts += 1

        self.running = True
        self.start_time = time.time()
        self.last_time = time.time()
        self.canvas.delete('all')
        # start background loop if selected
        sel = self.bg_var.get()
        if sel and sel != '(none)' and sel in BACKGROUND_FILES:
            bg_path = BACKGROUND_FILES[sel]
            # create stop event and thread
            self.bg_stop_event = threading.Event()
            def bg_play():
                try:
                    wf = wave.open(bg_path, 'rb')
                except Exception:
                    return
                try:
                    stream = PA.open(format=PA.get_format_from_width(wf.getsampwidth()),
                                     channels=wf.getnchannels(),
                                     rate=wf.getframerate(),
                                     output=True)
                except Exception:
                    try: wf.close()
                    except: pass
                    return
                # loop the short file until stopped
                try:
                    while not self.bg_stop_event.is_set() and self.running:
                        data = wf.readframes(1024)
                        if not data:
                            try:
                                wf.rewind()
                            except Exception:
                                wf.close()
                                wf = wave.open(bg_path, 'rb')
                            continue
                        stream.write(data)
                finally:
                    try:
                        stream.stop_stream(); stream.close()
                    except:
                        pass
                    try:
                        wf.close()
                    except:
                        pass
            self.bg_thread = threading.Thread(target=bg_play, daemon=True)
            self.bg_thread.start()
        self.loop()
    
    def stop(self):
        self.running = False
        # stop background playback and gracefully terminate pyaudio after short delay to allow last notes
        if getattr(self, 'bg_stop_event', None):
            try:
                self.bg_stop_event.set()
            except:
                pass
        threading.Timer(1.0, self.terminate_audio).start()

    def loop(self):
        if not self.running:
            return
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        # apply speed settings to balls so sliders control actual speeds
        if self.balls:
            for ball in self.balls:
                target = float(self.bass_speed_var.get()) if ball.octave == BASS_OCTAVE else ( float(self.harmonics_speed_var.get()) if ball.harmonic else float(self.melody_speed_var.get()) )
                vx, vy = ball.vx, ball.vy
                mag = math.hypot(vx, vy)
                if mag > 1e-6:
                    scale = target / mag
                    ball.vx *= scale
                    ball.vy *= scale
                else:
                    ang = random.uniform(0, 2*math.pi)
                    ball.vx = math.cos(ang) * target
                    ball.vy = math.sin(ang) * target
        # move
        for ball in self.balls:
            ball.move(dt)
            # wall collision
            hit = False
            if ball.x - BALL_RADIUS <= 0:
                ball.x = BALL_RADIUS; ball.vx = abs(ball.vx); hit = True
            elif ball.x + BALL_RADIUS >= WIDTH:
                ball.x = WIDTH - BALL_RADIUS; ball.vx = -abs(ball.vx); hit = True
            if ball.y - BALL_RADIUS <= 0:
                ball.y = BALL_RADIUS; ball.vy = abs(ball.vy); hit = True
            elif ball.y + BALL_RADIUS >= HEIGHT:
                ball.y = HEIGHT - BALL_RADIUS; ball.vy = -abs(ball.vy); hit = True
            if hit:
                # play one note for wall hit
                files = choose_note_for_hit(self.scale_notes, ball.octave, ball.harmonic, collision=False)
                for f in files:
                    if f: play_wav_async(f)
            # ball-ball collision
            for other in self.balls:
                if ball is other:
                    continue
                # other = self.balls[j]
                dx = other.x - ball.x
                dy = other.y - ball.y
                dist = math.sqrt(dx*dx + dy*dy)
                if dist < 2 * BALL_RADIUS and dist > 0.001:
                    # Simple elastic collision
                    nx = dx / dist
                    ny = dy / dist
                    v1n = ball.vx * nx + ball.vy * ny
                    v2n = other.vx * nx + other.vy * ny
                    if v1n - v2n > 0:  # Moving towards each other
                        v1t = ball.vx - v1n * nx
                        v2t = other.vx - v2n * nx
                        ball.vx = v2n * nx + v1t
                        ball.vy = v2n * ny + (ball.vy - v1n * ny)
                        other.vx = v1n * nx + v2t
                        other.vy = v1n * ny + (other.vy - v2n * ny)
                        # Separate balls
                        overlap = 2 * BALL_RADIUS - dist
                        ball.x -= nx * overlap / 2
                        ball.y -= ny * overlap / 2
                        other.x += nx * overlap / 2
                        other.y += ny * overlap / 2
                        for ball in (ball,other):
                            if ball.octave==BASS_OCTAVE:
                                files = choose_note_for_hit(self.scale_notes, ball.octave, ball.harmonic, collision=True)
                                for f in files:
                                    if f: play_wav_async(f)
                            else:
                                files = choose_note_for_hit(self.scale_notes, ball.octave, ball.harmonic, collision=False)
                                for f in files:
                                    if f: play_wav_async(f)

        # draw
        self.canvas.delete('all')
        # rectangular border (pool table)
        #self.canvas.create_rectangle(10,10,WIDTH-10,HEIGHT-10,outline='saddlebrown',width=12)
        for ball in self.balls:
            self.canvas.create_oval(ball.x-BALL_RADIUS, ball.y-BALL_RADIUS,
                                    ball.x+BALL_RADIUS, ball.y+BALL_RADIUS,
                                    fill=ball.color, outline='black')
        # stop after duration
        if time.time() - self.start_time >= RUN_DURATION:
            self.running = False
            # stop background playback and gracefully terminate pyaudio after short delay to allow last notes
            if getattr(self, 'bg_stop_event', None):
                try:
                    self.bg_stop_event.set()
                except:
                    pass
            threading.Timer(1.0, self.terminate_audio).start()
            return
        self.root.after(16, self.loop)

    def terminate_audio(self):
        try:
            PA.terminate()
        except:
            pass

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()