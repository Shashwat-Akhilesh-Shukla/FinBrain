### **FinBrain** - AI-Driven Financial Report Analysis 📊  

**FinBrain** is an **AI-powered financial document analysis tool** that extracts key insights from company reports, and earnings transcripts. It combines **Retrieval-Augmented Generation (RAG)** with **Qdrant** for vector search and **Krutrim DeepSeek** for AI-driven responses, all wrapped in a sleek **Streamlit interface** and containerized using **Docker**.

## 🚀 **Features**  
✅ **Upload & Process PDFs** – Extracts structured data from financial documents.  
✅ **AI-Powered Querying** – Uses **vector search + DeepSeek LLM** to provide precise insights.  
✅ **Interactive Streamlit UI** – Seamlessly search and analyze financial reports.  
✅ **Dockerized for Deployment** – Run it anywhere with **one command**.  

---

## 🛠 **Tech Stack**  
🔹 **Python** (FastAPI, Streamlit)  
🔹 **Qdrant** (Vector Database)  
🔹 **Krutrim DeepSeek API** (LLM)  
🔹 **PyMuPDF** (PDF Parsing)  
🔹 **Docker** (Containerization)  

---

## 🏗 **Installation & Setup**  

### **1️⃣ Clone the Repository**  
```bash
git clone https://github.com/Shashwat-Akhilesh-Shukla/FinBrain.git
cd FinBrain
```

### **2️⃣ Install Dependencies**  
```bash
pip install -r requirements.txt
```

### **3️⃣ Set Up Environment Variables**  
Create a `.env` file in the root directory and add:  
```
API_KEY=your_krutrim_api_key
```

### **4️⃣ Run Locally**  
```bash
streamlit run app.py
```

---

## 🐳 **Run with Docker**  
To containerize the app and run it in a **Dockerized environment**, use:  
```bash
docker build -t finbrain .
docker run -p 8501:8501 finbrain
```

---

## 🤝 **Contributing**  
Want to improve **FinInsight**? Feel free to:  
- **Fork** the repository  
- **Submit** a pull request  
- **Report issues**  

---

## 📜 **License**  
This project is licensed under the **MIT License**.  
