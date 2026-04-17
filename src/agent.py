from flask import Flask, request, jsonify
import os
import sys
sys.path.append('src')
from plugin_manager import PluginManager
from thought_action_observation import ThoughtActionObservation

class Agent:
    def __init__(self):
        self.thought_action_observation = ThoughtActionObservation()

    def process_message(self, message: str) -> str:
        thought = self.thought_action_observation.think(message)
        action = self.thought_action_observation.act(thought)
        observation = self.thought_action_observation.observe(action)
        return f"Thought: {thought}, Action: {action}, Observation: {observation}"
app = Flask(__name__)
plugin_manager = PluginManager()
plugin_manager.load_plugins_from_directory('plugins')

@app.route('/api/plugins/list', methods=['GET'])
def list_plugins():
    plugins_info = [{'name': name, 'enabled': plugin['enabled']} for name, plugin in plugin_manager.plugins.items()]
    return jsonify(plugins_info)

@app.route('/api/plugins/reload', methods=['POST'])
def reload_plugins():
    plugin_manager.reload_plugins('plugins')
    return jsonify({'status': 'success'})

@app.route('/api/plugins/enable/<name>', methods=['POST'])
def enable_plugin(name):
    if name in plugin_manager.plugins:
        plugin_manager.enable_plugin(name)
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Plugin not found'}), 404

@app.route('/api/plugins/disable/<name>', methods=['POST'])
def disable_plugin(name):
    if name in plugin_manager.plugins:
        plugin_manager.disable_plugin(name)
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Plugin not found'}), 404

if __name__ == "__main__":
    app.run(debug=True)