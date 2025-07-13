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

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

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
                    priority INTEGER DEFAULT 2,
                    completed BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create flashcards table if not exists
            db.execute("""
                CREATE TABLE IF NOT EXISTS flashcards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create attendance table if not exists
            db.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    status TEXT NOT NULL,  -- 'present', 'absent', 'late'
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)  -- Ensure only one record per date
                );
            """)
            
            db.commit()

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Groq client with current supported models
groq_api_key = os.environ.get('GROQ_API_KEY', "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")
client = Groq(api_key=groq_api_key)

# Current supported models (July 2025)
SUPPORTED_MODELS = [
    "llama3-8b-8192",    # Fast and efficient
    "llama3-70b-8192",   # More powerful but slower
    "mixtral-8x7b-32768" # Keeping as fallback in case it comes back
]

# Select the first working model
ACTIVE_MODEL = None
for model in SUPPORTED_MODELS:
    try:
        # Test the model with a simple prompt
        test_response = client.chat.completions.create(
            messages=[{"role": "user", "content": "Hello"}],
            model=model,
            max_tokens=10
        )
        if test_response.choices:
            ACTIVE_MODEL = model
            break
    except Exception as e:
        print(f"Model {model} not available: {str(e)}")
        continue

if not ACTIVE_MODEL:
    raise RuntimeError("No supported models available. Check Groq's documentation for current models.")

print(f"Using model: {ACTIVE_MODEL}")

# Helper functions
def generate_response(prompt, max_tokens=1024):
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=ACTIVE_MODEL,
            max_tokens=max_tokens,
            temperature=0.7  # Balanced creativity/factuality
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        return f"Sorry, I encountered an error processing your request. Please try again."

def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def schedule_task_reminders(task):
    """Schedule all reminders for a task using APScheduler"""
    try:
        due_time = datetime.strptime(task['due_date'], '%Y-%m-%dT%H:%M')
        
        # Remove any existing reminders for this task
        try:
            scheduler.remove_job(f"reminder_{task['id']}_30min")
            scheduler.remove_job(f"reminder_{task['id']}_due")
        except:
            pass  # Jobs might not exist
        
        # Schedule 30-minute reminder if it's in the future
        reminder_time = due_time - timedelta(minutes=30)
        if reminder_time > datetime.now():
            scheduler.add_job(
                send_reminder_notification,
                'date',
                run_date=reminder_time,
                args=[task['id'], False],
                id=f"reminder_{task['id']}_30min"
            )
        
        # Schedule due notification if it's in the future
        if due_time > datetime.now():
            scheduler.add_job(
                send_reminder_notification,
                'date',
                run_date=due_time,
                args=[task['id'], True],
                id=f"reminder_{task['id']}_due"
            )
        print(f"Scheduled reminders for task {task['id']} (Due: {task['due_date']})")
    except Exception as e:
        print(f"Error scheduling reminders for task {task['id']}: {str(e)}")

