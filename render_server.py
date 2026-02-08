from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)
CORS(app)

# Store active systems
active_systems = {}
lock = threading.Lock()

# Cleanup old entries (older than 5 minutes)
def cleanup_old_entries():
    while True:
        current_time = datetime.now()
        with lock:
            to_delete = []
            for system_id, data in list(active_systems.items()):
                last_seen = datetime.fromisoformat(data['last_seen'])
                if current_time - last_seen > timedelta(minutes=5):
                    to_delete.append(system_id)
            
            for system_id in to_delete:
                del active_systems[system_id]
        
        time.sleep(60)  # Cleanup every minute

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_entries, daemon=True)
cleanup_thread.start()

@app.route('/announce', methods=['POST'])
def announce_availability():
    data = request.json
    system_id = data.get('system_id')
    ip_address = data.get('ip_address', request.remote_addr)
    port = data.get('port')
    
    if not system_id or not port:
        return jsonify({'error': 'system_id and port are required'}), 400
    
    with lock:
        active_systems[system_id] = {
            'ip_address': ip_address,
            'port': port,
            'last_seen': datetime.now().isoformat(),
            'system_name': data.get('system_name', 'Unknown System')
        }
    
    return jsonify({
        'status': 'success',
        'message': f'System {system_id} announced as available'
    })

@app.route('/available', methods=['GET'])
def get_available_systems():
    with lock:
        # Filter only recently active systems (last 2 minutes)
        current_time = datetime.now()
        recent_systems = {}
        
        for system_id, data in active_systems.items():
            last_seen = datetime.fromisoformat(data['last_seen'])
            if current_time - last_seen <= timedelta(minutes=2):
                recent_systems[system_id] = data
        
        return jsonify({
            'count': len(recent_systems),
            'systems': recent_systems
        })

@app.route('/remove/<system_id>', methods=['DELETE'])
def remove_system(system_id):
    with lock:
        if system_id in active_systems:
            del active_systems[system_id]
            return jsonify({'status': 'success', 'message': f'System {system_id} removed'})
        return jsonify({'status': 'error', 'message': 'System not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
