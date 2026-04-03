# Inventario Técnico de Conectores — Delfa Bridge

> Referencia autoritativa para implementación de los 28 conectores pendientes.
> Generado: 2026-04-02 | Arquitectura: Panohayan™

## Patrón arquitectónico

Todos los conectores siguen el mismo flujo establecido por los 3 existentes (Google Drive, MicroSip, SQL):

```
Conector (extrae/recibe datos)
    ↓
DII (Digest Input Intelligence) — extracción de entidades
    ↓
EDB Lite (Supabase) — persistencia con embeddings
    ↓
GRG (Governance Guardrails) — evaluación de reglas
    ↓
TM (Traceability Matrix) — audit trail
```

- Cada conector es una clase en `app/connectors/<nombre>.py`
- Cada conector expone endpoint(s) en `app/api/routers/connectors.py`
- Todos reciben `org_id` como parámetro (multitenancy)
- Los datos se convierten a texto estructurado → archivo temporal → DII pipeline

---

## Conectores existentes (3)

| Conector | Archivo | Endpoints |
|----------|---------|-----------|
| Google Drive | `google_drive.py` | `POST /connectors/drive/process`, `GET /connectors/drive/files` |
| MicroSip | `microsip.py` | `POST /connectors/microsip/process`, `POST /connectors/microsip/login`, `POST /connectors/microsip/db/connect`, `POST /connectors/microsip/db/process`, `POST /connectors/microsip/files/process` |
| SQL genérico | `sql.py` | `POST /connectors/sql/connect`, `POST /connectors/sql/process` |

---

## Conectores pendientes (28)

### Productividad (7)

| # | Conector | Archivo | Método | Endpoints | Auth | Deps pip | Complejidad |
|---|---------|---------|--------|-----------|------|----------|-------------|
| 1 | Notion | `notion.py` | REST API | `POST /connectors/notion/sync` | OAuth2 (integration token) | `requests` | Simple |
| 2 | OneDrive | `onedrive.py` | REST API (MS Graph) | `POST /connectors/onedrive/process`, `GET /connectors/onedrive/files` | OAuth2 (Azure AD) | `msal`, `requests` | Media |
| 3 | SharePoint | `sharepoint.py` | REST API (MS Graph) | `POST /connectors/sharepoint/process`, `GET /connectors/sharepoint/sites` | OAuth2 (Azure AD, app registration) | `msal`, `requests` | Alta |
| 4 | Slack | `slack.py` | REST API + Webhook | `POST /connectors/slack/sync`, `POST /connectors/slack/webhook` | OAuth2 (Bot Token) | `slack-sdk` | Media |
| 5 | Teams | `teams.py` | REST API (MS Graph) | `POST /connectors/teams/sync` | OAuth2 (Azure AD) | `msal`, `requests` | Alta |
| 6 | Zoom | `zoom.py` | REST API | `POST /connectors/zoom/sync` | OAuth2 (Server-to-Server) | `requests` | Media |
| 7 | Meet | `meet.py` | REST API (Google) | `POST /connectors/meet/sync` | OAuth2 (Service Account) | `google-api-python-client`, `google-auth` | Media |

### Comunicación (3)

| # | Conector | Archivo | Método | Endpoints | Auth | Deps pip | Complejidad |
|---|---------|---------|--------|-----------|------|----------|-------------|
| 8 | WhatsApp Business | `whatsapp.py` | REST API (Cloud API) | `POST /connectors/whatsapp/webhook`, `POST /connectors/whatsapp/sync` | API Key (Bearer token) | `requests` | Media |
| 9 | Gmail | `gmail.py` | REST API (Google) | `POST /connectors/gmail/sync` | OAuth2 (Service Account) | `google-api-python-client`, `google-auth` | Media |
| 10 | Outlook | `outlook.py` | REST API (MS Graph) | `POST /connectors/outlook/sync` | OAuth2 (Azure AD) | `msal`, `requests` | Media |

### ERP mexicano (5)

