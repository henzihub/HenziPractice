# HenziPractice

## Azure Bot Framework Resources

This repository now includes a comprehensive guide for building chatbots with Azure Bot Framework and integrating Azure OpenAI for generative responses. Start with the documentation below:

- [Building a Generative Chatbot with Azure Bot Framework](docs/azure-bot-framework-chatbot.md)

## Python sample bot

The `bot/` directory contains a runnable Python bot that uses the Bot Framework SDK and optionally calls Azure OpenAI for generative replies. Use it as a starting point for your own assistants or as a reference implementation when following the guide above.

### Quick start

1. Create and activate a Python 3.10+ virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Export Azure credentials for the Bot Framework adapter and Azure OpenAI:
   ```bash
   export MICROSOFT_APP_ID="<bot-app-id>"
   export MICROSOFT_APP_PASSWORD="<bot-app-password>"
   export AZURE_OPENAI_ENDPOINT="https://<resource-name>.openai.azure.com"
   export AZURE_OPENAI_DEPLOYMENT="<deployment-name>"
   export AZURE_OPENAI_API_KEY="<api-key>"
   ```
4. Start the bot locally:
   ```bash
   python -m bot
   ```
5. Connect using the Bot Framework Emulator at `http://localhost:3978/api/messages`.

Run `pytest` to execute the unit tests for the bot logic.
