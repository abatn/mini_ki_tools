from thought_action_observation import TAOLoop

class Agent:
    def __init__(self):
        self.tao_loop = TAOLoop()

    def process_message(self, message: str) -> str:
        result, history = self.tao_loop.run(message)
        return result # Nur den String zurückgeben, nicht das Tuple
        