| # | Conector | Archivo | Método | Endpoints | Auth | Deps pip | Complejidad |
|---|---------|---------|--------|-----------|------|----------|-------------|
| 11 | CONTPAQi | `contpaqi.py` | ODBC + File-based (XML CFDI) | `POST /connectors/contpaqi/process`, `POST /connectors/contpaqi/files` | User/Pass (ODBC) | `pyodbc`, `sqlalchemy` | Alta |
| 12 | Aspel | `aspel.py` | ODBC + File-based | `POST /connectors/aspel/process`, `POST /connectors/aspel/files` | User/Pass (ODBC) | `pyodbc`, `sqlalchemy` | Alta |
| 13 | Bind ERP | `binderp.py` | REST API | `POST /connectors/binderp/sync` | API Key | `requests` | Simple |
| 14 | SAP Business One | `sapb1.py` | REST API (Service Layer) | `POST /connectors/sapb1/sync`, `POST /connectors/sapb1/query` | User/Pass (session-based) | `requests` | Alta |
| 15 | Odoo | `odoo.py` | REST API (JSON-RPC) | `POST /connectors/odoo/sync` | User/Pass + DB name | `requests` | Media |

### CRM (4)

| # | Conector | Archivo | Método | Endpoints | Auth | Deps pip | Complejidad |
|---|---------|---------|--------|-----------|------|----------|-------------|
| 16 | HubSpot | `hubspot.py` | REST API | `POST /connectors/hubspot/sync` | OAuth2 o API Key (private app) | `requests` | Simple |
| 17 | Salesforce | `salesforce.py` | REST API (SOQL) | `POST /connectors/salesforce/sync`, `POST /connectors/salesforce/query` | OAuth2 (Connected App) | `simple-salesforce` | Media |
| 18 | Zoho CRM | `zoho.py` | REST API | `POST /connectors/zoho/sync` | OAuth2 (self-client) | `requests` | Media |
| 19 | Pipedrive | `pipedrive.py` | REST API | `POST /connectors/pipedrive/sync` | API Key (token en query param) | `requests` | Simple |

### Legacy (4)

| # | Conector | Archivo | Método | Endpoints | Auth | Deps pip | Complejidad |
|---|---------|---------|--------|-----------|------|----------|-------------|
| 20 | ODBC genérico | `odbc.py` | ODBC | `POST /connectors/odbc/connect`, `POST /connectors/odbc/query`, `POST /connectors/odbc/process` | User/Pass (connection string) | `pyodbc`, `sqlalchemy` | Media |
| 21 | FTP/SFTP | `ftp.py` | File-based (FTP/SFTP) | `POST /connectors/ftp/sync` | User/Pass o SSH Key | `paramiko` | Media |
| 22 | IMAP | `imap.py` | Protocolo IMAP | `POST /connectors/imap/sync` | User/Pass o App Password | stdlib (`imaplib`, `email`) | Media |
| 23 | Agente On-Premise | `onpremise.py` | Webhook (push desde agente) | `POST /connectors/onpremise/receive`, `GET /connectors/onpremise/status` | API Key (shared secret) | `requests` | Alta |

### No-code (3)

| # | Conector | Archivo | Método | Endpoints | Auth | Deps pip | Complejidad |
|---|---------|---------|--------|-----------|------|----------|-------------|
| 24 | Make (Integromat) | `make.py` | Webhook (Delfa recibe) | `POST /connectors/make/webhook` | API Key (header custom) | Ninguna extra | Simple |
| 25 | Zapier | `zapier.py` | Webhook (Delfa recibe) | `POST /connectors/zapier/webhook` | API Key (header custom) | Ninguna extra | Simple |
| 26 | n8n | `n8n.py` | Webhook (Delfa recibe) | `POST /connectors/n8n/webhook` | API Key (header custom) | Ninguna extra | Simple |

### No-devs (4)

| # | Conector | Archivo | Método | Endpoints | Auth | Deps pip | Complejidad |
|---|---------|---------|--------|-----------|------|----------|-------------|
| 27 | Plugin Bubble | `bubble.py` | REST API (Bubble → Delfa) | `POST /connectors/bubble/process` | API Key | Ninguna extra | Simple |
| 28 | Plugin Lovable | `lovable.py` | REST API (Lovable → Delfa) | `POST /connectors/lovable/process` | API Key | Ninguna extra | Simple |
| 29 | Chrome Extension | `chrome_ext.py` | REST API (ext → Delfa) | `POST /connectors/chrome-ext/process` | API Key (usuario autenticado) | Ninguna extra | Simple |
| 30 | Webhook genérico | `webhook.py` | Webhook (cualquier fuente) | `POST /connectors/webhook/receive` | API Key o HMAC signature | Ninguna extra | Simple |

---

## Resumen por complejidad

