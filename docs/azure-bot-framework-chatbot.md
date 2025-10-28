# Building a Generative Chatbot with Azure Bot Framework

This guide walks through building, integrating, and deploying an Azure Bot Framework solution that uses Azure OpenAI to add generative AI capabilities. It assumes you want to develop locally, connect to Azure resources, and ship to production using recommended enterprise practices.

## 1. Architecture Overview

```
User → Channel (Teams/Web Chat/Direct Line) → Bot Adapter → Middleware → Dialog/Orchestration Layer →
  ├─ Deterministic Services (REST APIs, databases)
  ├─ Azure Cognitive Search (RAG enrichment)
  └─ Azure OpenAI (LLM inference)
```

Key components:

| Component | Purpose |
| --- | --- |
| **Azure Bot Service (Channels Registration)** | Central hub for channel connections and authentication. |
| **Bot Framework SDK v4** | Provides adapters, middleware pipeline, dialog system, and state management. |
| **Azure OpenAI Service** | Hosts GPT-family models for natural language generation. |
| **Azure Cognitive Search (optional)** | Supplies retrieval-augmented generation (RAG) content. |
| **Application Insights** | Observability, telemetry, and monitoring. |

## 2. Prerequisites

1. **Azure Subscription** with access to Azure OpenAI.
2. **Local tooling**:
   * Node.js 18+ (JavaScript/TypeScript) or .NET 6+ (C#) SDK.
   * Bot Framework CLI (`npm install -g @microsoft/botframework-cli`).
   * Bot Framework Emulator for local conversation testing.
3. **Development environment**:
   * VS Code with Bot Framework/ Azure extensions recommended.
   * Azure CLI (`az`) for resource provisioning.

## 3. Provision Azure Resources

```bash
# Log in
az login

# Create resource group
az group create \
  --name rg-bot-genai \
  --location eastus

# Provision Channels Registration (bot service)
az bot create \
  --resource-group rg-bot-genai \
  --name genai-chatbot \
  --kind registration \
  --sku S1 \
  --endpoint https://<placeholder-host>/api/messages \
  --display-name "GenAI Chatbot"

# Provision Azure OpenAI (only available in supported regions)
az cognitiveservices account create \
  --name aoai-genai \
  --resource-group rg-bot-genai \
  --kind OpenAI \
  --sku S0 \
  --location eastus

# Deploy a GPT model
az cognitiveservices account deployment create \
  --name aoai-genai \
  --resource-group rg-bot-genai \
  --deployment-name gpt-4o-mini \
  --model-name gpt-4o-mini \
  --model-format OpenAI \
  --scale-type Standard
```

Store the **Azure OpenAI endpoint** and **API key** (or configure Azure AD + Managed Identity for secure access).

## 4. Scaffold a Bot Framework Project

Use Yeoman or Composer. The following example uses Yeoman for a TypeScript bot with dialog support:

```bash
npm install -g yo generator-botbuilder
mkdir genai-bot && cd genai-bot
yo botbuilder
# Choose "Echo Bot (TypeScript)" or "Core Bot (TypeScript)" for dialog scaffolding.
```

Project structure highlights:

```
src/
  index.ts           # Entry point that wires up the adapter and bot
  bot.ts             # Bot class with onMessage, onMembersAdded handlers
  dialogs/           # Waterfall/Adaptive dialog definitions
  services/          # Custom services (add generative AI integration here)
.botconfig / appsettings.json # Configuration
```

## 5. Wire Up Azure OpenAI

1. Add configuration entries to `config/default.json` or `.env`:

```json
{
  "azureOpenAI": {
    "endpoint": "https://aoai-genai.openai.azure.com/",
    "deployment": "gpt-4o-mini",
    "apiKey": "${AZURE_OPENAI_KEY}"
  }
}
```

2. Install dependencies:

```bash
npm install openai node-fetch
```

3. Create a reusable service (TypeScript example) at `src/services/azureOpenAiService.ts`:

```ts
import OpenAI from "openai";

export interface GenerativeRequest {
  systemPrompt: string;
  history: { role: "system" | "user" | "assistant"; content: string }[];
  maxTokens?: number;
  temperature?: number;
}

export class AzureOpenAiService {
  private client: OpenAI;
  private deployment: string;

  constructor(endpoint: string, apiKey: string, deployment: string) {
    this.client = new OpenAI({
      apiKey,
      baseURL: `${endpoint}openai/deployments/${deployment}/`,
      defaultHeaders: { "api-key": apiKey }
    });
    this.deployment = deployment;
  }

  async generateChatCompletion(request: GenerativeRequest) {
    return this.client.chat.completions.create({
      model: this.deployment,
      temperature: request.temperature ?? 0.7,
      max_tokens: request.maxTokens ?? 800,
      messages: [
        { role: "system", content: request.systemPrompt },
        ...request.history
      ]
    });
  }
}
```

4. Consume it inside your bot (excerpt from `src/bot.ts`):

```ts
import { TurnContext, ActivityTypes } from "botbuilder";
import { AzureOpenAiService } from "./services/azureOpenAiService";

const openAiService = new AzureOpenAiService(
  process.env.AZURE_OPENAI_ENDPOINT!,
  process.env.AZURE_OPENAI_KEY!,
  process.env.AZURE_OPENAI_DEPLOYMENT!
);

export class GenAiBot {
  async onTurn(context: TurnContext): Promise<void> {
    if (context.activity.type === ActivityTypes.Message) {
      const userMessage = context.activity.text ?? "";

      const history = context.turnState.get("history") ?? [];
      const completion = await openAiService.generateChatCompletion({
        systemPrompt: "You are an enterprise assistant that answers with clear, concise responses.",
        history: [
          ...history,
          { role: "user", content: userMessage }
        ]
      });

      const reply = completion.choices[0]?.message?.content ?? "I’m sorry, I could not generate a response.";
      await context.sendActivity(reply);

      // Persist conversation history in ConversationState for future turns.
      history.push({ role: "assistant", content: reply });
      context.turnState.set("history", history);
    } else {
      await context.sendActivity(`[${context.activity.type} event detected]`);
    }
  }
}
```

## 6. Add Retrieval-Augmented Generation (Optional)

1. Index documents in Azure Cognitive Search with an index named `bot-knowledge`.
2. At runtime, fetch relevant passages:

```ts
import { SearchClient, AzureKeyCredential } from "@azure/search-documents";

const searchClient = new SearchClient(
  process.env.AZURE_SEARCH_ENDPOINT!,
  "bot-knowledge",
  new AzureKeyCredential(process.env.AZURE_SEARCH_KEY!)
);

async function getGroundingDocuments(query: string) {
  const results = await searchClient.search(query, {
    top: 5,
    queryType: "semantic",
    semanticConfiguration: "default",
    select: ["content", "source"],
  });

  const documents: string[] = [];
  for await (const result of results.results) {
    if (result.document.content) {
      documents.push(`Source: ${result.document.source}\n${result.document.content}`);
    }
  }
  return documents;
}
```

3. Inject the passages into your prompt:

```ts
const docs = await getGroundingDocuments(userMessage);
const completion = await openAiService.generateChatCompletion({
  systemPrompt: "Use the provided sources to answer. If unsure, say you don't know and cite sources.",
  history: [
    ...history,
    { role: "user", content: `${userMessage}\n\nContext:\n${docs.join("\n\n")}` }
  ]
});
```

## 7. Configure Middleware and State

1. Register storage in `index.ts`:

```ts
import { MemoryStorage, ConversationState, UserState } from "botbuilder";

const storage = process.env.REDIS_CONNECTION_STRING
  ? new CloudAdapterStorage(process.env.REDIS_CONNECTION_STRING)
  : new MemoryStorage();

const conversationState = new ConversationState(storage);
const userState = new UserState(storage);
```

2. Add middleware for telemetry, content moderation, or locale handling by using `adapter.use(new TelemetryLoggerMiddleware(appInsightsClient));`.

3. Remember to call `await conversationState.saveChanges(context);` at the end of each turn.

## 8. Local Testing

1. Run the bot locally:

```bash
npm run build
npm start
```

2. Start **Bot Framework Emulator** and connect to `http://localhost:3978/api/messages` with the Microsoft App ID/Password (or use the Emulator’s `open bot` with no credentials for local testing).

3. Validate message exchange, generative responses, and error handling. Use Emulator’s inspection features to review activities and state.

## 9. Deployment

1. **Hosting options**: Azure App Service (Web App), Azure Functions, or Azure Kubernetes Service.
2. **Publish** (App Service example):

```bash
az webapp up \
  --resource-group rg-bot-genai \
  --name genai-chatbot-app \
  --runtime "NODE|18-lts"
```

3. Update your bot Channels Registration endpoint to point to the hosted endpoint (`https://genai-chatbot-app.azurewebsites.net/api/messages`).
4. Configure CI/CD via GitHub Actions or Azure DevOps to automate builds, tests, and deployments.

## 10. Channel Configuration

1. In Azure Portal → your Bot resource → **Channels**, enable Microsoft Teams, Web Chat, or Direct Line.
2. For Web Chat, embed the control in your app:

```html
<script src="https://cdn.botframework.com/botframework-webchat/latest/webchat.js"></script>
<div id="webchat" role="main"></div>
<script>
  window.WebChat.renderWebChat({
    directLine: window.WebChat.createDirectLine({ token: "YOUR_DIRECT_LINE_TOKEN" })
  }, document.getElementById('webchat'));
</script>
```

3. Secure Direct Line tokens using your own back end and Azure AD.

## 11. Responsible AI and Operations

* **Content filtering:** Use Azure OpenAI content filters. Optionally add custom moderation middleware.
* **Telemetry:** Configure Application Insights for request logging, latency measurement, and analytics.
* **Feedback loops:** Capture thumbs-up/down events, store transcripts, and refine prompts or training data.
* **Versioning:** Maintain prompt templates, configuration, and LLM deployments in source control.

## 12. Next Steps

* Extend with **Adaptive Dialogs** for context-aware event handling.
* Add **Skill bots** for modularization.
* Integrate **Speech Services** for voice-enabled experiences.
* Explore **Bot Framework Composer** for low-code dialog design with code-behind LLM integration.

By combining Azure Bot Framework’s dialog/state infrastructure with Azure OpenAI’s generative power, you can deliver enterprise-grade conversational agents that blend structured workflows with natural, context-aware responses.
