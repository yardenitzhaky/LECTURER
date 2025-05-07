# 📘 NoteLecture.AI

**NoteLecture.AI** is a smart web app that transforms lecture recordings and presentation files into an interactive, searchable experience. It automatically transcribes spoken content, syncs it with slides, and offers AI-powered slide summaries.

---

## 📷 Screenshots

<details>
<summary>Click to expand</summary>

* **Homepage:** ![](screenshots/Screenshot%202025-04-06%20at%2012.16.49.png)
* **Upload Interface:** ![](screenshots/Screenshot%202025-04-06%20at%2012.17.19.png)
* **Processing State:** ![](screenshots/Screenshot%202025-04-09%20at%2017.01.11.png)
* **Lecture View:** ![](screenshots/Screenshot%202025-04-09%20at%2017.01.53.png)

</details>

---

## 🧰 Tech Stack

### Backend

* FastAPI (Python), Uvicorn
* MySQL, asyncio, httpx
* PyMuPDF, moviepy, OpenCV
* IVRIT.AI, OpenAI

### Frontend

* React.js, TypeScript, Vite
* Tailwind CSS, Axios, Lucide

---

## 🖥 Local Setup

### Requirements

* Python 3.11
* npm
* MySQL
* FFmpeg
* API keys: [IVRIT.AI](https://hebrew-ai.com/) & [OpenAI](https://openai.com)

### Clone & Install

```bash
git clone https://github.com/yardenitzhaky/LECTURER.git
cd LECTURER
```

### Backend Setup

```bash
cd notelecture-backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```env
DATABASE_URL="mysql+pymysql://user:pass@host/db"
IVRIT_AI_API_KEY="..."
OPENAI_API_KEY="..."
UPLOADS_DIR=uploads
SECRET_KEY=... (generate one)
```
Then:

```bash
python create_db.py
```

### Frontend Setup

```bash
cd ../notelecture-frontend
npm install
```

Create `.env`:

```env
VITE_API_URL=http://localhost:8000/api
```
---

## ▶️ Run Locally

### Backend

```bash
cd notelecture-backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Frontend (In a new terminal)

```bash
cd notelecture-frontend
npm run dev
```
---

## 🙌 Credits

Created by **Yarden Itzhaky**

Supervised by **Prof. Roei Porat**

Developed as part of a Computer Science project at **University of Haifa**

[Portfolio](https://yardenitzhaky.github.io/Portfolio/) · [LinkedIn](https://linkedin.com/in/yardenitzhaky) · [GitHub](https://github.com/yardenitzhaky)