| Complejidad | Cant. | Conectores |
|-------------|-------|-----------|
| **Simple** | 10 | Notion, Bind ERP, HubSpot, Pipedrive, Make, Zapier, n8n, Bubble, Lovable, Chrome Extension, Webhook genérico |
| **Media** | 12 | OneDrive, Slack, Zoom, Meet, WhatsApp, Gmail, Outlook, Odoo, Salesforce, Zoho, ODBC, FTP/SFTP, IMAP |
| **Alta** | 6 | SharePoint, Teams, CONTPAQi, Aspel, SAP B1, Agente On-Premise |

## Dependencias pip nuevas

| Paquete | Conectores | Notas |
|---------|-----------|-------|
| `msal` | OneDrive, SharePoint, Teams, Outlook | Microsoft Authentication Library — todos los conectores MS Graph |
| `slack-sdk` | Slack | SDK oficial de Slack |
| `google-api-python-client` | Meet, Gmail | Ya existe para Google Drive |
| `google-auth` | Meet, Gmail | Ya existe para Google Drive |
| `simple-salesforce` | Salesforce | Wrapper Python para Salesforce REST API |
| `pyodbc` | CONTPAQi, Aspel, ODBC genérico | Driver ODBC — requiere unixODBC en Docker |
| `paramiko` | FTP/SFTP | SSH/SFTP para Python |

Paquetes ya en el proyecto: `requests`, `sqlalchemy`, `google-auth`, `google-api-python-client`.

## Variables de entorno por conector

| Conector | Variables `.env` |
|----------|-----------------|
| Notion | `NOTION_TOKEN` |
| OneDrive | `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` |
| SharePoint | `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, `SHAREPOINT_SITE_URL` |
| Slack | `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` |
| Teams | `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` |
| Zoom | `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET` |
| Meet | `GOOGLE_SERVICE_ACCOUNT_FILE` (reutiliza Drive) |
| WhatsApp | `WHATSAPP_TOKEN`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_PHONE_ID` |
| Gmail | `GOOGLE_SERVICE_ACCOUNT_FILE` (reutiliza Drive) |
| Outlook | `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` |
| CONTPAQi | `CONTPAQI_ODBC_DSN`, `CONTPAQI_USER`, `CONTPAQI_PASSWORD` |
| Aspel | `ASPEL_ODBC_DSN`, `ASPEL_USER`, `ASPEL_PASSWORD` |
| Bind ERP | `BINDERP_API_KEY`, `BINDERP_URL` |
| SAP B1 | `SAPB1_URL`, `SAPB1_USER`, `SAPB1_PASSWORD`, `SAPB1_COMPANY` |
| Odoo | `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD` |
| HubSpot | `HUBSPOT_API_KEY` |
| Salesforce | `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD`, `SALESFORCE_TOKEN`, `SALESFORCE_DOMAIN` |
| Zoho | `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN` |
| Pipedrive | `PIPEDRIVE_API_TOKEN`, `PIPEDRIVE_DOMAIN` |
| ODBC genérico | `ODBC_CONNECTION_STRING` |
| FTP/SFTP | `FTP_HOST`, `FTP_USER`, `FTP_PASSWORD`, `FTP_PORT`, `FTP_PROTOCOL` |
| IMAP | `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD`, `IMAP_PORT` |
| Agente On-Premise | `ONPREMISE_SHARED_SECRET` |
| Make | `MAKE_WEBHOOK_SECRET` |
| Zapier | `ZAPIER_WEBHOOK_SECRET` |
| n8n | `N8N_WEBHOOK_SECRET` |
| Bubble | (usa auth estándar de Delfa Bridge) |
| Lovable | (usa auth estándar de Delfa Bridge) |
| Chrome Extension | (usa auth estándar de Delfa Bridge) |
| Webhook genérico | `WEBHOOK_HMAC_SECRET` (opcional) |

## Orden de implementación sugerido

### Fase 1 — Quick wins (10 simples)
Make, Zapier, n8n, Webhook genérico, Bubble, Lovable, Chrome Extension, Notion, HubSpot, Pipedrive, Bind ERP

### Fase 2 — Media complejidad (12)
Gmail, Outlook, OneDrive, Slack, WhatsApp, Zoom, Meet, Salesforce, Zoho, Odoo, ODBC, FTP/SFTP, IMAP

### Fase 3 — Alta complejidad (6)
SharePoint, Teams, CONTPAQi, Aspel, SAP B1, Agente On-Premise
