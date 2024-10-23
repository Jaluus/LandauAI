import random

TOPICS = [
    "Wellen",
    "Arbeit",
    "Gravitation",
    "Schwingungen",
    "Elastizität",
    "Kraftfelder",
    "Trägheitstensor",
    "Lorentztransformation",
    "Relativitätstheorie",
    "Minkowski-Diagramm",
    "Kreiselbewegung",
]

COMPARISONS = [
    "einem Dielektrikum und einem Paraelektrikum",
    "der Coulomb Kraft und der Gravitationskraft",
    "Galilei-Transformation und Lorentz Transformation",
    "einem Gedämpften und einem ungedämpften Oszillator",
    "den Drei Fällen eines gedämpften Oszillators",
]

# The lambda function is there to ensure the random choice is made at the time of the call
# without the lambda function, the random choice would be made at the time of the import, so only once
DEFAULT_STARTERS = [
    {
        "label": "Prüfungsfragen erstellen",
        "message": lambda: f"Erstell mir drei Prüfungsfragen zum Thema '{random.choice(TOPICS)}' ohne Antworten und ohne Tipps.",
        "icon": "/public/icons/icon_hat.svg",
    },
    {
        "label": "Themen kurzfassen",
        "message": lambda: f"Schreib mir eine kurze Zusammenfassung über das Thema '{random.choice(TOPICS)}'. Es sollten ungefähr 150 Wörter sein.",
        "icon": "/public/icons/icon_pen.svg",
    },
    {
        "label": "Phänomene erklären",
        "message": lambda: "Kannst du mir ein Beispiel nennen, wo die Lorentztransformation eine Rolle spielt?",
        "icon": "/public/icons/icon_bulb.svg",
    },
    {
        "label": "Konzepte Vergleichen",
        "message": lambda: f"Was ist der Unterschied zwischen {random.choice(COMPARISONS)}? Stelle es in Tabellenform dar.",
        "icon": "/public/icons/icon_atom.svg",
    },
]

COPILOT_STARTERS = [
    {
        "label": "Prüfungsfragen erstellen",
        "message": lambda: "Erstell mir drei Prüfungsfragen für das Kapitel ohne Antworten und ohne Tipps.",
        "icon": "/public/icons/icon_hat.svg",
    },
    {
        "label": "Aufgaben überlegen",
        "message": lambda: "Stell mir eine Aufgabe das zum Kapitel passt ohne Antwort und ohne Tipps.",
        "icon": "/public/icons/icon_pen.svg",
    },
    {
        "label": "Seite zusammenfassen",
        "message": lambda: "Fass die aktuelle Seite in ~100 wörtern zusammen.",
        "icon": "/public/icons/icon_book.svg",
    },
]
