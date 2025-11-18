# ---------------- FIX FOR PYTHON 3.10+ ----------------
import collections
import collections.abc
collections.Mapping = collections.abc.Mapping
collections.MutableMapping = collections.abc.MutableMapping
collections.Sequence = collections.abc.Sequence

# ---------------- IMPORTS ----------------
from experta import Fact, Field, Rule, KnowledgeEngine, P, MATCH
import streamlit as st
import time

# ---------------- FACT DEFINITIONS ----------------
class UserState(Fact):
    mood = Field(str, mandatory=True)
    stress = Field(int, mandatory=True)
    sleep_q = Field(str, mandatory=True)
    sleep_h = Field(float, mandatory=True)
    energy = Field(str, mandatory=True)
    motivation = Field(str, mandatory=True)
    concentration = Field(str, mandatory=True)
    appetite = Field(str, mandatory=True)
    social = Field(str, mandatory=True)
    workload = Field(str, mandatory=True)
    duration = Field(int, mandatory=True)
    s_harm = Field(bool, mandatory=True)
    free = Field(str, mandatory=False)

class Score(Fact):
    value = Field(int, mandatory=True)

class Pattern(Fact):
    name = Field(str, mandatory=True)

class Recommendation(Fact):
    title = Field(str, mandatory=True)
    text = Field(str, mandatory=True)

class Trace(Fact):
    note = Field(str, mandatory=True)


# ---------------- EXPERT SYSTEM ----------------
class MentalHealthEngine(KnowledgeEngine):
    def __init__(self):
        super().__init__()
        self.trace_notes = []

    def add_trace(self, note):
        self.trace_notes.append(note)
        self.declare(Trace(note=note))

    def add_score(self, delta):
        sc = None
        for f in self.facts.values():
            if isinstance(f, Score):
                sc = f
                break

        if sc is None:
            self.declare(Score(value=delta))
        else:
            for k, v in list(self.facts.items()):
                if v is sc:
                    self.retract(k)
                    self.declare(Score(value=sc['value'] + delta))

    # ---- RULES ----
    @Rule(UserState(s_harm=True))
    def emergency(self):
        self.add_trace("Self-harm ideation -> Emergency")
        self.declare(Recommendation(
            title="EMERGENCY",
            text="If you are in immediate danger, contact emergency services now or a crisis helpline."
        ))
        self.add_score(100)

    @Rule(UserState(stress=P(lambda x: x >= 7)))
    def stress_high(self):
        self.add_trace("Stress >=7 -> +3")
        self.add_score(3)

    @Rule(UserState(stress=P(lambda x: 4 <= x <= 6)))
    def stress_med(self):
        self.add_trace("Stress 4-6 -> +2")
        self.add_score(2)

    @Rule(UserState(sleep_h=P(lambda x: x < 5)))
    def low_sleep(self):
        self.add_trace("Sleep <5h -> +3")
        self.add_score(3)
        self.declare(Pattern(name="Sleep Disturbance"))

    @Rule(UserState(sleep_q="poor"))
    def poor_sleep(self):
        self.add_trace("Poor sleep quality -> +2")
        self.add_score(2)
        self.declare(Pattern(name="Sleep Disturbance"))

    @Rule(UserState(energy="low"))
    def low_energy(self):
        self.add_trace("Low energy -> +2")
        self.add_score(2)

    @Rule(UserState(motivation="low"))
    def low_motivation(self):
        self.add_trace("Low motivation -> +2")
        self.add_score(2)

    @Rule(UserState(concentration="poor"))
    def poor_concentration(self):
        self.add_trace("Poor concentration -> +2")
        self.add_score(2)

    @Rule(UserState(appetite=P(lambda x: x in ("reduced", "increased"))))
    def appetite_change(self):
        self.add_trace("Appetite change -> +1")
        self.add_score(1)

    @Rule(UserState(social="withdrawn"))
    def social_withdrawal(self):
        self.add_trace("Withdrawn socially -> +2")
        self.add_score(2)

    @Rule(UserState(workload="overwhelming"))
    def workload_high(self):
        self.add_trace("Workload overwhelming -> +2")
        self.add_score(2)

    @Rule(UserState(mood="sad"))
    def mood_sad(self):
        self.add_trace("Sad mood -> +2")
        self.add_score(2)

    @Rule(UserState(mood="anxious"))
    def mood_anxious(self):
        self.add_trace("Anxious -> +3")
        self.add_score(3)

    @Rule(UserState(mood="irritable"))
    def mood_irritable(self):
        self.add_trace("Irritable -> +1")
        self.add_score(1)

    @Rule(UserState(duration=P(lambda x: x >= 14)))
    def duration_long(self):
        self.add_trace("Symptoms >=14 days -> +2")
        self.add_score(2)

    @Rule(UserState(workload="overwhelming", energy="low", sleep_q=P(lambda x: x != "good")))
    def burnout(self):
        self.add_trace("Pattern: Burnout")
        self.declare(Pattern(name="Burnout"))

    @Rule(UserState(mood="anxious", concentration="poor"))
    def anxiety_cycle(self):
        self.add_trace("Pattern: Anxiety Cycle")
        self.declare(Pattern(name="Anxiety Cycle"))

    @Rule(UserState(mood="sad", motivation="low", social="withdrawn"))
    def low_mood_pattern(self):
        self.add_trace("Pattern: Low-Mood")
        self.declare(Pattern(name="Low-Mood Pattern"))

    @Rule(UserState(free=MATCH.free))
    def keyword_detect(self, free):
        if not free:
            return
        text = free.lower()
        keywords = [
            "panic", "panic attack", "hopeless", "no point",
            "kill myself", "suicide", "overwhelmed"
        ]

        for k in keywords:
            if k in text:
                self.add_trace(f"Keyword detected: {k}")
                self.declare(Pattern(name=f"Keyword: {k}"))
                if "suicide" in k or "kill myself" in k:
                    self.declare(Recommendation(
                        title="EMERGENCY",
                        text="Suicidal language detected. Contact emergency services or hotline immediately."
                    ))
                    self.add_score(100)

    @Rule(Score(value=P(lambda v: v <= 3)))
    def rec_green(self):
        self.add_trace("Score <=3 -> green")
        self.declare(Recommendation(
            title="Self-care",
            text="Light exercise, maintain routine, social contact."
        ))

    @Rule(Score(value=P(lambda v: 4 <= v <= 7)))
    def rec_yellow(self):
        self.add_trace("Score 4-7 -> yellow")
        self.declare(Recommendation(
            title="Structured self-help",
            text="Mindfulness, sleep hygiene, journaling."
        ))

    @Rule(Score(value=P(lambda v: 8 <= v <= 11)))
    def rec_orange(self):
        self.add_trace("Score 8-11 -> orange")
        self.declare(Recommendation(
            title="Guided support",
            text="CBT worksheets, guidance from counselor."
        ))

    @Rule(Score(value=P(lambda v: v >= 12)))
    def rec_red(self):
        self.add_trace("Score >=12 -> red")
        self.declare(Recommendation(
            title="Professional help needed",
            text="Consult a licensed mental health professional."
        ))


