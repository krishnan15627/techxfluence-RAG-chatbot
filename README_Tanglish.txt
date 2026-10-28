==============================================================
  TECHXFLUENCE AI - RAG CHATBOT  (Streamlit + Ollama + Llama 3.2)
  Windows + VS Code setup guide (Tanglish)
==============================================================

IDHU ENNA?
----------
TechXfluence AI oru local chatbot. Neenga kelvi kettaa:
  1. App, data/ folder-la irukkura TechXfluence website content-ah search pannum (Retrieval).
  2. Best matching sections-ah eduthu, local Llama 3.2 model-ku anuppum (Augmented).
  3. Llama 3.2 andha content-ah mattum vechu answer ezhudhum (Generation).
  4. Answer-oda sethu "Sources" (website link / file name) kaattum.

Gemini / OpenAI maari API key VENDAM. Paid service VENDAM. Ellame ungal computer-la run aagum.
Answer knowledge base-la illana, bot ippadi solum:
  "I couldn't find that information in the available TechXfluence resources.
   Please contact the official team."


PROJECT FILES
-------------
app.py                    -> Streamlit UI (chat screen, sidebar, CSS)
rag_engine.py             -> Knowledge load + search (BM25) + prompt build
ollama_llm.py             -> Local Ollama / Llama 3.2 oda pesura code
ingest_website.py         -> Website-la irundhu content download panna
data/company_knowledge.txt-> Main knowledge file (hand-checked website info)
requirements.txt          -> Python packages list
run_windows.bat           -> Double-click panni start panna (optional)


==============================================================
STEP-BY-STEP SETUP (WINDOWS + VS CODE)
==============================================================

STEP 0: ZIP EXTRACT PANNU
  - ZIP-ah right-click -> "Extract All..." -> TechXfluence_AI folder varum.
  - VS Code open pannu -> File -> Open Folder -> TechXfluence_AI select pannu.

STEP 1: PYTHON INSTALL PANNU (already irundha skip pannu)
  - https://www.python.org/downloads/ -> Python 3.10 or 3.11 or 3.12 download pannu.
  - Installer first screen-la "Add python.exe to PATH" CHECKBOX tick pannu. (Romba mukkiyam!)
  - Check: VS Code-la  Terminal -> New Terminal  open pannu, ezhudhu:
        python --version
    Version kaatina OK.

STEP 2: VIRTUAL ENVIRONMENT + PACKAGES INSTALL
  VS Code terminal-la (PowerShell) ivaiya order-la run pannu:

        python -m venv .venv
        .venv\Scripts\activate
        pip install -r requirements.txt

  PowerShell "running scripts is disabled" error kaatina, idhu run pannu, apram activate pannu:
        Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  (Illana Command Prompt (cmd) terminal use pannu.)

  Terminal-la (.venv) nu prompt munnadi therinjaa activate aaiduchu.

STEP 3: OLLAMA INSTALL PANNU
  - https://ollama.com/download -> "Download for Windows" -> OllamaSetup.exe run pannu.
  - Install aana apram Ollama background-la run aagum (system tray-la llama icon).
  - Check: new terminal-la
        ollama --version

STEP 4: LLAMA 3.2 MODEL DOWNLOAD PANNU
  Terminal-la:
        ollama pull llama3.2
  - Around 2 GB download. Internet speed-ah poruthu konjam neram aagum. Oru dhadavai mattum.
  - Test pannanum na:
        ollama run llama3.2
    "hello" nu type pannu. Reply vandha OK. Exit panna  /bye  type pannu.

  (Computer slow-a irundha / RAM kammi (8 GB-ku keela) na, chinna model use pannalam:
        ollama pull llama3.2:1b
        set OLLAMA_MODEL=llama3.2:1b
   Apram step 6-la start pannu.)

STEP 5: WEBSITE CONTENT KNOWLEDGE BASE-LA SERKA
  Option A - Already ready:
     data/company_knowledge.txt-la TechXfluence website (27 Oct 2026) content already irukku.
     Adhu verify panna content. Neenga adhai appadiye use pannalam.

  Option B - Website-la irundhu fresh-a download panna:
        python ingest_website.py
     Idhu data/website_content.txt file create pannum. (company_knowledge.txt overwrite aagaadhu.)
     Oru page mattum venum na:
        python ingest_website.py --url https://www.techxfluence.com/membership

  Option C - Kai-la copy panni add panna (website text extract aagala na):
     1) Website page-la text-ah copy pannu.
     2) data/company_knowledge.txt open pannu, kadaisila ippadi ezhudhu:

          === SECTION: Partners ===
          SOURCE: https://www.techxfluence.com/partners
          (inga copy panna text paste pannu)

     Illana command-la:
          python ingest_website.py --add "Partners" "copied text here" --source https://www.techxfluence.com/partners

  Mukkiyam: Unmaiyana website information mattum add pannu. Price, date, phone number
  ellam invent pannadha. Add panna apram app-la sidebar-la "Reload knowledge" click pannu
  (illana app-ah restart pannu).

