<p align="center">
  <img src="00-image-generation/assets/00_command_center_1024.png" alt="Promptling Command Center" width="400"/>
</p>

<h1 align="center">Microsoft Foundry for AI Engineers: Zero to Hero</h1>

<p align="center">
  <strong>Build, Scale, and Govern AI Applications in the Enterprise</strong>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#the-journey">The Journey</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#prerequisites">Prerequisites</a> •
  <a href="#resources">Resources</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Microsoft%20Foundry-blue?style=for-the-badge&logo=microsoft" alt="Microsoft Foundry"/>
  <img src="https://img.shields.io/badge/Python-3.10+-green?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge" alt="Status"/>
</p>

---

## Welcome, Explorer!

Meet **Promptling** — your friendly guide through the world of Microsoft Foundry! This repository is your progressive learning path from simple inference to building a full fleet of intelligent, governed AI agents.

<table>
<tr>
<td width="600" valign="top">

### What You'll Build

By the end of this journey, you'll have created agents that are:

- 🧠 **Grounded** — Using your enterprise data via Foundry IQ
- 🔧 **Capable** — Using tools via Model Context Protocol (MCP)
- 🤝 **Collaborative** — Orchestrated via the Microsoft Agent Framework 
- 👁️ **Observable** — Fully traced with OpenTelemetry
- 🏛️ **Governed** — Managed via AI Gateway & Control Plane

</td>
<td width="250" align="center" valign="top">
<img src="00-image-generation/assets/01_architect_256.png" alt="The Architect" width="200"/>
<br/>
<em>The Architect — Ready to build!</em>
</td>
</tr>
</table>

---

## Architecture

<table>
<tr>
<td width="300" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/02_hub_spoke_256.png" alt="Hub & Spoke" width="250"/>
</td>
<td valign="top">

<h3>Enterprise Hub & Spoke Model</h3>

<p>This repository implements an <strong>enterprise-first hub-and-spoke architecture</strong>:</p>

<table>
<thead>
<tr>
<th width="200">Component</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Landing Zone (Hub)</strong></td>
<td>All AI model deployments, APIM gateway, shared infrastructure</td>
</tr>
<tr>
<td><strong>App Teams (Spokes)</strong></td>
<td>Connect via APIM or Model Gateway — no direct deployments</td>
</tr>
</tbody>
</table>

<p><strong>Why this pattern?</strong></p>
<ul>
<li>✅ Centralized cost management</li>
<li>✅ Consistent security policies</li>
<li>✅ Model usage tracking & compliance</li>
<li>✅ Simplified lifecycle management</li>
</ul>

</td>
</tr>
</table>

---

## The Journey

Each phase builds upon the last. Follow Promptling through each adventure!

<table>
<tr>
<td colspan="2"><h3>Phase 1: Foundations & Setup</h3></td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/03_foundation_256.png" alt="Foundation" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./01-project-setup">Step 01: Project Setup</a></h4>
<em>Plant your flag and establish your foundation</em>
<br/><br/>
<table>
<thead>
<tr>
<th width="150">Lab</th>
<th width="300">Description</th>
</tr>
</thead>
<tbody>
<tr>
<td><a href="./01-project-setup/lab-1a-landing-zone">Lab 1A</a></td>
<td>🏗️ Deploy the Landing Zone (Hub)</td>
</tr>
<tr>
<td><a href="./01-project-setup/lab-1b-project-spoke">Lab 1B</a></td>
<td>🔌 Deploy a Project Spoke</td>
</tr>
<tr>
<td><a href="./01-project-setup/lab-1c-model-router">Lab 1C</a></td>
<td>🚦 Configure Model Router</td>
</tr>
</tbody>
</table>
</td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/06_scaling_up_256.png" alt="Scaling Up" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./02-inference">Step 02: Unified Inference</a></h4>
<em>Deploy models and scale your team</em>
<br/><br/>
<table>
<thead>
<tr>
<th width="150">Lab</th>
<th width="300">Description</th>
</tr>
</thead>
<tbody>
<tr>
<td><a href="./02-inference/lab-2a-team-spokes">Lab 2A</a></td>
<td>👥 Deploy Team Spokes</td>
</tr>
<tr>
<td><a href="./02-inference/lab-2b-direct-apim">Lab 2B</a></td>
<td>📡 Direct APIM Integration</td>
</tr>
</tbody>
</table>
</td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/08_guard_256.png" alt="The Guard" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./03-governance-policy">Step 03: Governance Policy</a></h4>
<em>Protect your infrastructure with policies</em>
<br/><br/>
<p>Deploy Azure Policy to prevent unauthorized model deployments in spokes. Keep your architecture secure and compliant!</p>
</td>
</tr>