def send_reminder_notification(task_id, is_due):
    """Send reminder notification via WebSocket"""
    with app.app_context():
        with get_db() as db:
            task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if task and not task['completed']:
                task_dict = dict(task)
                socketio.emit('task_reminder', {
                    'task': task_dict['task'],
                    'due_date': task_dict['due_date'],
                    'task_id': task_dict['id'],
                    'is_due': is_due
                })

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Routes
@app.route('/')
def index():
    return render_template('raiden.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    prompt = f"""You are Raiden AI, an intelligent university assistant. Provide helpful, accurate and well-structured responses to student questions.

    Guidelines for responses:
    1. Be professional yet friendly and approachable
    2. Provide detailed explanations for complex topics
    3. Break down solutions step-by-step when appropriate
    4. Use clear headings and bullet points for organization
    5. Format code examples properly with syntax highlighting
    6. Use bold text for important concepts and key terms
    7. Provide examples and analogies when helpful
    8. Admit when you don't know something
    9. Structure responses with clear sections
    10. Use proper HTML formatting (h1, h2, h3, p, ul, li, strong, em, code, pre)
    11. Do NOT use markdown formatting (no **, ##, etc.)
    12. Make responses educational and easy to understand for students

    User: {message}
    Raiden AI: """
    
    response = generate_response(prompt, max_tokens=1500)
    return jsonify({"response": response})

@app.route('/code_playground/run', methods=['POST'])
def run_code():
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', 'python')
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    try:
        # For Python, we can use exec (with caution)
        if language == 'python':
            # Create a dictionary to capture the output
            output = []
            import io
            from contextlib import redirect_stdout
            
            f = io.StringIO()
            with redirect_stdout(f):
                try:
                    exec(code, {'__builtins__': {}})
                except Exception as e:
                    output.append(f"Error: {str(e)}")
            
            output_str = f.getvalue()
            if not output_str:
                output_str = ""
            
            # Generate result statement
            result_prompt = f"""Given this {language} code and its output, create a concise result statement:

            Code:
            {code}

            Output:
            {output_str}

            Create a single sentence that states what the output will be, in this format:
            "The output of the code will be [specific result based on the code and output]."

            Examples:
            - For factorial function: "The output of the code will be the result of the factorial function for the input n = 13, which is 6,227."
            - For print statement: "The output of the code will be 'Hello World'."
            - For variable assignment: "The output of the code will be the value 42."

            Result:"""
            
            result_statement = generate_response(result_prompt, max_tokens=200)
            
            # Generate explanation
            explanation_prompt = f"""Analyze this {language} code and provide a comprehensive explanation starting with "Overview of the Code":

            Code:
            {code}

            Output:
            {output_str}

            Provide a well-structured explanation that includes:
            1. Overview of the Code
            2. How it works (step-by-step breakdown)
            3. Key concepts and techniques used
            4. Any important details about the output
            5. Educational insights for learning

            Use HTML formatting (h3, p, ul, li, strong, code) but NO markdown formatting.
            Make it easy for students to understand and learn from.

            Explanation:"""
            
            explanation = generate_response(explanation_prompt, max_tokens=1000)
            
            return jsonify({
                'output': output_str,
                'result_statement': result_statement,
                'explanation': explanation
            })
        else:
            # For other languages, use Groq to analyze
            prompt = f"""Analyze this {language} code and provide a comprehensive explanation starting with "Overview of the Code":

            Code:
            {code}

            Provide a detailed analysis including:
            1. Overview of the Code
            2. How it works
            3. Expected output
            4. Key concepts and techniques
            5. Potential issues or improvements
            6. Learning insights

            Use HTML formatting (h3, p, ul, li, strong, code) but NO markdown formatting.
            Make it educational and easy to understand for students.

            Analysis:"""
            
            analysis = generate_response(prompt, max_tokens=1000)
            return jsonify({
                'output': f"Code analysis for {language} (not executed)",
                'explanation': analysis
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/solve_math', methods=['POST'])
def solve_math():
    data = request.get_json()
    equation = data.get('equation', '')
    
    if not equation:
        return jsonify({"error": "No equation provided"}), 400
    
    try:
        # Enhanced symbolic solution with SymPy
        symbolic_solution = ""
        try:
            # Clean the equation and identify variables
            cleaned_equation = equation.replace(' ', '').replace('×', '*').replace('÷', '/')
            
            # Check if it's a simple arithmetic expression (no variables)
            if not any(char.isalpha() for char in cleaned_equation):
                # Evaluate arithmetic expression
                try:
                    expr = parse_expr(cleaned_equation)
                    result = expr.evalf()
                    # Format result nicely - remove unnecessary decimal places
                    if hasattr(result, 'is_integer') and result.is_integer():
                        result_str = str(int(result))
                    else:
                        result_str = str(float(result))
                    symbolic_solution = f"<strong>Result:</strong> <code>{equation}</code> = <strong>{result_str}</strong>"
                except Exception as calc_error:
                    # If SymPy fails, try basic evaluation
                    try:
                        # Safe evaluation for basic arithmetic
                        result = eval(cleaned_equation)
                        if isinstance(result, (int, float)):
                            if result.is_integer():
                                result_str = str(int(result))
                            else:
                                result_str = str(float(result))
                            symbolic_solution = f"<strong>Result:</strong> <code>{equation}</code> = <strong>{result_str}</strong>"
                        else:
                            symbolic_solution = f"<strong>Result:</strong> <code>{equation}</code> = <strong>{result}</strong>"
                    except:
                        symbolic_solution = f"<strong>Calculation Error:</strong> Unable to process {equation}. Please check the format and try again."
            else:
                # Handle equations with variables
                # Find all variables in the equation
                variables = set()
                for char in cleaned_equation:
                    if char.isalpha():
                        variables.add(char)
                
                if len(variables) == 1:
                    # Single variable equation
                    var = list(variables)[0]
                    var_symbol = sp.symbols(var)
                    
                    # Check if it's an equation (contains =)
                    if '=' in cleaned_equation:
                        # Solve equation
                        left_side, right_side = cleaned_equation.split('=', 1)
                        try:
                            left_expr = parse_expr(left_side)
                            right_expr = parse_expr(right_side)
                            equation_expr = sp.Eq(left_expr, right_expr)
                            solution = sp.solve(equation_expr, var_symbol)
                            if solution:
                                # Format solution nicely
                                if len(solution) == 1:
                                    sol_str = str(solution[0])
                                    if hasattr(solution[0], 'is_integer') and solution[0].is_integer():
                                        sol_str = str(int(solution[0]))
                                    symbolic_solution = f"<strong>Solution:</strong> {var} = {sol_str}"
                                else:
                                    sol_str = str(solution)
                                    symbolic_solution = f"<strong>Solutions:</strong> {var} = {sol_str}"
                            else:
                                symbolic_solution = f"<strong>No solution found</strong> for {equation}"
                        except:
                            # If parsing fails, try to simplify the expression
                            try:
                                expr = parse_expr(cleaned_equation)
                                simplified = sp.simplify(expr)
                                symbolic_solution = f"<strong>Simplified form:</strong> {equation} = {simplified}"
                            except:
                                symbolic_solution = f"<strong>Expression:</strong> {equation} (requires manual evaluation)"
                    else:
                        # Simplify expression
                        try:
                            expr = parse_expr(cleaned_equation)
                            simplified = sp.simplify(expr)
                            symbolic_solution = f"<strong>Simplified form:</strong> {equation} = {simplified}"
                        except:
                            symbolic_solution = f"<strong>Expression:</strong> {equation} (requires manual evaluation)"
                else:
                    # Multiple variables or complex expression
                    try:
                        expr = parse_expr(cleaned_equation)
                        simplified = sp.simplify(expr)
                        symbolic_solution = f"<strong>Simplified form:</strong> {equation} = {simplified}"
                    except:
                        symbolic_solution = f"<strong>Expression:</strong> {equation} (multiple variables detected)"
                    
        except Exception as sympy_error:
            symbolic_solution = f"<strong>Calculation Error:</strong> Unable to process {equation}. Please check the format and try again."
        
        # Enhanced explanation prompt with better structure
        prompt = f"""Solve and explain the following math problem in a clear, professional, and educational manner:

        Problem: {equation}

        Provide a well-structured solution that includes:

        <h3>Problem Analysis</h3>
        - Identify the type of problem (arithmetic, algebra, equation, etc.)
        - Explain what we need to find or calculate
        - Mention any important mathematical concepts involved

        <h3>Solution Steps</h3>
        - Break down the solution into clear, numbered steps
        - Show each calculation with proper mathematical notation
        - Explain the reasoning behind each step
        - Use order of operations (PEMDAS) when applicable

        <h3>Final Answer</h3>
        - Present the final result clearly and prominently
        - Include units if applicable
        - Verify the answer is reasonable

        <h3>Key Concepts</h3>
        - Explain the mathematical rules and concepts used
        - Provide learning insights and tips
        - Mention common mistakes to avoid

        Formatting requirements:
        - Use ONLY HTML tags: h3, p, ul, li, strong, code, em
        - Use <code> tags for mathematical expressions and calculations
        - Use <strong> tags for final answers and important terms
        - Use <em> tags for emphasis and learning tips
        - Make it professional, clear, and easy to follow
        - Keep explanations concise but comprehensive
        - Structure with proper headings and bullet points
        - Ensure all HTML tags are properly closed

        Solution:"""
        
        explanation = generate_response(prompt, max_tokens=1200)
        
        return jsonify({
            "solution": symbolic_solution,
            "explanation": explanation
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/flashcards', methods=['GET', 'POST'])
def handle_flashcards():
    try:
        if request.method == 'GET':
            with get_db() as db:
                # Verify table exists
                try:
                    db.execute("SELECT 1 FROM flashcards LIMIT 1")
                except sqlite3.OperationalError as e:
                    if "no such table" in str(e):
                        init_db()  # Reinitialize database if table is missing
                        return jsonify({"flashcards": []})
                    raise
                
                flashcards = db.execute("SELECT * FROM flashcards").fetchall()
                flashcards = [dict(flashcard) for flashcard in flashcards]
                return jsonify({"flashcards": flashcards})
        else:
            data = request.get_json()
            text = data.get('text', '')
            
            if not text:
                return jsonify({"error": "No text provided"}), 400
            
            try:
                prompt = f"""Convert the following study notes into a list of 5-10 flashcards in JSON format. 
                Each flashcard should have a clear question and a concise answer.
                Return only the JSON array with no additional text or explanations.
                
                Notes:
                {text}
                
                Format example:
                [{{"question": "What is photosynthesis?", "answer": "The process by which plants convert sunlight into energy."}}]"""
                
                response = generate_response(prompt)
                response = response.strip().replace('```json', '').replace('```', '').strip()
                generated_flashcards = json.loads(response)
                
                with get_db() as db:
                    # Verify table exists
                    try:
                        db.execute("SELECT 1 FROM flashcards LIMIT 1")
                    except sqlite3.OperationalError as e:
                        if "no such table" in str(e):
                            init_db()  # Reinitialize database if table is missing
                    
                    for card in generated_flashcards:
                        db.execute(
                            "INSERT INTO flashcards (question, answer) VALUES (?, ?)",
                            (card['question'], card['answer'])
                        )
                    db.commit()
                    
                    # Get the newly added flashcards with their IDs
                    new_flashcards = []
                    for card in generated_flashcards:
                        new_card = db.execute(
                            "SELECT * FROM flashcards WHERE question = ? AND answer = ? ORDER BY id DESC LIMIT 1",
                            (card['question'], card['answer'])
                        ).fetchone()
                        new_flashcards.append(dict(new_card))
                
                return jsonify({
                    "success": True,
                    "message": f"Added {len(new_flashcards)} new flashcards",
                    "flashcards": new_flashcards
                })
            except json.JSONDecodeError as e:
                return jsonify({
                    "error": f"Failed to parse AI response: {str(e)}",
                    "response": response if 'response' in locals() else None
                }), 500
            except Exception as e:
                return jsonify({
                    "error": f"Failed to generate flashcards: {str(e)}",
                    "response": response if 'response' in locals() else None
                }), 500
    except Exception as e:
        return jsonify({
            "error": f"Database error: {str(e)}"
        }), 500

@app.route('/flashcards/<int:card_id>', methods=['DELETE'])
def delete_flashcard(card_id):
    try:
        with get_db() as db:
            # First get the card to return it in the response
            card = db.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,)).fetchone()
            if not card:
                return jsonify({"error": "Flashcard not found"}), 404
            
            db.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))
            db.commit()
            
            return jsonify({
                "success": True,
                "message": "Flashcard deleted successfully",
                "deleted_card": dict(card)
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/summarize_pdf', methods=['POST'])
def summarize_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        if file and file.filename.lower().endswith('.pdf'):
            # Ensure upload folder exists
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Extract text from PDF
            text = extract_text_from_pdf(filepath)
            if text.startswith("Error"):
                return jsonify({"error": text}), 500
            
            # Generate summary
            prompt = f"""Create a comprehensive, well-structured summary of the following PDF document:

            Document Content:
            {text[:12000]}  # Limit to first 12k chars to avoid token limits

            Provide a detailed summary that includes:
            1. Main topic and purpose of the document
            2. Key concepts and ideas presented
            3. Important findings or conclusions
            4. Supporting evidence or examples
            5. Practical applications or implications
            6. Summary of main sections

            Format the summary with:
            - Clear headings and subheadings
            - Bullet points for key information
            - Bold text for important terms
            - Proper organization and flow
            - Educational insights for students

            Use HTML formatting (h2, h3, p, ul, li, strong, em) but NO markdown formatting.
            Make it comprehensive, readable, and educational.

            Summary:"""
            
            summary = generate_response(prompt, max_tokens=1500)
            return jsonify({"summary": summary})
        else:
            return jsonify({"error": "Only PDF files are allowed"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to process PDF: {str(e)}"}), 500

@app.route('/citation/fields', methods=['GET'])
def get_citation_fields():
    source_type = request.args.get('source_type', 'book')
    
    # Define required fields for each source type
    fields = {
        'book': ['author', 'title', 'year', 'publisher', 'location'],
        'journal': ['author', 'title', 'journal', 'year', 'volume', 'issue', 'pages', 'doi'],
        'website': ['author', 'title', 'website', 'url', 'pub_date', 'retrieval_date'],
        'video': ['author', 'title', 'year', 'platform', 'url', 'duration'],
        'newspaper': ['author', 'title', 'newspaper', 'year', 'pages', 'date'],
        'thesis': ['author', 'title', 'year', 'university', 'location'],
        'conference': ['author', 'title', 'conference', 'year', 'location', 'pages'],
        'report': ['author', 'title', 'year', 'institution', 'location', 'report_number']
    }
    
    return jsonify({
        'required_fields': fields.get(source_type, []),
        'optional_fields': []
    })

@app.route('/citation/generate', methods=['POST'])
def generate_citation():
    data = request.get_json()
    style = data.get('style', 'apa')
    source_type = data.get('source_type', 'book')
    
    # Validate required fields
    required_fields = {
        'book': ['author', 'title', 'year'],
        'journal': ['author', 'title', 'journal', 'year'],
        'website': ['title', 'url'],
        'video': ['title', 'url'],
        'newspaper': ['author', 'title', 'newspaper', 'date'],
        'thesis': ['author', 'title', 'year', 'university'],
        'conference': ['author', 'title', 'conference', 'year'],
        'report': ['author', 'title', 'year', 'institution']
    }
    
    missing_fields = []
    for field in required_fields.get(source_type, []):
        if not data.get(field):
            missing_fields.append(field)
    
    if missing_fields:
        return jsonify({
            'error': f'Missing required fields: {", ".join(missing_fields)}',
            'required_fields': required_fields.get(source_type, [])
        }), 400
    
    # Prepare prompt for the AI
    prompt = f"""Generate a {style.upper()} style citation (7th edition if APA) for the following {source_type} source:
    
    Source Type: {source_type}
    Author(s): {data.get('author', 'N/A')}
    Title: {data.get('title', 'N/A')}
    Year: {data.get('year', 'N/A')}
    Journal: {data.get('journal', 'N/A')}
    Volume: {data.get('volume', 'N/A')}
    Issue: {data.get('issue', 'N/A')}
    Pages: {data.get('pages', 'N/A')}
    Publisher: {data.get('publisher', 'N/A')}
    URL: {data.get('url', 'N/A')}
    DOI: {data.get('doi', 'N/A')}
    Publication Date: {data.get('pub_date', 'N/A')}
    Retrieval Date: {data.get('retrieval_date', 'N/A')}
    Location: {data.get('location', 'N/A')}
    
    The citation should be properly formatted according to {style.upper()} guidelines for a {source_type}.
    Only return the citation itself with no additional text or explanations.
    
    Citation:"""
    
    citation = generate_response(prompt)
    return jsonify({"citation": citation.strip()})

@app.route('/transcribe/start', methods=['POST'])
def start_transcription():
    # In a real implementation, you would start a transcription service here
    return jsonify({"status": "recording_started", "session_id": str(uuid.uuid4())})

@app.route('/transcribe/stop', methods=['POST'])
def stop_transcription():
    # In a real implementation, you would stop the transcription service here
    return jsonify({"status": "recording_stopped"})

@app.route('/transcribe/generate_slides', methods=['POST'])
def generate_slides_from_transcript():
    transcript = request.form.get('transcript', '')
    
    if not transcript:
        return jsonify({"error": "No transcript provided"}), 400
    
    # Generate slides from transcript with better structure
    prompt = f"""Convert the following lecture transcript into a well-structured slide presentation with 5-8 slides.
    
    Requirements:
    1. Each slide should have a clear, concise title
    2. Include 3-5 key bullet points per slide
    3. Use proper markdown formatting with # for slide titles
    4. Make the content educational and easy to follow
    5. Focus on main concepts and key takeaways
    6. Use bullet points (-) for list items
    
    Transcript:
    {transcript[:8000]}  # Limit to first 8k chars for better processing
    
    Format the response as:
    # Slide Title 1
    - Key point 1
    - Key point 2
    - Key point 3
    
    # Slide Title 2
    - Key point 1
    - Key point 2
    - Key point 3
    
    And so on...
    
    Slides:"""
    
    slides = generate_response(prompt, max_tokens=1500)
    return jsonify({"slides": slides})

@app.route('/attendance', methods=['GET', 'POST'])
def handle_attendance():
    try:
        if request.method == 'GET':
            year = request.args.get('year', datetime.now().year)
            month = request.args.get('month', datetime.now().month)
            
            with get_db() as db:
                # Verify table exists
                try:
                    db.execute("SELECT 1 FROM attendance LIMIT 1")
                except sqlite3.OperationalError as e:
                    if "no such table" in str(e):
                        init_db()  # Reinitialize database if table is missing
                        return jsonify({"error": "Database was reinitialized, please try again"}), 500
                    raise
                
                # Get all attendance records for the month
                attendance = db.execute("""
                    SELECT * FROM attendance 
                    WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ?
                    ORDER BY date
                """, (str(year), f"{int(month):02d}")).fetchall()
                
                attendance = [dict(record) for record in attendance]
                
                # Get statistics
                stats = db.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present,
                        SUM(CASE WHEN status = 'absent' THEN 1 ELSE 0 END) as absent,
                        SUM(CASE WHEN status = 'late' THEN 1 ELSE 0 END) as late
                    FROM attendance
                    WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ?
                """, (str(year), f"{int(month):02d}")).fetchone()
                
                stats = dict(stats) if stats else {
                    'total': 0, 'present': 0, 'absent': 0, 'late': 0
                }
                
                return jsonify({
                    'attendance': attendance,
                    'stats': stats
                })
        else:
            data = request.get_json()
            date = data.get('date')
            status = data.get('status')
            notes = data.get('notes', '')
            
            if not date or not status:
                return jsonify({"error": "Missing required fields"}), 400
            
            with get_db() as db:
                # Verify table exists
                try:
                    db.execute("SELECT 1 FROM attendance LIMIT 1")
                except sqlite3.OperationalError as e:
                    if "no such table" in str(e):
                        init_db()  # Reinitialize database if table is missing
                        return jsonify({"error": "Database was reinitialized, please try again"}), 500
                    raise
                
                # Check if record already exists for this date
                existing = db.execute(
                    "SELECT id FROM attendance WHERE date = ?",
                    (date,)
                ).fetchone()
                
                if existing:
                    # Update existing record
                    db.execute(
                        "UPDATE attendance SET status = ?, notes = ? WHERE id = ?",
                        (status, notes, existing['id'])
                    )
                    action = 'updated'
                else:
                    # Create new record
                    db.execute(
                        "INSERT INTO attendance (date, status, notes) VALUES (?, ?, ?)",
                        (date, status, notes)
                    )
                    action = 'added'
                
                db.commit()
                
                # Get the updated/added record
                record = db.execute(
                    "SELECT * FROM attendance WHERE id = ?",
                    (db.lastrowid if not existing else existing['id'],)
                ).fetchone()
                
                socketio.emit('attendance_update', {
                    'action': action,
                    'record': dict(record)
                })
                
                return jsonify({
                    "message": f"Attendance record {action} successfully",
                    "record": dict(record)
                })
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            init_db()  # Reinitialize database if table is missing
            return jsonify({"error": "Database was reinitialized, please try again"}), 500
        raise

@app.route('/attendance/<int:record_id>', methods=['DELETE'])
def delete_attendance_record(record_id):
    with get_db() as db:
        # First get the record to return it in the response
        record = db.execute(
            "SELECT * FROM attendance WHERE id = ?",
            (record_id,)
        ).fetchone()
        
        if not record:
            return jsonify({"error": "Record not found"}), 404
        
        db.execute("DELETE FROM attendance WHERE id = ?", (record_id,))
        db.commit()
        
        socketio.emit('attendance_update', {
            'action': 'deleted',
            'record_id': record_id
        })
        
        return jsonify({
            "message": "Attendance record deleted successfully",
            "deleted_record": dict(record)
        })

@app.route('/attendance/export', methods=['GET'])
def export_attendance():
    format = request.args.get('format', 'csv')
    year = request.args.get('year', datetime.now().year)
    month = request.args.get('month', datetime.now().month)
    
    with get_db() as db:
        # Verify table exists
        try:
            db.execute("SELECT 1 FROM attendance LIMIT 1")
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                init_db()  # Reinitialize database if table is missing
                return jsonify({"error": "Database was reinitialized, please try again"}), 500
            raise
        
        records = db.execute("""
            SELECT date, status, notes 
            FROM attendance
            WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ?
            ORDER BY date
        """, (str(year), f"{int(month):02d}")).fetchall()
        
        records = [dict(record) for record in records]
        
        if format == 'csv':
            # Generate CSV
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=['date', 'status', 'notes'])
            writer.writeheader()
            writer.writerows(records)
            
            response = make_response(output.getvalue())
            response.headers['Content-Disposition'] = f'attachment; filename=attendance_{year}_{month}.csv'
            response.headers['Content-type'] = 'text/csv'
            return response
        else:
            # Default to JSON
            return jsonify(records)

