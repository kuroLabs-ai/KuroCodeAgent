# External Integrations Architecture & Guide

> **Namespace:** `src/kurocode/integrations/`  
> **Manager:** `kurocode.core.integration_manager.integration_manager`

---

## 1. Overview & Action Risk Classification

All external services integrate via `BaseIntegration` (`src/kurocode/integrations/base.py`). Every action executed against an integration is classified by risk:

| Risk Category | Invariant & Permission Rule | Examples |
| :--- | :--- | :--- |
| **`READ`** | Read-only inspection; auto-allowed if connected | `get_user`, `list_repos`, `list_files`, `get_updates` |
| **`WRITE`** | State modification; governed by Safe Mode | `upload_file`, `update_issue`, `save_draft` |
| **`EXTERNAL_SIDE_EFFECT`** | Outward-facing communication; requires confirmation by default | `send_message`, `create_pr`, `post_comment` |
| **`DESTRUCTIVE`** | Deletion or removal; always prompts for confirmation | `delete_repo`, `delete_file`, `close_pr` |

---

## 2. Supported Integrations

### 📱 Telegram Integration (`telegram_integration.py`)
* **Capabilities**: Bot messaging to users, groups, and channels (`@channel` or numeric ID), photo/document uploads, diagnostics.
* **Connection**:
  ```bash
  /connect telegram <BOT_TOKEN> [CHAT_ID_OR_CHANNEL]
  ```
* **API Methods**: `sendMessage`, `sendPhoto`, `sendDocument`, `getChat`, `getMe`.

### 🎮 Discord Webhook Integration (`discord_integration.py`)
* **Capabilities**: Urgency-colored rich embed cards, host telemetry footer, custom avatars.
* **Connection**:
  ```bash
  /connect discord <WEBHOOK_URL>
  ```

### 🐙 GitHub Integration (`github_integration.py`)
* **Capabilities**: Repository search, issue tracking, commit inspection, pull request automation.
* **Connection**:
  ```bash
  /connect github <PERSONAL_ACCESS_TOKEN>
  ```

### 📁 Google Drive Integration (`google_drive_integration.py`)
* **Capabilities**: File search, metadata retrieval, document upload.
* **Connection**:
  ```bash
  /connect drive <API_TOKEN>
  ```

### 🦊 GitLab Integration (`gitlab_integration.py`)
* **Capabilities**: Repository queries, merge requests, pipeline status.
* **Connection**:
  ```bash
  /connect gitlab <PRIVATE_TOKEN>
  ```

---

## 3. Credential Storage
All integration tokens and URLs are automatically encrypted via Windows DPAPI and stored in `vault.enc` (`kurocode.core.vault`).
