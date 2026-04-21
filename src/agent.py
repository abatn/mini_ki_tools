from thought_action_observation import TAOLoop

class Agent:
    def __init__(self):
        self.tao_loop = TAOLoop()

    def process_message(self, message: str):
        result, tao_history = self.tao_loop.run(message)
        history = []
        for state in tao_history:
            history.append({
                "iteration": state.iteration,
                "thought": state.thought,
                "tool_calls": [{"tool": tc.tool.value, "arguments": tc.arguments, "result": tc.result, "success": tc.success} for tc in state.tool_calls],
                "observations": state.observations,
                "final_result": state.final_result
            })
        return result, history
        