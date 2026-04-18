from flask import Flask, Response, request, jsonify
import json

app = Flask(__name__)

# In-memory storage for simplicity
tools = {}
resources = {}
prompts = {}

@app.route('/register_tool', methods=['POST'])
def register_tool():
    tool_data = request.json
    tools[tool_data['name']] = tool_data
    return jsonify({"status": "success", "message": "Tool registered"})

@app.route('/register_resource', methods=['POST'])
def register_resource():
    resource_data = request.json
    resources[resource_data['name']] = resource_data
    return jsonify({"status": "success", "message": "Resource registered"})

@app.route('/register_prompt', methods=['POST'])
def register_prompt():
    prompt_data = request.json
    prompts[prompt_data['name']] = prompt_data
    return jsonify({"status": "success", "message": "Prompt registered"})

@app.route('/sse')
def sse():
    def generate():
        while True:
            # Simulate event generation
            event_data = json.dumps(tools)
            yield f"data: {event_data}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, threaded=True)