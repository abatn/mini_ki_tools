import os
import importlib.util
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory storage for plugins
plugins = {}

@app.route('/register_plugin', methods=['POST'])
def register_plugin():
    plugin_data = request.json
    plugins[plugin_data['name']] = plugin_data
    return jsonify({"status": "success", "message": "Plugin registered"})

@app.route('/get_plugins', methods=['GET'])
def get_plugins():
    return jsonify(plugins)

class PluginManager:
    def __init__(self):
        self.plugins = {}
        self.enabled_plugins = set()
        self.observer = Observer()

    def register_plugin(self, plugin_name, module):
        self.plugins[plugin_name] = {
            'module': module,
            'enabled': False
        }

    def enable_plugin(self, plugin_name):
        if plugin_name in self.plugins:
            self.plugins[plugin_name]['enabled'] = True
            self.enabled_plugins.add(plugin_name)

    def disable_plugin(self, plugin_name):
        if plugin_name in self.plugins:
            self.plugins[plugin_name]['enabled'] = False
            self.enabled_plugins.discard(plugin_name)

    def load_plugins_from_directory(self, directory):
        for filename in os.listdir(directory):
            if filename.endswith('.py') and filename != '__init__.py':
                filepath = os.path.join(directory, filename)
                spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'register'):
                    module.register(self)

    def start_watching_directory(self, directory):
        event_handler = FileSystemEventHandler()
        event_handler.on_modified = lambda event: self.reload_plugins(directory)
        self.observer.schedule(event_handler, path=directory, recursive=False)
        self.observer.start()

    def reload_plugins(self, directory):
        self.plugins.clear()
        self.enabled_plugins.clear()
        self.load_plugins_from_directory(directory)

# Example usage
if __name__ == "__main__":
    plugin_manager = PluginManager()
    plugin_manager.load_plugins_from_directory('plugins')
    plugin_manager.start_watching_directory('plugins')

    app.run(debug=True, threaded=True)