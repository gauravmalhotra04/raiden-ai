document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const sidebar = document.querySelector('.sidebar');
    const navItems = document.querySelectorAll('.nav-item');
    const featurePanels = document.querySelectorAll('.feature-panel');
    const closePanelBtns = document.querySelectorAll('.close-panel');
    const chatContainer = document.getElementById('chat-container');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const voiceInputBtn = document.getElementById('voice-input-btn');
    const welcomeScreen = document.getElementById('welcome-screen');
    const aboutBtn = document.getElementById('about-btn');
    const recordBtn = document.getElementById('record-btn');
    const transcriptText = document.getElementById('transcript-text');
    const clearTranscriptBtn = document.getElementById('clear-transcript');
    const copyTranscriptBtn = document.getElementById('copy-transcript');
    const generateSlidesBtn = document.getElementById('generate-slides');
    const slidePreview = document.getElementById('slide-preview');

    // Feature Panel Elements
    const runCodeBtn = document.getElementById('runCodeBtn');
    const codeInput = document.getElementById('codeInput');
    const codeExplanation = document.getElementById('codeExplanation');
    const languageSelect = document.getElementById('languageSelect');
    const htmlPreview = document.getElementById('htmlPreview');
    const previewFrame = document.getElementById('previewFrame');
    const flashcard = document.getElementById('flashcard');
    const prevFlashcardBtn = document.getElementById('prev-flashcard');
    const nextFlashcardBtn = document.getElementById('next-flashcard');
    const flipFlashcardBtn = document.getElementById('flip-flashcard');
    const generateFlashcardsBtn = document.querySelector('.add-task-btn');
    const mathInput = document.querySelector('#math-panel textarea');
    const solveMathBtn = document.querySelector('#math-panel .run-code');
    const mathSolution = document.querySelector('#math-panel .code-output');
    const mathSymbolBtns = document.querySelectorAll('.math-symbol-btn');
    const pdfUploadBtn = document.querySelector('#pdf-panel .add-task-btn');
    const citationGenerateBtn = document.querySelector('#citations-panel .run-code');
    const addTaskBtn = document.getElementById('addTaskBtn');
    const taskList = document.getElementById('taskList');
    const completedCount = document.getElementById('completed-count');
    const pendingCount = document.getElementById('pending-count');
    const plannerNavBtns = document.querySelectorAll('.planner-nav-btn');

    // State Variables
    let isRecording = false;
    let recognition;
    let flashcardIndex = 0;
    let flashcards = [];
    let currentTasks = [];
    let transcriptSessionId = null;

    // Initialize all modules
    initSidebar();
    initChat();
    initVoiceInput();
    initCodePlayground();
    initFlashcards();
    initMathSolver();
    initPDFSummarizer();
    initStudyPlanner();
    initLectureTranscriber();
    initAttendanceTracker();
    initWebSocket();

    // ===== Sidebar Navigation =====
    function initSidebar() {
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                navItems.forEach(navItem => navItem.classList.remove('active'));
                item.classList.add('active');
                const panelId = item.getAttribute('data-panel') + '-panel';
                showPanel(panelId);
            });
        });

        closePanelBtns.forEach(btn => {
            btn.addEventListener('click', closeAllPanels);
        });

        aboutBtn.addEventListener('click', () => showPanel('about-panel'));
    }

    function showPanel(panelId) {
        featurePanels.forEach(panel => panel.classList.remove('active'));
        const panel = document.getElementById(panelId);
        if (panel) panel.classList.add('active');

        if (panelId === 'citations-panel') {
            initCitationGenerator();
        }

        if (window.innerWidth <= 992) sidebar.classList.remove('active');
    }

    function closeAllPanels() {
        featurePanels.forEach(panel => panel.classList.remove('active'));
    }

    // ===== Chat Functionality =====
    function initChat() {
        sendBtn.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Auto-resize textarea
        messageInput.addEventListener('input', autoResize);
        messageInput.addEventListener('focus', autoResize);
    }
    
    function autoResize() {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
    }

    function sendMessage() {
        const message = messageInput.value.trim();
        if (message) {
            // Check if message contains code patterns
            const codePatterns = [
                /```[\s\S]*?```/, // Code blocks
                /def\s+\w+\s*\(/, // Python functions
                /function\s+\w+\s*\(/, // JavaScript functions
                /#include\s*</, // C includes
                /<html/i, // HTML tags
                /console\.log/, // JavaScript console
                /print\s*\(/, // Python print
                /printf\s*\(/, // C printf
                /int\s+main\s*\(/, // C main function
                /class\s+\w+/, // Classes
                /import\s+/, // Imports
                /const\s+|let\s+|var\s+/, // Variable declarations
            ];
            
            const containsCode = codePatterns.some(pattern => pattern.test(message));
            
            if (welcomeScreen.style.display !== 'none') welcomeScreen.style.display = 'none';
            addMessage(message, 'user');
            messageInput.value = '';
            showTypingIndicator();
            
            // Auto-open code playground if code is detected
            if (containsCode) {
                setTimeout(() => {
                    const codePanel = document.getElementById('code-panel');
                    if (codePanel) {
                        codePanel.classList.add('active');
                        // Set focus to code input
                        setTimeout(() => {
                            const codeInput = document.getElementById('codeInput');
                            if (codeInput) {
                                codeInput.focus();
                                // Auto-paste the code
                                codeInput.value = message;
                            }
                        }, 100);
                    }
                }, 500);
            }
            
            fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            })
            .then(response => response.json())
            .then(data => {
                hideTypingIndicator();
                if (data.error) {
                    showError(data.error);
                    return;
                }
                addMessage(data.response, 'ai');
                scrollToBottom();
            })
            .catch(error => {
                hideTypingIndicator();
                showError("Sorry, I encountered an error. Please try again.");
                console.error('Error:', error);
            });
        }
    }

    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Clean up markdown formatting if present
        const cleanedText = cleanMarkdownFormatting(text);
        
        messageDiv.innerHTML = `${cleanedText}<div class="message-time">Today, ${timeString}</div>`;
        chatContainer.insertBefore(messageDiv, chatContainer.lastElementChild);
        scrollToBottom();
    }

    function cleanMarkdownFormatting(text) {
        return text
            // Remove markdown headers
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            // Remove bold markdown
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Remove italic markdown
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Remove code markdown
            .replace(/`(.*?)`/g, '<code>$1</code>')
            // Remove strikethrough
            .replace(/~~(.*?)~~/g, '<del>$1</del>')
            // Convert line breaks to proper spacing
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            // Wrap in paragraphs if not already wrapped
            .replace(/^(?!<[h|p|u|o|b|d|p])(.*?)(?=<[h|p|u|o|b|d|p]|$)/gm, '<p>$1</p>')
            // Clean up empty paragraphs
            .replace(/<p><\/p>/g, '')
            .replace(/<p>(.*?)<\/p>/g, (match, content) => {
                if (content.trim()) return match;
                return '';
            });
    }

    function showTypingIndicator() {
        const typingIndicator = document.querySelector('.typing-indicator');
        if (typingIndicator) typingIndicator.style.display = 'flex';
    }

    function hideTypingIndicator() {
        const typingIndicator = document.querySelector('.typing-indicator');
        if (typingIndicator) typingIndicator.style.display = 'none';
    }

    function scrollToBottom() {
        chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
    }

    // ===== Voice Input =====
    function initVoiceInput() {
        if ('webkitSpeechRecognition' in window) {
            const recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            
            voiceInputBtn.addEventListener('click', () => {
                if (voiceInputBtn.classList.contains('recording')) {
                    recognition.stop();
                    voiceInputBtn.classList.remove('recording');
                    voiceInputBtn.innerHTML = '<i class="fas fa-microphone"></i>';
                } else {
                    recognition.start();
                    voiceInputBtn.classList.add('recording');
                    voiceInputBtn.innerHTML = '<i class="fas fa-microphone-slash"></i>';
                }
            });

            recognition.onresult = (event) => {
                messageInput.value = event.results[0][0].transcript;
                voiceInputBtn.classList.remove('recording');
                voiceInputBtn.innerHTML = '<i class="fas fa-microphone"></i>';
            };

            recognition.onerror = (event) => {
                console.error('Speech recognition error', event.error);
                voiceInputBtn.classList.remove('recording');
                voiceInputBtn.innerHTML = '<i class="fas fa-microphone"></i>';
                showError('Voice input error: ' + event.error);
            };
        } else {
            voiceInputBtn.style.display = 'none';
            console.log('Speech recognition not supported');
        }
    }

    // ===== Code Playground =====
    function initCodePlayground() {
        runCodeBtn.addEventListener('click', runCode);
    }

    async function runCode() {
        const code = codeInput.value.trim();
        const language = languageSelect.value;
        
        if (!code) {
            codeExplanation.innerHTML = '<div style="color: #aaa;">Please enter some code to execute</div>';
            return;
        }

        runCodeBtn.disabled = true;
        runCodeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running...';
        
        // Hide HTML preview for non-HTML code
        if (language !== 'html') {
            htmlPreview.style.display = 'none';
        }
        
        try {
            const response = await fetch('/code_playground/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, language })
            });
            
            const data = await response.json();
            
            if (data.error) {
                codeExplanation.innerHTML = `
                    <h4><i class="fas fa-lightbulb"></i> Code Analysis</h4>
                    <div style="color: #ff4757;">Error: ${data.error}</div>
                `;
            } else {
                // Format the output and explanation together
                let outputContent = data.output;
                let outputSection = '';
                
                // Use the AI-generated result statement
                const resultStatement = data.result_statement || 'No result statement available';
                outputSection = `
                    <div style="margin-bottom: 15px;">
                        <div style="color: var(--accent); font-weight: 600; font-size: 15px; margin-bottom: 8px;">
                            <i class="fas fa-terminal"></i> Result:
                        </div>
                        <div style="white-space: pre-wrap; line-height: 1.5; font-family: 'Courier New', monospace; background: rgba(30, 30, 45, 0.8); padding: 12px; border-radius: 8px; border: 1px solid rgba(170, 126, 238, 0.3); font-size: 14px; color: #e0e0e0;">${resultStatement}</div>
                    </div>
                `;
                
                // Format the explanation with proper HTML
                const formattedExplanation = data.explanation || 'No explanation provided';
                codeExplanation.innerHTML = `
                    ${outputSection}
                    <h4><i class="fas fa-lightbulb"></i> Code Analysis</h4>
                    <div style="white-space: pre-wrap; line-height: 1.6; font-size: 15px; color: rgba(255, 255, 255, 0.9);">${formattedExplanation}</div>
                `;
                
                // Show HTML preview for HTML code
                if (language === 'html') {
                    htmlPreview.style.display = 'block';
                    const blob = new Blob([code], { type: 'text/html' });
                    const url = URL.createObjectURL(blob);
                    previewFrame.src = url;
                }
            }
        } catch (error) {
            console.error('Error:', error);
            codeExplanation.innerHTML = `
                <h4><i class="fas fa-lightbulb"></i> Code Analysis</h4>
                <div style="color: #ff4757;">Failed to execute code</div>
            `;
        } finally {
            runCodeBtn.disabled = false;
            runCodeBtn.innerHTML = 'Run & Analyze';
        }
    }

    // ===== Math Solver =====
    function initMathSolver() {
        solveMathBtn.addEventListener('click', solveMath);
        
        mathSymbolBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                mathInput.value += btn.textContent;
            });
        });
    }

    function solveMath() {
        const equation = mathInput.value.trim();
        if (!equation) {
            document.getElementById('math-result-block').innerHTML = '<div style="color: #aaa;">Please enter an equation</div>';
            document.getElementById('math-explanation-block').innerHTML = '';
            return;
        }

        solveMathBtn.disabled = true;
        solveMathBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Solving...';

        fetch('/solve_math', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ equation })
        })
        .then(response => response.json())
        .then(data => {
            const resultBlock = document.getElementById('math-result-block');
            const explanationBlock = document.getElementById('math-explanation-block');
            if (data.error) {
                resultBlock.innerHTML = `<div style="background: rgba(255, 71, 87, 0.15); color: #ff4757; border: 1px solid #ff4757; border-radius: 8px; padding: 12px 24px; font-weight: 600; display: inline-block; text-align: center;">${data.error}</div>`;
                explanationBlock.innerHTML = '';
            } else {
                // Format result as a single green block, centered
                const formattedSolution = data.solution || 'No solution available';
                const formattedExplanation = data.explanation || '';
                const isError = formattedSolution.includes('Calculation Error') || formattedSolution.includes('Error');
                resultBlock.innerHTML = `<div style="background: ${isError ? 'rgba(255, 71, 87, 0.15)' : 'rgba(76, 209, 55, 0.15)'}; color: ${isError ? '#ff4757' : '#4cd137'}; border: 1px solid ${isError ? '#ff4757' : '#4cd137'}; border-radius: 8px; padding: 12px 24px; font-weight: 600; display: inline-block; text-align: center;">${formattedSolution}</div>`;
                // Remove 'Detailed Solution' header and bring 'Problem Analysis' to top
                let explanationHTML = formattedExplanation;
                explanationHTML = explanationHTML.replace(/<div[^>]*class=["']?math-explanation-header["']?[^>]*>.*?<\/div>/gi, ''); // Remove header if present
                explanationHTML = explanationHTML.replace(/<h3>Detailed Solution<\/h3>/gi, ''); // Remove header if present
                // Move 'Problem Analysis' to top if not already
                explanationBlock.innerHTML = explanationHTML;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('math-result-block').innerHTML = '<div style="color: #ff4757;">Failed to solve equation</div>';
            document.getElementById('math-explanation-block').innerHTML = '';
        })
        .finally(() => {
            solveMathBtn.disabled = false;
            solveMathBtn.innerHTML = 'Solve';
        });
    }

    // ===== PDF Summarizer =====
    function initPDFSummarizer() {
        pdfUploadBtn.addEventListener('click', () => {
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = '.pdf';
            
            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (!file) return;
                
                const formData = new FormData();
                formData.append('file', file);
                
                pdfUploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                
                fetch('/summarize_pdf', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        showError(data.error);
                    } else {
                        // Format the summary with proper structure
                        const formattedSummary = data.summary || 'No summary generated';
                        addMessage(`
                            <div style="margin-bottom: 15px;">
                                <h3 style="color: var(--accent); margin-bottom: 15px;">
                                    <i class="fas fa-file-pdf"></i> PDF Summary: ${file.name}
                                </h3>
                                <div style="white-space: pre-wrap; line-height: 1.6;">
                                    ${formattedSummary}
                                </div>
                            </div>
                        `, 'ai');
                        scrollToBottom();
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showError('Failed to summarize PDF');
                })
                .finally(() => {
                    pdfUploadBtn.innerHTML = '<i class="fas fa-file-upload"></i> Upload PDF';
                });
            });
            
            fileInput.click();
        });
    }

    // ===== Study Planner =====
    function initStudyPlanner() {
        loadTasks('today');
        
        addTaskBtn.addEventListener('click', showAddTaskModal);
        
        plannerNavBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                plannerNavBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                loadTasks(btn.dataset.period);
            });
        });
    }

    function loadTasks(period) {
        taskList.innerHTML = '<div class="loading">Loading tasks...</div>';
        
        fetch(`/study_planner/tasks?period=${period}`)
            .then(response => response.json())
            .then(data => {
                currentTasks = data.tasks || [];
                renderTasks(currentTasks);
                updateTaskStats();
            })
            .catch(error => {
                console.error('Error loading tasks:', error);
                taskList.innerHTML = '<div class="error-message">Failed to load tasks</div>';
            });
    }

    function renderTasks(tasks) {
        if (tasks.length === 0) {
            taskList.innerHTML = `
                <div class="no-tasks">
                    <i class="fas fa-calendar-plus"></i>
                    <p>No tasks found</p>
                    <button class="add-first-task" id="addFirstTask">Add Your First Task</button>
                </div>
            `;
            document.getElementById('addFirstTask').addEventListener('click', showAddTaskModal);
            return;
        }

        taskList.innerHTML = '';
        tasks.forEach(task => {
            const taskElement = document.createElement('div');
            taskElement.className = `task-item ${task.completed ? 'task-completed' : ''}`;
            taskElement.innerHTML = `
                <div class="task-info">
                    <input type="checkbox" class="task-checkbox" ${task.completed ? 'checked' : ''} 
                        data-task-id="${task.id}">
                    <div class="task-details">
                        <div class="task-title">${task.task}</div>
                        <div class="task-due">Due: ${formatDate(task.due_date)}</div>
                    </div>
                </div>
                <div class="task-actions">
                    <button class="task-action-btn delete-task" data-task-id="${task.id}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            taskList.appendChild(taskElement);
        });

        // Add event listeners
        document.querySelectorAll('.task-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', toggleTaskCompletion);
        });

        document.querySelectorAll('.delete-task').forEach(btn => {
            btn.addEventListener('click', deleteTask);
        });
    }

    function toggleTaskCompletion(e) {
        const taskId = e.target.dataset.taskId;
        const completed = e.target.checked;
        const taskTitle = e.target.closest('.task-item').querySelector('.task-title').textContent;
        
        fetch(`/study_planner/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ completed })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.message) {
                loadTasks(document.querySelector('.planner-nav-btn.active').dataset.period);
                showTaskNotification(`Task marked as ${completed ? 'completed' : 'pending'}: "${taskTitle}"`, 'success');
            }
        })
        .catch(error => {
            console.error('Error updating task:', error);
            showError('Failed to update task');
            e.target.checked = !completed; // Revert checkbox
        });
    }

    function deleteTask(e) {
        const taskId = e.currentTarget.dataset.taskId;
        const taskTitle = e.currentTarget.closest('.task-item').querySelector('.task-title').textContent;
        
        if (!confirm('Are you sure you want to delete this task?')) return;
        
        fetch(`/study_planner/tasks/${taskId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                loadTasks(document.querySelector('.planner-nav-btn.active').dataset.period);
                showTaskNotification(`Task deleted: "${taskTitle}"`, 'success');
            }
        })
        .catch(error => {
            console.error('Error deleting task:', error);
            showError('Failed to delete task');
        });
    }

    function showAddTaskModal() {
        const existingModal = document.querySelector('.task-modal');
        if (existingModal) existingModal.remove();

        const modalHTML = `
            <div class="task-modal">
                <div class="modal-content">
                    <h3>Add New Task</h3>
                    <div class="form-group">
                        <label>Task Description</label>
                        <input type="text" id="taskDescription" placeholder="What needs to be done?">
                    </div>
                    <div class="form-group">
                        <label>Due Date & Time</label>
                        <input type="datetime-local" id="taskDueDate">
                    </div>
                    <div class="form-group">
                        <label>Priority</label>
                        <select id="taskPriority">
                            <option value="1">Low</option>
                            <option value="2">Medium</option>
                            <option value="3">High</option>
                        </select>
                    </div>
                    <div class="modal-actions">
                        <button class="modal-btn cancel-btn" id="cancelTask">Cancel</button>
                        <button class="modal-btn confirm-btn" id="saveTask">Save Task</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);

        document.getElementById('cancelTask').addEventListener('click', () => {
            document.querySelector('.task-modal').remove();
        });

        document.getElementById('saveTask').addEventListener('click', saveTask);
    }

    function saveTask() {
        const description = document.getElementById('taskDescription').value;
        const dueDate = document.getElementById('taskDueDate').value;
        const priority = document.getElementById('taskPriority').value;
        
        if (!description || !dueDate) {
            showError('Please fill in all required fields');
            return;
        }
        
        fetch('/study_planner/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                task: description, 
                due_date: dueDate, 
                priority 
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                document.querySelector('.task-modal').remove();
                loadTasks(document.querySelector('.planner-nav-btn.active').dataset.period);
                showNotification('Task added successfully!', 'success');
            }
        })
        .catch(error => {
            console.error('Error adding task:', error);
            showError('Failed to add task');
        });
    }

    function updateTaskStats() {
        const completed = currentTasks.filter(task => task.completed).length;
        const pending = currentTasks.length - completed;
        
        completedCount.textContent = completed;
        pendingCount.textContent = pending;
    }

    function formatDate(dateString) {
        const options = { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric',
            hour: '2-digit', 
            minute: '2-digit' 
        };
        return new Date(dateString).toLocaleDateString('en-US', options);
    }

    // ===== Lecture Transcriber =====
    function initLectureTranscriber() {
        const clearBtn = document.getElementById('clear-transcript');
        const copyBtn = document.getElementById('copy-transcript');
        const generateSlidesBtn = document.getElementById('generate-slides');
        const recordingStatus = document.getElementById('recording-status');
        const statusIndicator = recordingStatus?.querySelector('.status-indicator');
        const statusText = recordingStatus?.querySelector('.status-text');

        if ('webkitSpeechRecognition' in window) {
            recognition = new webkitSpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onresult = (event) => {
                let interimTranscript = '';
                let finalTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript + ' ';
                    } else {
                        interimTranscript += transcript;
                    }
                }

                const transcriptText = document.getElementById('transcript-text');
                if (finalTranscript || interimTranscript) {
                    transcriptText.innerHTML = finalTranscript + interimTranscript;
                }
            };

            recognition.onerror = (event) => {
                console.error('Speech recognition error', event.error);
                stopRecording();
                showError('Voice input error: ' + event.error);
            };

            recognition.onend = () => {
                if (isRecording) {
                    recognition.start();
                }
            };

            recordBtn.addEventListener('click', toggleRecording);
            clearBtn.addEventListener('click', clearTranscript);
            copyBtn.addEventListener('click', copyTranscript);
            generateSlidesBtn.addEventListener('click', generateSlidesFromTranscript);
        } else {
            recordBtn.style.display = 'none';
            const transcriptText = document.getElementById('transcript-text');
            transcriptText.innerHTML = `
                <div class="transcript-placeholder">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Speech recognition not supported in your browser. Please try Chrome or Edge.</p>
                </div>
            `;
        }
    }

    function toggleRecording() {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    }

    function startRecording() {
        isRecording = true;
        recordBtn.classList.add('recording');
        recordBtn.innerHTML = '<i class="fas fa-stop"></i><span class="btn-text">Stop Recording</span>';
        
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');
        if (statusIndicator) statusIndicator.classList.add('recording');
        if (statusText) statusText.textContent = 'Recording...';
        
        const transcriptText = document.getElementById('transcript-text');
        transcriptText.innerHTML = '<div style="color: var(--accent);">Listening... (Recording in progress)</div>';
        
        recognition.start();
        
        fetch('/transcribe/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            transcriptSessionId = data.session_id;
        })
        .catch(error => {
            console.error('Error starting transcription:', error);
        });
    }

    function stopRecording() {
        isRecording = false;
        recordBtn.classList.remove('recording');
        recordBtn.innerHTML = '<i class="fas fa-microphone"></i><span class="btn-text">Start Recording</span>';
        
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');
        if (statusIndicator) statusIndicator.classList.remove('recording');
        if (statusText) statusText.textContent = 'Ready to record';
        
        recognition.stop();
        
        if (transcriptSessionId) {
            fetch('/transcribe/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: transcriptSessionId })
            })
            .catch(error => {
                console.error('Error stopping transcription:', error);
            });
        }
    }

    function clearTranscript() {
        const transcriptText = document.getElementById('transcript-text');
        transcriptText.innerHTML = `
            <div class="transcript-placeholder">
                <i class="fas fa-microphone-slash"></i>
                <p>Click "Start Recording" to begin transcription...</p>
            </div>
        `;
        
        const slidePreview = document.getElementById('slide-preview');
        slidePreview.innerHTML = `
            <div class="slide-preview-placeholder">
                <i class="fas fa-file-powerpoint"></i>
                <p>Generated slides will appear here...</p>
            </div>
        `;
    }

    function copyTranscript() {
        const transcript = document.getElementById('transcript-text').textContent;
        if (!transcript || transcript.includes('Click "Start Recording"')) {
            showError('No transcript to copy');
            return;
        }
        
        navigator.clipboard.writeText(transcript)
            .then(() => {
                const copyBtn = document.getElementById('copy-transcript');
                const originalHTML = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => { 
                    copyBtn.innerHTML = originalHTML; 
                }, 2000);
                showNotification('Transcript copied to clipboard!', 'success');
            })
            .catch(error => {
                console.error('Failed to copy transcript:', error);
                showError('Failed to copy transcript');
            });
    }

    function generateSlidesFromTranscript() {
        const transcript = document.getElementById('transcript-text').textContent;
        if (!transcript || transcript.includes('Click "Start Recording"')) {
            showError('Please record some audio first');
            return;
        }

        generateSlidesBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        generateSlidesBtn.disabled = true;
        
        const formData = new FormData();
        formData.append('transcript', transcript);
        
        fetch('/transcribe/generate_slides', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
            } else {
                slidePreview.innerHTML = `
                    <div class="slides-preview-header">
                        <h3><i class="fas fa-file-powerpoint"></i> Generated Slides Preview</h3>
                        <div class="slides-actions">
                            <button class="slide-action-btn" onclick="exportSlides()">
                                <i class="fas fa-download"></i> Export
                            </button>
                            <button class="slide-action-btn" onclick="copySlides()">
                                <i class="fas fa-copy"></i> Copy
                            </button>
                        </div>
                    </div>
                    <div class="slides-container">
                        ${formatSlides(data.slides)}
                    </div>
                `;
                showNotification('Slides generated successfully!', 'success');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Failed to generate slides');
        })
        .finally(() => {
            generateSlidesBtn.innerHTML = '<i class="fas fa-file-powerpoint"></i> Generate Slides';
            generateSlidesBtn.disabled = false;
        });
    }

    function formatSlides(slidesText) {
        // Split the text into slides based on markdown headers
        const slides = slidesText.split(/(?=^#\s+)/m).filter(slide => slide.trim());
        
        return slides.map((slide, index) => {
            const lines = slide.trim().split('\n');
            const title = lines[0].replace(/^#\s+/, '');
            const content = lines.slice(1).join('\n');
            
            return `
                <div class="slide" data-slide="${index + 1}">
                    <div class="slide-header">
                        <div class="slide-number">Slide ${index + 1}</div>
                        <div class="slide-title">${title}</div>
                    </div>
                    <div class="slide-content">
                        ${formatSlideContent(content)}
                    </div>
                </div>
            `;
        }).join('');
    }

    function formatSlideContent(content) {
        if (!content.trim()) return '<p class="slide-empty">No content</p>';
        
        return content
            .replace(/^-\s+(.*$)/gm, '<li>$1</li>')
            .replace(/^•\s+(.*$)/gm, '<li>$1</li>')
            .replace(/^(\d+\.)\s+(.*$)/gm, '<li>$1 $2</li>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/<li>.*?<\/li>/g, match => {
                // Group consecutive list items
                const items = match.match(/<li>.*?<\/li>/g);
                if (items && items.length > 1) {
                    return `<ul>${items.join('')}</ul>`;
                }
                return `<ul>${match}</ul>`;
            })
            .replace(/^(?!<[uo]l>|<li>)(.*?)(?=<[uo]l>|<li>|$)/gm, '<p>$1</p>')
            .replace(/<p><\/p>/g, '')
            .replace(/<p>(.*?)<\/p>/g, (match, content) => {
                if (content.trim()) return match;
                return '';
            });
    }

    // Add global functions for slide actions
    window.exportSlides = function() {
        const slidesContent = document.querySelector('.slides-container').innerText;
        const blob = new Blob([slidesContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'lecture-slides.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showNotification('Slides exported successfully!', 'success');
    };

    window.copySlides = function() {
        const slidesContent = document.querySelector('.slides-container').innerText;
        navigator.clipboard.writeText(slidesContent)
            .then(() => {
                showNotification('Slides copied to clipboard!', 'success');
            })
            .catch(error => {
                console.error('Failed to copy slides:', error);
                showError('Failed to copy slides');
            });
    };

    // ===== Attendance Tracker =====
    function initAttendanceTracker() {
        const calendarContainer = document.querySelector('.attendance-calendar');
        const exportBtn = document.querySelector('.attendance-actions button:first-child');
        const addRecordBtn = document.querySelector('.attendance-actions button:last-child');
        const statsContainer = document.querySelector('.attendance-stats');
        const currentMonthDisplay = document.getElementById('current-month');
        const prevMonthBtn = document.getElementById('prev-month');
        const nextMonthBtn = document.getElementById('next-month');
        
        let currentDate = new Date();
        let attendanceRecords = [];
        
        // Initialize calendar with current month
        renderCalendar(currentDate.getFullYear(), currentDate.getMonth() + 1);
        
        // Add navigation event listeners
        prevMonthBtn.addEventListener('click', () => {
            currentDate.setMonth(currentDate.getMonth() - 1);
            renderCalendar(currentDate.getFullYear(), currentDate.getMonth() + 1);
        });
        
        nextMonthBtn.addEventListener('click', () => {
            currentDate.setMonth(currentDate.getMonth() + 1);
            renderCalendar(currentDate.getFullYear(), currentDate.getMonth() + 1);
        });
        
        exportBtn.addEventListener('click', exportAttendance);
        addRecordBtn.addEventListener('click', showAddRecordModal);
        
        const socket = io();
        socket.on('attendance_update', handleAttendanceUpdate);
        
        function renderCalendar(year, month) {
            calendarContainer.innerHTML = '';
            
            // Update month display
            const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                               'July', 'August', 'September', 'October', 'November', 'December'];
            currentMonthDisplay.textContent = `${monthNames[month - 1]} ${year}`;
            
            const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
            days.forEach(day => {
                const header = document.createElement('div');
                header.className = 'calendar-header';
                header.textContent = day;
                calendarContainer.appendChild(header);
            });
            
            const firstDay = new Date(year, month - 1, 1).getDay();
            const daysInMonth = new Date(year, month, 0).getDate();
            
            for (let i = 0; i < firstDay; i++) {
                const emptyCell = document.createElement('div');
                emptyCell.className = 'calendar-day empty';
                calendarContainer.appendChild(emptyCell);
            }
            
            for (let day = 1; day <= daysInMonth; day++) {
                const dateStr = `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
                const dayCell = document.createElement('div');
                dayCell.className = 'calendar-day';
                dayCell.textContent = day;
                dayCell.dataset.date = dateStr;
                
                const today = new Date();
                if (year === today.getFullYear() && month === today.getMonth() + 1 && day === today.getDate()) {
                    dayCell.classList.add('today');
                }
                
                const record = attendanceRecords.find(r => r.date === dateStr);
                if (record) {
                    dayCell.classList.add(record.status);
                    dayCell.title = record.notes || record.status;
                }
                
                dayCell.addEventListener('click', () => showDayDetails(dateStr));
                calendarContainer.appendChild(dayCell);
            }
            
            loadAttendanceData(year, month);
        }
        
        function loadAttendanceData(year, month) {
            fetch(`/attendance?year=${year}&month=${month}`)
                .then(response => response.json())
                .then(data => {
                    attendanceRecords = data.attendance;
                    updateStats(data.stats);
                    highlightCalendarDays();
                })
                .catch(error => {
                    console.error('Error loading attendance data:', error);
                });
        }
        
        function updateStats(stats) {
            const total = stats.total || 0;
            const present = stats.present || 0;
            const absent = stats.absent || 0;
            const late = stats.late || 0;
            
            const presentPercentage = total > 0 ? Math.round((present / total) * 100) : 0;
            const absentPercentage = total > 0 ? Math.round((absent / total) * 100) : 0;
            
            statsContainer.innerHTML = `
                <div class="stat-card">
                    <div class="stat-value">${presentPercentage}%</div>
                    <div class="stat-label">Present</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${absentPercentage}%</div>
                    <div class="stat-label">Absent</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${late}</div>
                    <div class="stat-label">Late</div>
                </div>
            `;
        }
        
        function highlightCalendarDays() {
            document.querySelectorAll('.calendar-day').forEach(dayCell => {
                const dateStr = dayCell.dataset.date;
                if (dateStr) {
                    const record = attendanceRecords.find(r => r.date === dateStr);
                    if (record) {
                        dayCell.classList.add(record.status);
                        dayCell.title = record.notes || record.status;
                    } else {
                        dayCell.className = 'calendar-day';
                        if (dayCell.classList.contains('today')) {
                            dayCell.classList.add('today');
                        }
                    }
                }
            });
        }
        
        function showDayDetails(dateStr) {
            const record = attendanceRecords.find(r => r.date === dateStr);
            const date = new Date(dateStr);
            const dateFormatted = date.toLocaleDateString('en-US', { 
                weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' 
            });
            
            const modalHTML = `
                <div class="attendance-modal">
                    <div class="modal-content">
                        <h3>Attendance for ${dateFormatted}</h3>
                        <div class="form-group">
                            <label>Status</label>
                            <select id="attendance-status">
                                <option value="present" ${record?.status === 'present' ? 'selected' : ''}>Present</option>
                                <option value="absent" ${record?.status === 'absent' ? 'selected' : ''}>Absent</option>
                                <option value="late" ${record?.status === 'late' ? 'selected' : ''}>Late</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Notes</label>
                            <textarea id="attendance-notes">${record?.notes || ''}</textarea>
                        </div>
                        <div class="modal-actions">
                            ${record ? `<button class="modal-btn delete-btn" id="delete-attendance">Delete Record</button>` : ''}
                            <button class="modal-btn cancel-btn" id="cancel-attendance">Cancel</button>
                            <button class="modal-btn confirm-btn" id="save-attendance">Save</button>
                        </div>
                    </div>
                </div>
            `;
            
            const existingModal = document.querySelector('.attendance-modal');
            if (existingModal) existingModal.remove();
            
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            document.getElementById('cancel-attendance').addEventListener('click', () => {
                document.querySelector('.attendance-modal').remove();
            });
            
            document.getElementById('save-attendance').addEventListener('click', () => {
                saveAttendanceRecord(dateStr);
            });
            
            if (record) {
                document.getElementById('delete-attendance').addEventListener('click', () => {
                    deleteAttendanceRecord(record.id);
                });
            }
        }
        
        function saveAttendanceRecord(dateStr) {
            const status = document.getElementById('attendance-status').value;
            const notes = document.getElementById('attendance-notes').value;
            
            fetch('/attendance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date: dateStr, status, notes })
            })
            .then(response => response.json())
            .then(data => {
                document.querySelector('.attendance-modal').remove();
                showNotification(`Attendance record ${data.message}`, 'success');
            })
            .catch(error => {
                console.error('Error saving attendance:', error);
                showError('Failed to save attendance record');
            });
        }
        
        function deleteAttendanceRecord(recordId) {
            if (!confirm('Are you sure you want to delete this attendance record?')) return;
            
            fetch(`/attendance/${recordId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                document.querySelector('.attendance-modal').remove();
                showNotification('Attendance record deleted', 'success');
            })
            .catch(error => {
                console.error('Error deleting attendance:', error);
                showError('Failed to delete attendance record');
            });
        }
        
        function exportAttendance() {
            const year = currentDate.getFullYear();
            const month = currentDate.getMonth() + 1;
            
            window.open(`/attendance/export?year=${year}&month=${month}&format=csv`, '_blank');
        }
        
        function showAddRecordModal() {
            const today = new Date().toISOString().split('T')[0];
            
            const modalHTML = `
                <div class="attendance-modal">
                    <div class="modal-content">
                        <h3>Add New Attendance Record</h3>
                        <div class="form-group">
                            <label>Date</label>
                            <input type="date" id="attendance-date" value="${today}">
                        </div>
                        <div class="form-group">
                            <label>Status</label>
                            <select id="attendance-status">
                                <option value="present">Present</option>
                                <option value="absent">Absent</option>
                                <option value="late">Late</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Notes</label>
                            <textarea id="attendance-notes"></textarea>
                        </div>
                        <div class="modal-actions">
                            <button class="modal-btn cancel-btn" id="cancel-attendance">Cancel</button>
                            <button class="modal-btn confirm-btn" id="save-attendance">Save</button>
                        </div>
                    </div>
                </div>
            `;
            
            const existingModal = document.querySelector('.attendance-modal');
            if (existingModal) existingModal.remove();
            
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            document.getElementById('cancel-attendance').addEventListener('click', () => {
                document.querySelector('.attendance-modal').remove();
            });
            
            document.getElementById('save-attendance').addEventListener('click', () => {
                const dateStr = document.getElementById('attendance-date').value;
                saveAttendanceRecord(dateStr);
            });
        }
        
        function handleAttendanceUpdate(data) {
            if (data.action === 'added' || data.action === 'updated') {
                const index = attendanceRecords.findIndex(r => r.id === data.record.id);
                if (index >= 0) {
                    attendanceRecords[index] = data.record;
                } else {
                    attendanceRecords.push(data.record);
                }
            } else if (data.action === 'deleted') {
                attendanceRecords = attendanceRecords.filter(r => r.id !== data.record_id);
            }
            
            const recordDate = data.action !== 'deleted' ? new Date(data.record.date) : null;
            const currentYear = currentDate.getFullYear();
            const currentMonth = currentDate.getMonth() + 1;
            
            if (!recordDate || (recordDate.getFullYear() === currentYear && recordDate.getMonth() + 1 === currentMonth)) {
                loadAttendanceData(currentYear, currentMonth);
            }
        }
    }

    // ===== WebSocket Notifications =====
    function initWebSocket() {
        const socket = io(window.location.origin);
        
        socket.on('connect', () => {
            console.log('Connected to WebSocket server');
        });
        
        socket.on('disconnect', () => {
            console.log('Disconnected from WebSocket server');
            setTimeout(initWebSocket, 5000);
        });
        
        socket.on('connect_error', (error) => {
            console.log('WebSocket connection error:', error);
        });
        
        socket.on('task_update', (data) => {
            console.log('Task update:', data);
            switch(data.action) {
                case 'added':
                    showTaskNotification(`New task added: "${data.task.task}"`, 'success');
                    break;
                case 'updated':
                    showTaskNotification(`Task marked as ${data.task.completed ? 'completed' : 'pending'}: "${data.task.task}"`, 'success');
                    break;
                case 'deleted':
                    showTaskNotification(`Task deleted`, 'success');
                    break;
            }
        });
        
        socket.on('task_reminder', (data) => {
            console.log('Received reminder:', data);
            if (data.is_due) {
                showDueNotification(`Task is due now: "${data.task}"`, data.task_id);
            } else {
                const dueTime = new Date(data.due_date);
                const timeString = dueTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                showNotification(`Reminder: "${data.task}" is due at ${timeString}`, data.task_id);
            }
        });
    }

    function showTaskNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type === 'due' ? 'due-notification' : type === 'success' ? 'success-notification' : ''}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas ${type === 'due' ? 'fa-exclamation-circle' : type === 'success' ? 'fa-check-circle' : 'fa-info-circle'}"></i>
                <span>${message}</span>
            </div>
        `;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 500);
        }, 5000);
    }

    function showDueNotification(message, taskId) {
        document.querySelectorAll('.notification').forEach(notification => {
            if (notification.dataset.taskId === taskId?.toString()) {
                notification.remove();
            }
        });
        
        const notification = document.createElement('div');
        notification.className = 'notification due-notification';
        notification.dataset.taskId = taskId;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-exclamation-circle"></i>
                <span>${message}</span>
                <button class="mark-complete-btn">Mark Complete</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        notification.querySelector('.mark-complete-btn').addEventListener('click', () => {
            markTaskComplete(taskId);
            notification.remove();
        });
        
        setTimeout(() => {
            if (document.body.contains(notification)) {
                notification.classList.add('fade-out');
                setTimeout(() => notification.remove(), 500);
            }
        }, 30000);
    }

    function markTaskComplete(taskId) {
        fetch(`/study_planner/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ completed: true })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                loadTasks(document.querySelector('.planner-nav-btn.active').dataset.period);
            }
        })
        .catch(error => {
            console.error('Error updating task:', error);
            showError('Failed to update task');
        });
    }

    // ===== Helper Functions =====
    function showError(message) {
        // Show notification instead of adding to chat
        const notification = document.createElement('div');
        notification.className = 'notification error-notification';
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${message}</span>
            </div>
        `;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 500);
        }, 5000);
    }

    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type === 'success' ? 'success-notification' : ''}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-info-circle'}"></i>
                <span>${message}</span>
            </div>
        `;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 500);
        }, 5000);
    }

    function initCitationGenerator() {
        const sourceTypeSelect = document.getElementById('source-type');
        const generateBtn = document.getElementById('generate-citation-btn');
        const copyBtn = document.getElementById('copy-citation');
        const clearBtn = document.getElementById('clear-citation');

        if (sourceTypeSelect) {
            sourceTypeSelect.addEventListener('change', () => {
                toggleCitationFields();
            });
            toggleCitationFields();
        }

        if (generateBtn) {
            generateBtn.addEventListener('click', () => {
                generateCitation();
            });
        }

        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                copyCitation();
            });
        }

        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                clearCitationForm();
            });
        }

        function toggleCitationFields() {
            const sourceType = sourceTypeSelect.value;
            const allFields = document.querySelectorAll('.citation-field');
            
            allFields.forEach(field => {
                field.style.display = 'none';
            });
            
            const requiredFields = document.querySelectorAll(`.citation-field.${sourceType}`);
            requiredFields.forEach(field => {
                field.style.display = 'block';
            });
        }

        function generateCitation() {
            const sourceType = sourceTypeSelect.value;
            const formData = {};
            
            document.querySelectorAll(`.citation-field.${sourceType} input`).forEach(input => {
                formData[input.name] = input.value;
            });
            
            fetch('/generate_citation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sourceType, ...formData })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                } else {
                    document.getElementById('citation-result').value = data.citation;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showError('Failed to generate citation');
            });
        }

        function copyCitation() {
            const citation = document.getElementById('citation-result').value;
            if (!citation) return;
            
            navigator.clipboard.writeText(citation)
                .then(() => {
                    const originalText = copyBtn.innerHTML;
                    copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                    setTimeout(() => { 
                        copyBtn.innerHTML = originalText; 
                    }, 2000);
                })
                .catch(error => {
                    console.error('Failed to copy citation:', error);
                });
        }

        function clearCitationForm() {
            document.querySelectorAll('.citation-field input').forEach(input => {
                input.value = '';
            });
            document.getElementById('citation-result').value = '';
        }
    }
});