STEP 6: CHATBOT START PANNU
  Ollama run aagikittu irukkanum. Apram terminal-la (venv active):
        streamlit run app.py
  Browser auto-a open aagum: http://localhost:8501
  Open aagala na andha URL-ah browser-la type pannu.

  Illana simple-a  run_windows.bat  file-ah double-click pannu
  (venv create panni, packages install panni, app start pannum).

  Stop panna: terminal-la Ctrl + C.

STEP 7: TRY PANNU - SAMPLE QUESTIONS
  - What services does TechXfluence offer?
  - What are the membership plans and prices?
  - How can I host an event?
  - What job roles are open?
  - How can I contact TechXfluence?
  - Who is the president of USA?        (Idhu knowledge-la illa -> "couldn't find" nu solla vendum)


SIDEBAR-LA ENNA IRUKKU
----------------------
  - Local AI model status: Ollama run aaguthaa, Llama 3.2 download aachaa nu kaattum.
  - Knowledge base: ethana chunks, entha files load aachu.
  - RAG pipeline steps.
  - Clear chat, Reload knowledge buttons.


COMMON ERRORS + FIX
-------------------
1) 'python' is not recognized...
   -> Python install pannumbodhu "Add to PATH" tick pannala. Python-ah uninstall/repair panni
      marubadi install pannu, PATH checkbox tick pannu. Apram VS Code-ah close panni thirumba open pannu.

2) 'streamlit' is not recognized
   -> Venv activate aagala. Run:  .venv\Scripts\activate   apram  pip install -r requirements.txt
      Illana:  python -m streamlit run app.py

3) Sidebar-la "Ollama not running"  /  "Cannot reach Ollama"
   -> Start menu-la "Ollama" app open pannu. Illana terminal-la:  ollama serve
      Apram browser-la page refresh pannu.
      "bind: Only one usage of each socket address" nu vandha, Ollama already run aaguthu - OK.

4) Sidebar-la "Model not downloaded"  /  error 404
   -> Run:  ollama pull llama3.2   (Check:  ollama list)

5) First answer romba slow
   -> Model first time memory-la load aagum. Konjam wait pannu. Aduthu answers fast-a irukkum.
      Romba slow na  llama3.2:1b  use pannu (Step 4 paar).

6) Always "I couldn't find that information..." nu varudhu
   -> Kelvi-la irukkura words knowledge file-la illa. Kelvi-ah vera maari kelu, illana
      data/company_knowledge.txt-la andha information add pannu. File format
      (=== SECTION: ... === line) correct-a irukka check pannu.

7) ingest_website.py  [fail] / "very little text found"
   -> Internet check pannu. Website JavaScript-la load aana text kidaikkaadhu. Option C
      (kai-la copy-paste) use pannu.

8) ModuleNotFoundError: No module named 'requests' (or bs4 / streamlit)
   -> Venv active-a irukka check pannu, apram:  pip install -r requirements.txt

9) Port 8501 already in use
   -> Vera port-la run pannu:  streamlit run app.py --server.port 8502

10) Answer-la thappa irukku nu thonuchu
   -> Sources-la kaattura link-ah open panni official website-la verify pannu. Prices, dates,
      job openings maarum. Knowledge file-ah update pannu.


TIPS
----
  - Model maatha:  set OLLAMA_MODEL=llama3.2:1b   (PowerShell-la:  $env:OLLAMA_MODEL="llama3.2:1b")
  - Search strict / loose maatha: rag_engine.py top-la MIN_COVERAGE, TOP_K, MIN_SCORE maathu.
  - Synonyms add panna: rag_engine.py-la SYNONYMS dictionary-la words serkkalaam.
  - UI colours maatha: app.py-la CSS block-la --cyan, --purple, --navy maathu.
  - Private / confidential documents data/ folder-la podaadha (permission illama).
  - API key edhuvum code-la hardcode pannala; need-um illa.

All the best! 🚀
