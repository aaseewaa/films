
```bash
cd backend

# 1) Виртуальное окружение
python3 -m venv venv
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# из папки backend, с активным venv
uvicorn app.main:app --reload
