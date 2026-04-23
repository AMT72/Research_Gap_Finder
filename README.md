# 🔍 Research Gap Finder

An AI-powered system that automatically discovers research gaps from scientific papers.

---

## 🗂️ Project Structure

```
research_gap_finder/
├── app.py              ← Main Streamlit interface
├── pdf_reader.py       ← PDF parsing and cleaning
├── analyzer.py         ← Summarization and gap detection (Claude API)
├── report.py           ← PDF report generation
├── requirements.txt    ← Required libraries
├── .env.example        ← API Key configuration template
└── README.md
```

---

## ⚙️ Step-by-Step Installation

### 1. Install Python
Ensure you have Python 3.10 or newer:

```bash
python --version
```

### 2.2. Create a Virtual Environment (Recommended)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup API Key
Copy the `.env.example` file and rename it to `.env`:
```bash
cp .env.example .env
```
Open the file and add your key:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxx
```

Get your key for free at: https://console.anthropic.com

### 5. Run the Application
```bash
streamlit run app.py
```

The browser will automatically open at: http://localhost:8501

---

## 🚀 How to Use

1. Open the app in your browser.
2. Enter your API key in the sidebar
3. Upload 2-10 PDF files (research papers).
4. Click Start Analysis.
5. Wait for approximately 2 minutes.
6. View the results and download the PDF report.
   
---

## 📊 Features & Output

| Feature | Description |
| :--- | :--- |
| Paper Summary | Methodology, Data, Results, and Limitations. |
| Comparison Matrix | A comparative table across all uploaded papers. |
| Research Gaps | Identified gaps with a "Novelty Score" out of 10. |
| Idea Generator | Suggested research ideas with feasibility assessment. |
| Citation Graph | Visualizing relationships between papers. |
| PDF Report | Downloadable professional report. |

---

## 🔑 Obtaining an API Key

1. Go to [https://console.anthropic.com](https://console.anthropic.com).
2. Create a free account.
3. Navigate to **API Keys**.
4. Create a new key.
5. The free tier is sufficient for testing the project.

---

## ❓ Troubleshooting

**Issue: `ModuleNotFoundError`**
```bash
pip install -r requirements.txt
```
**Issue: `AuthenticationError`**
- Verify the validity of your API Key.
- Ensure you have entered it correctly in the sidebar.

**Issue: Paper is "too short"**
- The file might be protected or a scanned document (images only).
- Try uploading a different research paper.

**Issue: `streamlit: command not found`**
Run the application using:
```bash
python -m streamlit run app.py
```
---

## 🛠️ Future Roadmap

- [ ] Support automatic paper retrieval from ArXiv.
- [ ] Full Arabic language interface support.
- [ ] In-depth citation and reference analysis.
- [ ] Microsoft Word (.docx) file support.
