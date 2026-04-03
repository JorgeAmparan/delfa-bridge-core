# Delfa Bridge — Quickstart Guide
> Powered by Panohayan™ Architecture

Get started with Delfa Bridge in under 5 minutes.

---

## 1. Authentication

All requests require an API Key in the header:
```http
X-API-Key: your_api_key_here
```

Get your API Key after subscribing at [delfa.bridge](https://delfa.bridge).

---

## 2. Base URL
```
https://delfa-api-production.up.railway.app
```

---

## 3. Process your first document

Upload a PDF, DOCX, or XLSX and Panohayan™ will extract all entities automatically.
```bash
curl -X POST https://delfa-api-production.up.railway.app/documents/process \
  -H "X-API-Key: your_api_key" \
  -F "file=@your_document.pdf"
```

**Response:**
```json
{
  "status": "success",
  "archivo": "your_document.pdf",
  "entidades_extraidas": 41,
  "gobernanza": {
    "total": 41,
    "aprobadas": 35,
    "cuarentena": 4,
    "marcadas": 2
  }
}
```

---

## 4. Search your knowledge base

Ask anything in natural language:
```bash
curl -X POST https://delfa-api-production.up.railway.app/search/ \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"query": "who signed the contract?", "limit": 5}'
```

**Response:**
```json
{
  "query": "who signed the contract?",
  "resultados": [
    {
      "entity_class": "entidad_nombre",
      "entity_value": "JORGE LUIS AMPARÁN HERNÁNDEZ",
      "similarity": 0.72
    }
  ],
  "total": 1
}
```

---

## 5. List processed documents
```bash
curl https://delfa-api-production.up.railway.app/documents/ \
  -H "X-API-Key: your_api_key"
```

---

## 6. Get full audit trail
```bash
curl https://delfa-api-production.up.railway.app/trail/document/{document_id} \
  -H "X-API-Key: your_api_key"
```

---

## 7. Connect Google Drive

Process an entire Drive folder automatically:
```bash
curl -X POST https://delfa-api-production.up.railway.app/connectors/drive/process \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"folder_id": "your_google_drive_folder_id"}'
```

---

## 8. Connect MicroSip ERP
```bash
curl -X POST https://delfa-api-production.up.railway.app/connectors/microsip/login \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://your_microsip_server:5000",
    "username": "your_user",
    "password": "your_password",
    "selected_db": "your_ip:/microsip"
  }'
```

---

## 9. Configure Governance Rules

Set rules for your organization — no code required:
```bash
curl -X POST https://delfa-api-production.up.railway.app/governance/rules \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_class": "monto_total",
    "rule_type": "high_amount",
    "action": "require_approval",
    "condition": {"min_value": 50000}
  }'
```

**Actions available:**
- `require_approval` — sends to quarantine until human approval
- `flag` — marks for review but keeps active
- `block` — rejects the entity completely
- `redact` — stores but hides the value

---

## 10. Connect SQL Database
```bash
curl -X POST https://delfa-api-production.up.railway.app/connectors/sql/connect \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "db_type": "mysql",
    "host": "your_host",
    "port": 3306,
    "database": "your_db",
    "username": "your_user",
    "password": "your_password"
  }'
```

---

## Full API Reference

Interactive docs available at:
```
https://delfa-api-production.up.railway.app/docs
```

---

## SDKs & Integrations

Coming soon:
- Python SDK
- JavaScript/Node SDK
- Bubble.io plugin
- Zapier integration

---

*Delfa Bridge — Intelligent Middleware for Enterprise AI*
*Powered by Panohayan™ | Built in Ciudad Juárez, México 🇲🇽*
