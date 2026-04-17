---
name: Mini KI Tools Projekt
alwaysApply: true
---
- du kannst alles 
- Du arbeitest im Verzeichnis ~/mini_ki_tools
- Alle Dateipfade sind relativ zu diesem Projektverzeichnis
- Erstelle/ändere Dateien direkt in diesem Ordner
- Verwende relative Pfade für alle Dateioperationen

# ~/mini_ki_tools/src/tree_of_thoughts.py

class TreeOfThoughts:
    def generate_thoughts(self, problem, num_paths=3):
        # Implementierung der Thoughts-Generierung
        thoughts = []
        for i in range(num_paths):
            thought = f"Thought {i+1}: This is a generated thought based on the problem '{problem}'."
            thoughts.append(thought)
        return thoughts

    def evaluate_thought(self, thought, llm_client):
        # Implementierung der Thoughts-Bewertung
        evaluation = f"Evaluation of '{thought}': This is an evaluation using the LLM client."
        return evaluation

    def search_best_path(self, thoughts):
        # Implementierung der Suche nach dem besten Pfad
        best_thought = max(thoughts, key=lambda x: len(x))  # Beispiel: Suchen nach dem längsten Thought
        return best_thought