<tr>
<td colspan="2"><h3>Phase 2: The Agent Service</h3></td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/09_container_256.png" alt="Container" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./04-hosted-agents">Step 04: Hosted Agents</a></h4>
<em>Deploy containerized agents with Azure Developer CLI</em>
<br/><br/>
<p>Use the official <code>Azure-Samples/ai-foundry-starter-basic</code> template to deploy production-ready hosted agents on Azure Container Apps.</p>
</td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/10_brain_256.png" alt="The Brain" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./05-agent-memory">Step 05: Agent Memory</a></h4>
<em>Give your agents the gift of memory</em>
<br/><br/>
<table>
<thead>
<tr>
<th width="150">Memory Type</th>
<th width="300">Description</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>User Profile</strong></td>
<td>Static preferences (dietary, etc.)</td>
</tr>
<tr>
<td><strong>Summary</strong></td>
<td>Distilled context from past chats</td>
</tr>
<tr>
<td><strong>Search</strong></td>
<td>Automatic memory retrieval</td>
</tr>
</tbody>
</table>
</td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/11_detective_256.png" alt="Detective" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./06-foundry-iq">Step 06: Foundry IQ</a></h4>
<em>Knowledge retrieval and RAG pipelines</em>
<br/><br/>
<p>Connect your agent to a Foundry IQ knowledge base for intelligent Retrieval Augmented Generation (RAG).</p>
</td>
</tr>

<tr>
<td colspan="2"><h3>Phase 3: Tools & Integration</h3></td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/12_mechanic_256.png" alt="Mechanic" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./07-tool-catalog">Step 07: Tool Catalog</a></h4>
<em>Equip your agents with powerful tools</em>
<br/><br/>
<table>
<thead>
<tr>
<th width="150">Lab</th>
<th width="300">Tools</th>
</tr>
</thead>
<tbody>
<tr>
<td><a href="./07-tool-catalog/lab-7a-builtin-tools">Lab 7A</a></td>
<td>🔧 Bing Search, Code Interpreter</td>
</tr>
<tr>
<td><a href="./07-tool-catalog/lab-7b-foundry-tools">Lab 7B</a></td>
<td>🔌 MCP Servers (GitHub, Slack)</td>
</tr>
<tr>
<td><a href="./07-tool-catalog/lab-7c-bing-grounding">Lab 7C</a></td>
<td>🌐 Bing Grounding</td>
</tr>
</tbody>
</table>
</td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/15_scholar_256.png" alt="Scholar" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./08-deep-research">Step 08: Deep Research</a></h4>
<em>Multi-step agentic research with citations</em>
<br/><br/>
<p>Build deep research pipelines with <code>o3-deep-research</code> model, NASA NTRS documents, and MCP integration.</p>
</td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/16_scanner_256.png" alt="Scanner" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./09-content-understanding">Step 09: Content Understanding</a></h4>
<em>Extract insights from any content type</em>
<br/><br/>
<table>
<thead>
<tr>
<th width="150">Content Type</th>
<th width="300">Capabilities</th>
</tr>
</thead>
<tbody>
<tr>
<td>📄 <strong>Documents</strong></td>
<td>Fields, tables, structure</td>
</tr>
<tr>
<td>🎬 <strong>Video</strong></td>
<td>Keyframes, transcripts, chapters</td>
</tr>
</tbody>
</table>
</td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/13_connector_256.png" alt="M365" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./11-agent-365">Step 10: M365 Copilot Integration</a> <sup><code>beta</code></sup></h4>
<em>Connect to Microsoft 365 ecosystem</em>
<br/><br/>
<p>Extend your agents to work with Microsoft 365 services and Copilot.</p>

<table>
<thead>
<tr>
<th width="150">Lab</th>
<th width="300">Description</th>
</tr>
</thead>
<tbody>
<tr>
<td><a href="./11-agent-365">Lab 10A</a></td>
<td>🧩 M365 Copilot Integration</td>
</tr>
<tr>
<td><a href="./14b-m365-foundry-publish">Lab 10B</a></td>
<td>🚀 Publish via Activity Protocol</td>
</tr>
</tbody>
</table>
</td>
</tr>

<tr>
<td colspan="2"><h3>Phase 4: Agent Orchestration</h3></td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/04_connection_256.png" alt="Connector" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./10-agent-registry">Step 11: Agent Registry</a></h4>
<em>Centralized agent discovery and management</em>
<br/><br/>
<p>Build a private tool catalog to manage agent discovery and organization-wide tools.</p>
</td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/07_legacy_line_256.png" alt="Workflow" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./12-agent-workflow">Step 12: Agent Workflow</a></h4>
<em>Multi-agent collaboration with Microsoft Agent Framework</em>
<br/><br/>
<p>Build a <strong>Planet Slideshow Builder</strong> with orchestrated agents:</p>
<pre>🎯 Planner → 🔍 Researcher → 📝 Reviewer → ⚖️ Judge</pre>
</td>
</tr>