@app.route('/study_planner/tasks', methods=['GET', 'POST'])
def handle_tasks():
    if request.method == 'GET':
        period = request.args.get('period', 'today')
        now = datetime.now()
        
        if period == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif period == 'week':
            start = now - timedelta(days=now.weekday())
            end = start + timedelta(days=7)
        elif period == 'month':
            start = now.replace(day=1)
            end = (start + timedelta(days=32)).replace(day=1)
        else:
            start = datetime.min
            end = datetime.max
        
        with get_db() as db:
            # Verify table exists
            try:
                db.execute("SELECT 1 FROM tasks LIMIT 1")
            except sqlite3.OperationalError as e:
                if "no such table" in str(e):
                    init_db()  # Reinitialize database if table is missing
                    return jsonify({"error": "Database was reinitialized, please try again"}), 500
                raise
            
            query = """
                SELECT * FROM tasks 
                WHERE datetime(due_date) BETWEEN datetime(?) AND datetime(?)
                ORDER BY due_date
            """
            filtered_tasks = db.execute(query, (start.isoformat(), end.isoformat())).fetchall()
            filtered_tasks = [dict(task) for task in filtered_tasks]
        
        return jsonify({"tasks": filtered_tasks})
    else:
        data = request.get_json()
        if not data or 'task' not in data or 'due_date' not in data:
            return jsonify({"error": "Missing required fields"}), 400
        
        with get_db() as db:
            # Verify table exists
            try:
                db.execute("SELECT 1 FROM tasks LIMIT 1")
            except sqlite3.OperationalError as e:
                if "no such table" in str(e):
                    init_db()  # Reinitialize database if table is missing
                    return jsonify({"error": "Database was reinitialized, please try again"}), 500
                raise
            
            cursor = db.execute("""
                INSERT INTO tasks (task, due_date, priority, completed)
                VALUES (?, ?, ?, ?)
            """, (data['task'], data['due_date'], data.get('priority', 2), False))
            db.commit()
            task_id = cursor.lastrowid
            
            # Get the newly created task
            new_task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            new_task = dict(new_task)
        
        # Schedule reminders
        try:
            schedule_task_reminders(new_task)
        except Exception as e:
            print(f"Error scheduling reminders: {str(e)}")
        
        socketio.emit('task_update', {
            'action': 'added',
            'task': new_task
        })
        
        return jsonify({"message": "Task added successfully", "task": new_task}), 201

