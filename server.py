from flask import Flask, request, jsonify, send_from_directory, render_template, g, make_response
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import datetime
import json
from groq import Groq
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr
import PyPDF2
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
import threading
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3
from contextlib import closing
import uuid
import io
import csv
import requests
from bs4 import BeautifulSoup

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# API Keys
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Database configuration
DATABASE = 'raiden.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        with closing(get_db()) as db:
            # Create tasks table if not exists
            db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    completed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create flashcards table
            db.execute("""
                CREATE TABLE IF NOT EXISTS flashcards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    front TEXT NOT NULL,
                    back TEXT NOT NULL,
                    category TEXT DEFAULT 'General',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create attendance table
            db.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            db.commit()

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Initialize Groq client
def get_groq_client():
    if not GROQ_API_KEY:
        return None
    return Groq(api_key=GROQ_API_KEY)

# Main route
@app.route('/')
def index():
    return render_template('raiden.html')

# Chat endpoint
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        
        client = get_groq_client()
        if not client:
            return jsonify({'error': 'Groq API key not configured'}), 500
        
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": message}],
            temperature=0.7,
            max_tokens=1000
        )
        
        return jsonify({'response': response.choices[0].message.content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Math solver endpoint
@app.route('/solve_math', methods=['POST'])
def solve_math():
    try:
        data = request.json
        problem = data.get('problem', '')
        
        # Parse and solve the mathematical expression
        expr = parse_expr(problem)
        result = expr.evalf()
        
        # Also try to get step-by-step solution
        steps = []
        try:
            # Try to simplify step by step
            simplified = sp.simplify(expr)
            if simplified != expr:
                steps.append(f"Simplified: {simplified}")
            
            # Try to expand if applicable
            if hasattr(expr, 'expand'):
                expanded = expr.expand()
                if expanded != expr:
                    steps.append(f"Expanded: {expanded}")
                    
        except:
            pass
        
        return jsonify({
            'result': str(result),
            'steps': steps,
            'problem': problem
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# PDF summarization endpoint
@app.route('/summarize_pdf', methods=['POST'])
def summarize_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and file.filename.lower().endswith('.pdf'):
            # Read PDF content
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            
            # Summarize using Groq
            client = get_groq_client()
            if not client:
                return jsonify({'error': 'Groq API key not configured'}), 500
            
            prompt = f"Please summarize the following text in 3-5 key points:\n\n{text[:3000]}"
            
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            return jsonify({
                'summary': response.choices[0].message.content,
                'original_text': text[:500] + "..." if len(text) > 500 else text
            })
        else:
            return jsonify({'error': 'Invalid file type. Please upload a PDF file.'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Flashcards endpoints
@app.route('/flashcards', methods=['GET'])
def get_flashcards():
    try:
        with closing(get_db()) as db:
            flashcards = db.execute(
                'SELECT * FROM flashcards ORDER BY created_at DESC'
            ).fetchall()
            
            return jsonify([dict(flashcard) for flashcard in flashcards])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/flashcards', methods=['POST'])
def create_flashcard():
    try:
        data = request.json
        front = data.get('front', '')
        back = data.get('back', '')
        category = data.get('category', 'General')
        
        with closing(get_db()) as db:
            db.execute(
                'INSERT INTO flashcards (front, back, category) VALUES (?, ?, ?)',
                (front, back, category)
            )
            db.commit()
            
        return jsonify({'message': 'Flashcard created successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/flashcards/<int:card_id>', methods=['DELETE'])
def delete_flashcard(card_id):
    try:
        with closing(get_db()) as db:
            db.execute('DELETE FROM flashcards WHERE id = ?', (card_id,))
            db.commit()
            
        return jsonify({'message': 'Flashcard deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Study planner endpoints
@app.route('/study_planner/tasks', methods=['GET'])
def get_tasks():
    try:
        with closing(get_db()) as db:
            tasks = db.execute(
                'SELECT * FROM tasks ORDER BY due_date ASC'
            ).fetchall()
            
            return jsonify([dict(task) for task in tasks])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/study_planner/tasks', methods=['POST'])
def create_task():
    try:
        data = request.json
        task = data.get('task', '')
        due_date = data.get('due_date', '')
        
        with closing(get_db()) as db:
            db.execute(
                'INSERT INTO tasks (task, due_date) VALUES (?, ?)',
                (task, due_date)
            )
            db.commit()
            
        return jsonify({'message': 'Task created successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/study_planner/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    try:
        data = request.json
        completed = data.get('completed', False)
        
        with closing(get_db()) as db:
            db.execute(
                'UPDATE tasks SET completed = ? WHERE id = ?',
                (completed, task_id)
            )
            db.commit()
            
        return jsonify({'message': 'Task updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/study_planner/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        with closing(get_db()) as db:
            db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            db.commit()
            
        return jsonify({'message': 'Task deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# News endpoint
@app.route('/news')
def get_news():
    try:
        if not GNEWS_API_KEY:
            return jsonify({'error': 'News API key not configured'}), 500
        
        url = f"https://gnews.io/api/v4/top-headlines?token={GNEWS_API_KEY}&lang=en&country=us&max=10"
        response = requests.get(url)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to fetch news'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Weather endpoint
@app.route('/weather')
def get_weather():
    try:
        if not OPENWEATHER_API_KEY:
            return jsonify({'error': 'Weather API key not configured'}), 500
        
        city = request.args.get('city', 'London')
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to fetch weather'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Web search endpoint
@app.route('/search-web', methods=['POST'])
def search_web():
    try:
        data = request.json
        query = data.get('query', '')
        
        # Simple web search using requests and BeautifulSoup
        search_url = f"https://www.google.com/search?q={query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract search results (simplified)
        results = []
        for result in soup.find_all('h3')[:5]:
            title = result.get_text()
            link = result.find_parent('a')
            if link:
                href = link.get('href')
                if href and href.startswith('/url?q='):
                    href = href.split('/url?q=')[1].split('&')[0]
                    results.append({'title': title, 'url': href})
        
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Code playground endpoint
@app.route('/code_playground/run', methods=['POST'])
def run_code():
    try:
        data = request.json
        code = data.get('code', '')
        language = data.get('language', 'python')
        
        # This is a simplified code runner - in production, use a proper sandbox
        if language == 'python':
            try:
                # Create a safe execution environment
                exec_globals = {
                    '__builtins__': {
                        'print': print,
                        'len': len,
                        'str': str,
                        'int': int,
                        'float': float,
                        'list': list,
                        'dict': dict,
                        'tuple': tuple,
                        'set': set,
                        'range': range,
                        'enumerate': enumerate,
                        'zip': zip,
                        'map': map,
                        'filter': filter,
                        'sum': sum,
                        'max': max,
                        'min': min,
                        'abs': abs,
                        'round': round,
                        'sorted': sorted,
                        'reversed': reversed,
                        'any': any,
                        'all': all,
                        'bin': bin,
                        'hex': hex,
                        'oct': oct,
                        'chr': chr,
                        'ord': ord,
                        'isinstance': isinstance,
                        'type': type,
                        'hasattr': hasattr,
                        'getattr': getattr,
                        'setattr': setattr,
                        'dir': dir,
                        'vars': vars,
                        'globals': globals,
                        'locals': locals,
                    }
                }
                
                # Capture output
                import sys
                from io import StringIO
                
                old_stdout = sys.stdout
                sys.stdout = captured_output = StringIO()
                
                exec(code, exec_globals)
                
                sys.stdout = old_stdout
                output = captured_output.getvalue()
                
                return jsonify({'output': output, 'error': None})
                
            except Exception as e:
                return jsonify({'output': '', 'error': str(e)})
        else:
            return jsonify({'error': f'Language {language} not supported yet'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Citation generator endpoint
@app.route('/citation/generate', methods=['POST'])
def generate_citation():
    try:
        data = request.json
        title = data.get('title', '')
        author = data.get('author', '')
        year = data.get('year', '')
        url = data.get('url', '')
        citation_style = data.get('style', 'APA')
        
        # Generate citation based on style
        if citation_style == 'APA':
            if url:
                citation = f"{author} ({year}). {title}. Retrieved from {url}"
            else:
                citation = f"{author} ({year}). {title}."
        elif citation_style == 'MLA':
            if url:
                citation = f'"{title}." {author}, {year}, {url}.'
            else:
                citation = f"{author}. {title}. {year}."
        else:
            citation = f"{author}. {title}. {year}."
        
        return jsonify({'citation': citation})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Attendance tracker endpoints
@app.route('/attendance', methods=['GET'])
def get_attendance():
    try:
        with closing(get_db()) as db:
            attendance = db.execute(
                'SELECT * FROM attendance ORDER BY date DESC'
            ).fetchall()
            
            return jsonify([dict(record) for record in attendance])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/attendance', methods=['POST'])
def add_attendance():
    try:
        data = request.json
        student_name = data.get('student_name', '')
        date = data.get('date', '')
        subject = data.get('subject', '')
        status = data.get('status', 'Present')
        notes = data.get('notes', '')
        
        with closing(get_db()) as db:
            db.execute(
                'INSERT INTO attendance (student_name, date, subject, status, notes) VALUES (?, ?, ?, ?, ?)',
                (student_name, date, subject, status, notes)
            )
            db.commit()
            
        return jsonify({'message': 'Attendance record added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'data': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('message')
def handle_message(data):
    emit('response', {'data': f'Echo: {data}'})

# Initialize database on startup
init_db()

if __name__ == '__main__':
    print("🚀 Starting Raiden AI server...")
    print("📊 Features available:")
    print("   - AI Chat")
    print("   - Math Solver")
    print("   - PDF Summarization")
    print("   - Flashcards")
    print("   - Study Planner")
    print("   - Code Playground")
    print("   - News & Weather")
    print("   - Web Search")
    print("   - Citation Generator")
    print("   - Attendance Tracker")
    print("\n🌐 Server will be available at: http://localhost:5000")
    print("📝 Make sure to set your API keys in environment variables:")
    print("   - GROQ_API_KEY")
    print("   - GNEWS_API_KEY")
    print("   - OPENWEATHER_API_KEY")
    
    socketio.run(app, debug=True, port=5000, host='0.0.0.0')