<tr>
<td colspan="2"><h3>Phase 5: Reliability & Quality</h3></td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/14_telescope_256.png" alt="Telescope" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./15-observability">Step 13: Observability</a> <sup><code>beta</code></sup></h4>
<em>See everything with OpenTelemetry tracing</em>
<br/><br/>
<p>Trace multi-agent hops, tool latencies, and system performance in the Foundry portal.</p>
</td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/11_detective_256.png" alt="Evaluation" width="150"/>
</td>
<td width="800" valign="top">
<h4><a href="./16-evaluation">Step 14: Evaluation</a> <sup><code>beta</code></sup></h4>
<em>Assess AI quality and performance</em>
<br/><br/>
<p>Use the Azure AI Evaluation SDK for quality metrics (coherence, fluency, relevance, groundedness) and custom evaluators.</p>
</td>
</tr>

<tr>
<td colspan="2"><h3><a href="./01-project-setup/lab-1c-model-router">Model Router</a></h3></td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/05_traffic_control_256.png" alt="Traffic Control" width="150"/>
</td>
<td width="800" valign="top">

<p>Model Router automatically selects the best LLM for each request, optimizing for your priorities. See <a href="./01-project-setup/lab-1c-model-router">Lab 1C</a> to configure it.</p>

<table>
<thead>
<tr>
<th width="150">Mode</th>
<th width="300">Optimizes For</th>
</tr>
</thead>
<tbody>
<tr>
<td>⚖️ <strong>Balanced</strong></td>
<td>Quality, latency, and cost (default)</td>
</tr>
<tr>
<td>🏆 <strong>Quality</strong></td>
<td>Response quality</td>
</tr>
<tr>
<td>💰 <strong>Cost</strong></td>
<td>Cost optimization</td>
</tr>
<tr>
<td>⚡ <strong>Latency</strong></td>
<td>Response speed</td>
</tr>
</tbody>
</table>

<br/>
<h4>Supported Models</h4>
<table>
<thead>
<tr><th>Provider</th><th>Models</th></tr>
</thead>
<tbody>
<tr><td><strong>OpenAI</strong></td><td>gpt-5, gpt-5-mini, gpt-5-nano, gpt-4.1, gpt-4.1-mini, o4-mini</td></tr>
<tr><td><strong>Anthropic</strong></td><td>claude-haiku-4-5, claude-opus-4-1, claude-sonnet-4-5</td></tr>
<tr><td><strong>DeepSeek</strong></td><td>Deepseek-v3.1</td></tr>
<tr><td><strong>Meta</strong></td><td>llama4-maverick-instruct</td></tr>
<tr><td><strong>xAI</strong></td><td>grok-4, grok-4-fast</td></tr>
<tr><td><strong>Microsoft</strong></td><td>gpt-oss-120b</td></tr>
</tbody>
</table>
<br>
</td>
</tr>

<tr>
<td colspan="2"><h3>Safety & Guardrails</h3></td>
</tr>
<tr>
<td width="200" align="center" valign="top">
<br/>
<img src="00-image-generation/assets/08_guard_256.png" alt="Guard" width="150"/>
</td>
<td width="800" valign="top">

<h4>Protect Your AI Systems</h4>

<p><a href="./16-red-teaming">Red Teaming</a> <sup><code>beta</code></sup> — Scan for vulnerabilities with AI Red Teaming Agent (PyRIT)</p>
<p><a href="./13-human-in-loop">Human-in-Loop</a> <sup><code>beta</code></sup> — Add manual approval for sensitive actions</p>

</td>
</tr>
</table>

---

## Prerequisites

Before you begin, ensure you have:

| Requirement | Description |
|-------------|-------------|
| ☁️ **Azure Subscription** | Owner or User Access Administrator permissions |
| 🐍 **Python 3.10+** | For running notebooks and scripts |
| 🔧 **Azure CLI** | [Download here](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| 💻 **VS Code** | With [Microsoft Foundry Extension](https://aka.ms/azureaifoundry/vscode) |

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/aymenfurter/AI-Engineer-Zero-to-Hero.git
cd AI-Engineer-Zero-to-Hero

# 2. Authenticate with Azure
az login

# 3. Create your .env file
cp .env.sample .env
# Edit .env with your Foundry connection string

# 4. Start with Step 01!
cd 01-project-setup
```

---

## Landing Zone Support Matrix

The following table shows how each lab's features integrate with the centralized Landing Zone architecture:

| Lab | Feature | Support Level | Notes |
|-----|---------|---------------|-------|
| **00 - Image Gen** | gpt-image-1.5 | APIM | Supports APIM (notebook not yet updated) |
| **01a - Landing Zone** | Hub deployment | APIM | Deploys central APIM gateway + model deployments |
| **01b - Project Spoke** | Spoke + APIM connection | Connection | Spoke consumes models via APIM connection |
| **01c - Model Router** | model-router deployment | APIM | Intelligent routing across models |
| **02a - Team Spokes** | Multi-team model access | Connection | Teams access models via `<connection>/<model>` |
| **02b - Direct APIM** | REST API access | APIM | Direct APIM calls without Foundry SDK |
| **05 - Agent Memory** | Memory API | Hybrid | Chat via APIM, but Memory API needs local embedding model |
| **06 - Foundry IQ** | Knowledge bases | Connection | RAG via APIM for both chat and embeddings |
| **07a - Built-in Tools** | File Search, Code Interpreter | Hybrid | File Search requires local model, Code Interpreter works via APIM |
| **07b - AI Gateway MCP** | MCP tool governance | APIM | Extends APIM to govern MCP tool calls |
| **07c - Web Search** | Bing grounding | Local | Web search tool requires local model |
| **08 - Deep Research** | o3-deep-research | APIM | Full APIM support via Norway East hub |
| **09 - Content Understanding** | Document/video analysis | Local | CU requires GPT-4.1 + embeddings in same resource |
| **12 - Agent Workflow** | Multi-agent orchestration | APIM | Microsoft Agent Framework via APIM gateway |
| **13 - Human-in-Loop** | Function approval | APIM | Works with APIM-based agents |
| **16 - Local Evaluation** | Azure AI Evaluation SDK | APIM | Evaluators use APIM for judge model |

---

## Repository Structure

```
AI-Engineer-Zero-to-Hero/
├── 📖 README.md                    # You are here!
├── 🎨 00-image-generation/         # Promptling mascot images
├── 🏗️ 01-project-setup/            # Phase 1: Foundations
│   ├── lab-1a-landing-zone/
│   ├── lab-1b-project-spoke/
│   └── lab-1c-model-router/
├── 🔄 02-inference/                # Unified inference
├── 🛡️ 03-governance-policy/        # Azure Policy
├── 📦 04-hosted-agents/            # Hosted agents
├── 🧠 05-agent-memory/             # Memory service
├── 🔍 06-foundry-iq/               # Knowledge & RAG
├── 🔧 07-tool-catalog/             # Tools & MCP
├── 📚 08-deep-research/            # Research pipelines
├── 📄 09-content-understanding/    # Document/video analysis
├── 📋 10-agent-registry/           # Agent discovery
├── 🔗 11-agent-365/                # M365 integration (Step 10)
├── 🔀 12-agent-workflow/           # Multi-agent orchestration
├── 👤 13-human-in-loop/            # Safety: Human approval
├── 14-m365-integration/         # Additional M365
├── 14b-m365-foundry-publish/    # Publish Agents via Activity Protocol
├── 15-observability/            # Tracing & monitoring
├── 📊 16-evaluation/               # AI quality evaluation
└── 🔴 16-red-teaming/              # Safety: Red teaming
```

---

## Resources

<table>
<tr>
<td width="240">

### Documentation
- 🌐 [Foundry Portal](https://ai.azure.com)
- 📚 [Official Docs](https://learn.microsoft.com/azure/ai-foundry/)
- 📊 [Evaluation Guide](https://learn.microsoft.com/azure/ai-foundry/how-to/evaluate-generative-ai-app)
- 🛡️ [Content Safety](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/content-filters)

</td>
<td width="240">

### Tools & SDKs
- 🔌 [Model Context Protocol](https://modelcontextprotocol.io)
- 🚪 [APIM GenAI Gateway](https://learn.microsoft.com/azure/api-management/genai-gateway-capabilities)
- 📦 [Foundry Samples](https://github.com/azure-ai-foundry/foundry-samples)
- 📈 [Status Page](https://status.ai.azure.com)

</td>
</tr>
</table>

---

## Roadmap

- **Advanced Observability Lab** — Deep dive into tracing with Foundry Agents and Application Insights integration
- **Cloud Evaluations Lab** — Run evaluations at scale using Foundry's cloud-based evaluation infrastructure
- **Speech Capabilities Lab** — Explore Foundry's voice features including the Voice Live API
- **Basic vs Standard Agent Deployment** — Configure secure access to resources used within Agents (VNet integration, private endpoints)

*Have ideas for new labs? [Open an issue](https://github.com/aymenfurter/AI-Engineer-Zero-to-Hero/issues) or submit a PR!*

---

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit a pull request.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <img src="00-image-generation/assets/00_command_center_256.png" alt="Promptling" width="100"/>
</p>

<p align="center">
  <strong>Happy Building! 🚀</strong><br/>
  <em>— Promptling & Aymen</em>
</p>

<p align="center">
  <sub>Built with 💙 for AI</sub>
</p>