@app.route('/study_planner/tasks/<int:task_id>', methods=['PUT', 'DELETE'])
def handle_single_task(task_id):
    try:
        if request.method == 'PUT':
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
                
            with get_db() as db:
                # Verify table exists
                try:
                    db.execute("SELECT 1 FROM tasks LIMIT 1")
                except sqlite3.OperationalError as e:
                    if "no such table" in str(e):
                        init_db()  # Reinitialize database if table is missing
                        return jsonify({"error": "Database was reinitialized, please try again"}), 500
                    raise
                
                db.execute("""
                    UPDATE tasks 
                    SET completed = ?
                    WHERE id = ?
                """, (data.get('completed', False), task_id))
                db.commit()
                
                task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
                task = dict(task) if task else None
            
            if not task:
                return jsonify({"error": "Task not found"}), 404
                
            if task['completed']:
                try:
                    scheduler.remove_job(f"reminder_{task_id}_30min")
                    scheduler.remove_job(f"reminder_{task_id}_due")
                except:
                    pass
            
            socketio.emit('task_update', {
                'action': 'updated',
                'task': task
            })
            
            return jsonify({"message": "Task updated successfully"})
        else:
            with get_db() as db:
                # Verify table exists
                try:
                    db.execute("SELECT 1 FROM tasks LIMIT 1")
                except sqlite3.OperationalError as e:
                    if "no such table" in str(e):
                        init_db()  # Reinitialize database if table is missing
                        return jsonify({"error": "Database was reinitialized, please try again"}), 500
                    raise
                
                task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
                if not task:
                    return jsonify({"error": "Task not found"}), 404
                    
                db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                db.commit()
            
            try:
                scheduler.remove_job(f"reminder_{task_id}_30min")
                scheduler.remove_job(f"reminder_{task_id}_due")
            except:
                pass
            
            socketio.emit('task_update', {
                'action': 'deleted',
                'task_id': task_id
            })
            
            return jsonify({"message": "Task deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    # Send current task list to newly connected client
    with get_db() as db:
        try:
            tasks = db.execute("SELECT * FROM tasks").fetchall()
            emit('initial_tasks', {'tasks': [dict(task) for task in tasks]})
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                init_db()
                emit('initial_tasks', {'tasks': []})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')

if __name__ == '__main__':
    # Check if running in production (Render)
    if os.environ.get('FLASK_ENV') == 'production':
        print("Starting Raiden AI in production mode...")
        
        # Create necessary directories
        os.makedirs('static/js', exist_ok=True)
        os.makedirs('static/css', exist_ok=True)
        os.makedirs('static/images', exist_ok=True)
        os.makedirs('templates', exist_ok=True)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Initialize database
        try:
            with app.app_context():
                init_db()
                print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            exit(1)
        
        print("Starting Raiden AI server in production...")
        socketio.run(app, debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    else:
        # Development mode - clear data on startup for fresh memory
        print("Starting Raiden AI with fresh memory...")
        
        # Delete database file if it exists to start fresh
        if os.path.exists('raiden.db'):
            os.remove('raiden.db')
            print("Previous database cleared for fresh start")
        
        # Clear uploads folder
        if os.path.exists(UPLOAD_FOLDER):
            import shutil
            shutil.rmtree(UPLOAD_FOLDER)
            print("Uploads folder cleared")
        
        # Create necessary directories
        os.makedirs('static/js', exist_ok=True)
        os.makedirs('static/css', exist_ok=True)
        os.makedirs('static/images', exist_ok=True)
        os.makedirs('templates', exist_ok=True)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Initialize fresh database
        try:
            with app.app_context():
                init_db()
                print("Fresh database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            exit(1)
        
        print("Starting Raiden AI server with clean slate...")
        socketio.run(app, debug=True, port=5000)