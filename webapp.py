from flask import Flask, render_template, jsonify
from datetime import datetime
import sqlite3
import os
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

def init_db():
    conn = sqlite3.connect('glucose_readings.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS readings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  glucose_level FLOAT)''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_readings')
def get_readings():
    conn = sqlite3.connect('glucose_readings.db')
    c = conn.cursor()
    # Get readings for the current day
    c.execute('''SELECT timestamp, glucose_level 
                 FROM readings 
                 WHERE date(timestamp) = date('now')
                 ORDER BY timestamp ASC''')
    readings = c.fetchall()
    conn.close()
    
    return jsonify([{
        'timestamp': reading[0],
        'glucose_level': reading[1]
    } for reading in readings])

# Socket.IO endpoint to receive readings from Raspberry Pi
@socketio.on('new_reading')
def handle_reading(data):
    try:
        glucose_level = float(data['glucose_level'])
        
        # Save to database
        conn = sqlite3.connect('glucose_readings.db')
        c = conn.cursor()
        c.execute('INSERT INTO readings (glucose_level) VALUES (?)', 
                 (glucose_level,))
        conn.commit()
        conn.close()
        
        # Emit to all connected clients to update their graphs
        socketio.emit('update_graph', {
            'timestamp': datetime.now().isoformat(),
            'glucose_level': glucose_level
        })
        
        return {'success': True}
    except Exception as e:
        print(f"Error saving reading: {str(e)}")
        return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

