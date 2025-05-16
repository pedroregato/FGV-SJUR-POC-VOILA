# Homologation Instructions for SJUR Email Processing Pipeline

This document describes how to run and validate the SJUR pipeline responsible for ingesting legal publication emails from Outlook, extracting relevant citation data, and storing them into a structured SQLite database.

## 🔧 Requirements

Ensure the following are configured in your environment:

- Windows with Outlook installed and configured
- Python 3.10+ virtual environment with dependencies installed
- SQLite database already initialized (`sjur.db`)
- The Outlook account folder name is correctly set (default: `SJUR Coleta Serdon`)
- The following Python modules should be correctly implemented and accessible:
  - `app.agents.sjur_agent`
  - `app.modules.serdon_processor.outlook_ingestor`
  - `app.database.db_operations`

## 📂 Folder Structure

```
sjur-poc-voila/
├── app/
│   ├── agents/
│   │   └── sjur_agent.py
│   ├── modules/
│   │   ├── serdon_processor/
│   │   │   └── outlook_ingestor.py
│   └── database/
│       ├── db_connection.py
│       ├── db_operations.py
│       └── db_schema.py
├── tests/
├── .venv/
└── main.py
```

## 🚀 Running the Homologation Script

Run the following command to process emails:

```bash
python -m app.modules.serdon_processor.outlook_ingestor
```

By default, the script will process **all emails** found in the configured Outlook folder.

### 🔢 Limiting the Number of Emails

To process only the first `N` emails for testing:

```python
processar_emails_outlook(quantidade_maxima=5)
```

This should be invoked within `main.py` or another test harness.

## 🧪 Expected Outcomes

1. ✅ HTML and JSON files for each email will be saved in the `emails_html/` and `emails_json/` directories.
2. ✅ The SQLite database (`sjur.db`) will be updated:
   - Table `emails_processados` should contain the processed `message_id`s.
   - Tables `citacoes`, `citacoes_partes`, and `citacoes_metadados` (if implemented) will contain extracted publication data.
3. ✅ Logs will be printed to the console indicating processing status.

## 🧼 Notes

- Re-running the script will **skip already processed emails** using the `message_id` from the `emails_processados` table.
- The JSON file structure will reflect the normalized format with publication fields and process IDs.

## 📞 Troubleshooting

- If you encounter `ModuleNotFoundError`, ensure your working directory is at the project root.
- If Outlook throws access errors, confirm that Outlook is open and that security permissions are granted.
- Clear `.pytest_cache` and rebuild virtual environment if issues persist.

---

For any issues, contact the project maintainer.
