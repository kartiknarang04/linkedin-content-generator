# 🚀 LinkedIn Content Generator

This is an automated LinkedIn content generator app that scrapes your profile, generates personalized posts using AI, and stores the results in MongoDB. It leverages OpenAI/Groq for content creation and Selenium for scraping.

---

## 📦 Features

- 🔍 Scrapes LinkedIn profiles
- 🧠 Generates LinkedIn content using AI (Groq/OpenAI)
- 🗓️ Content calendar generation (weekly/monthly)
- 🗃️ Stores content in MongoDB
- 🖥️ Built with Python and Streamlit

---

## 📁 Project Structure

complete-app/
├── app2.py # Main Streamlit app
├── linkedin_scraper.py # Profile scraping logic using Selenium
├── persona.py # Handles persona/context setup
├── .env # Contains sensitive environment variables (not tracked)
├── .gitignore # Ensures .env and other temp files are excluded


## 🔧 Setup Instructions

### 1. Clone the repo

```bash
git clone https://github.com/kartiknarang04/linkedin-content-generator.git
cd linkedin-content-generator
```
### 2.Set up virtual environment
```bash
python -m venv venv
venv\Scripts\activate   # On Windows
# source venv/bin/activate   # On macOS/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your environment variables

Create a .env file in the root directory:
```bash
LINKEDIN_EMAIL=your_email_here
LINKEDIN_PASSWORD=your_password_here
GROQ_API_KEY=your_groq_api_key_here
MONGO_URI=mongodb://localhost:27017/
```

### 5. Run app
```bash
streamlit run app2.py
```