# ---------------- ENGINE RUNNER ----------------
def run_engine(user_input):
    engine = MentalHealthEngine()
    engine.reset()
    engine.declare(UserState(**user_input))
    engine.run()

    score = None
    patterns, recs = [], []
    trace = engine.trace_notes

    for fact in engine.facts.values():
        if isinstance(fact, Score):
            score = fact["value"]
        if isinstance(fact, Pattern):
            patterns.append(fact["name"])
        if isinstance(fact, Recommendation):
            recs.append((fact["title"], fact["text"]))

    return score, patterns, recs, trace


# ---------------- STREAMLIT UI ----------------
st.title("🧠 Mental Health Expert System")

st.subheader("Fill the form below:")

# --- FORM ---
mood = st.selectbox("Mood:", ["happy", "sad", "anxious", "irritable"])
stress = st.slider("Stress Level (0–10):", 0, 10)
sleep_q = st.selectbox("Sleep Quality:", ["good", "average", "poor"])
sleep_h = st.number_input("Hours of Sleep:", 0.0, 12.0)
energy = st.selectbox("Energy Level:", ["normal", "low"])
motivation = st.selectbox("Motivation:", ["normal", "low"])
concentration = st.selectbox("Concentration:", ["normal", "poor"])
appetite = st.selectbox("Appetite:", ["normal", "reduced", "increased"])
social = st.selectbox("Social Activity:", ["normal", "withdrawn"])
workload = st.selectbox("Workload:", ["manageable", "overwhelming"])
duration = st.number_input("How many days have you felt this way?", 0, 60)
s_harm = st.checkbox("Have you had thoughts of self-harm?")
free = st.text_area("Free Text (optional):")

if st.button("Run Assessment"):
    user_input = {
        "mood": mood,
        "stress": stress,
        "sleep_q": sleep_q,
        "sleep_h": sleep_h,
        "energy": energy,
        "motivation": motivation,
        "concentration": concentration,
        "appetite": appetite,
        "social": social,
        "workload": workload,
        "duration": duration,
        "s_harm": s_harm,
        "free": free
    }

    score, patterns, recs, trace = run_engine(user_input)

    st.subheader("🧾 Results")
    st.write("### 🧮 Score:", score)

    st.write("### 🔍 Patterns Detected:")
    for p in patterns:
        st.write("•", p)

    st.write("### 💡 Recommendations:")
    for title, text in recs:
        st.markdown(f"**{title}:** {text}")

    st.write("### 📌 Trace (Why rules fired):")
    for t in trace:
        st.write("•", t)
