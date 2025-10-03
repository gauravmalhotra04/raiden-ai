# Raiden AI - Deployment Guide

## 🚀 Quick Deployment Options

### Option 1: Local Development (Recommended for Testing)

1. **Clone the Repository**
   ```bash
   git clone https://github.com/gauravmalhotra04/raiden-ai.git
   cd raiden-ai
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**
   ```bash
   # Windows
   set GROQ_API_KEY=your_groq_api_key_here
   set GNEWS_API_KEY=your_gnews_api_key_here
   set OPENWEATHER_API_KEY=your_openweather_api_key_here
   
   # Linux/Mac
   export GROQ_API_KEY=your_groq_api_key_here
   export GNEWS_API_KEY=your_gnews_api_key_here
   export OPENWEATHER_API_KEY=your_openweather_api_key_here
   ```

4. **Run the Server**
   ```bash
   python server.py
   ```

5. **Access the Application**
   - Open your browser and go to: http://localhost:5000

### Option 2: Using Setup Script

```bash
python setup.py
```
This will guide you through the entire setup process.

### Option 3: Windows Batch File

Double-click `run_server.bat` to start the server.

## 🌐 Cloud Deployment Options

### Option 1: Render (Recommended for Free Hosting)

1. **Connect to GitHub**
   - Go to [Render.com](https://render.com)
   - Sign up and connect your GitHub account
   - Select your `raiden-ai` repository

2. **Create a Web Service**
   - Choose "Web Service"
   - Use these settings:
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python server.py`
     - **Environment**: Python 3

3. **Set Environment Variables**
   - In Render dashboard, go to Environment
   - Add these variables:
     ```
     GROQ_API_KEY=your_groq_api_key_here
     GNEWS_API_KEY=your_gnews_api_key_here
     OPENWEATHER_API_KEY=your_openweather_api_key_here
     ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment to complete
   - Your app will be available at the provided URL

### Option 2: Heroku

1. **Install Heroku CLI**
   ```bash
   # Download from https://devcenter.heroku.com/articles/heroku-cli
   ```

2. **Login and Create App**
   ```bash
   heroku login
   heroku create your-app-name
   ```

3. **Set Environment Variables**
   ```bash
   heroku config:set GROQ_API_KEY=your_groq_api_key_here
   heroku config:set GNEWS_API_KEY=your_gnews_api_key_here
   heroku config:set OPENWEATHER_API_KEY=your_openweather_api_key_here
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

### Option 3: Railway

1. **Connect to GitHub**
   - Go to [Railway.app](https://railway.app)
   - Sign up and connect your GitHub account

2. **Deploy from GitHub**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `raiden-ai` repository

3. **Set Environment Variables**
   - Go to Variables tab
   - Add your API keys

4. **Deploy**
   - Railway will automatically deploy your app

## 🔑 Getting API Keys

### Groq API Key (Required for AI Features)
1. Go to [https://console.groq.com/](https://console.groq.com/)
2. Sign up or log in
3. Create a new API key
4. Copy the key (starts with `gsk_`)

### GNews API Key (Optional - for News)
1. Go to [https://gnews.io/](https://gnews.io/)
2. Sign up for a free account
3. Get your API key from the dashboard

### OpenWeather API Key (Optional - for Weather)
1. Go to [https://openweathermap.org/api](https://openweathermap.org/api)
2. Sign up for a free account
3. Get your API key from the dashboard

## 📊 Features Available

- ✅ **AI Chat** - Powered by Groq's LLM models
- ✅ **Math Solver** - Advanced mathematical problem solving
- ✅ **PDF Summarization** - Extract and summarize PDF content
- ✅ **Flashcards** - Create and manage study flashcards
- ✅ **Task Management** - Study planner with reminders
- ✅ **News API** - Get latest news and headlines
- ✅ **Weather API** - Current weather and forecasts
- ✅ **Web Search** - Search the web for information
- ✅ **Citation Generator** - Generate academic citations
- ✅ **Attendance Tracker** - Track attendance records
- ✅ **Code Playground** - Run Python code safely

## 🛠️ Troubleshooting

### Common Issues

1. **"No supported models available"**
   - Check your Groq API key is valid
   - Ensure you have sufficient credits in your Groq account

2. **Port 5000 already in use**
   - Change the port in `server.py` line 542
   - Or kill the process using port 5000

3. **Import errors**
   - Run `pip install -r requirements.txt` again
   - Check Python version compatibility (Python 3.8+)

4. **Database errors**
   - The SQLite database (`raiden.db`) is created automatically
   - If issues persist, delete the database file and restart

### Getting Help

- Check the console output for error messages
- Ensure all dependencies are installed
- Verify your API keys are correct
- Check the [GitHub Issues](https://github.com/gauravmalhotra04/raiden-ai/issues) for common problems

## 🔒 Security Notes

- Never commit API keys to your repository
- Use environment variables for all sensitive data
- The application uses secure practices for API key handling
- All user data is stored locally in SQLite database

## 📈 Performance Tips

- For production deployment, consider using a proper WSGI server like Gunicorn
- Set up proper logging and monitoring
- Use a reverse proxy like Nginx for better performance
- Consider using a proper database like PostgreSQL for production

## 🎯 Next Steps

1. Set up your API keys
2. Deploy to your preferred platform
3. Customize the application for your needs
4. Add additional features as required

---

**Happy Coding! 🚀**
