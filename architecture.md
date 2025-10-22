# 🏗️ AutoTriage & AutoFix Agent - Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AutoTriage & AutoFix Agent                              │
│                     AWS Bedrock AgentCore Powered System                        │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub Repo   │    │   GitHub Repo   │    │   GitHub Repo   │
│   (Issues)      │    │   (Issues)      │    │   (Issues)      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ Webhook Events       │ Webhook Events       │ Webhook Events
          │ (Issues Opened)      │ (Issues Edited)      │ (Issues Reopened)
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              API Gateway                                        │
│                         /github-webhook endpoint                                │
└─────────────────────────────────────────────────────────────────────────────────┘
          │
          │ HTTP POST
          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        Lambda: Webhook Handler                                  │
│  • Validates GitHub signature                                                   │
│  • Extracts issue context                                                       │
│  • Filters eligible issues                                                      │
│  • Triggers orchestrator asynchronously                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
          │
          │ Async Invocation
          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      Lambda: Agent Orchestrator                                  │
│  • Retrieves agent memory from DynamoDB                                         │
│  • Builds comprehensive prompt                                                  │
│  • Calls Bedrock AgentCore for reasoning                                       │
│  • Executes agent actions via tools                                             │
│  • Stores results and learns from outcomes                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
          │
          │ Agent Reasoning
          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        Amazon Bedrock AgentCore                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │   Memory        │  │   Tools         │  │   Reasoning     │                │
│  │   Primitive     │  │   Primitive      │  │   Primitive     │                │
│  │                 │  │                 │  │                 │                │
│  │ • Past fixes    │  │ • GitHub API    │  │ • Claude 3.5    │                │
│  │ • Patterns      │  │ • CodeBuild     │  │ • Decision      │                │
│  │ • Learning      │  │ • S3 Storage    │  │ • Planning      │                │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────────┘
          │
          │ Tool Execution
          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Agent Tools                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │  GitHub Tool    │  │ CodeBuild Tool   │  │    S3 Tool       │                │
│  │                 │  │                  │  │                  │                │
│  │ • Create branch │  │ • Start builds   │  │ • Store patches  │                │
│  │ • Apply patches │  │ • Monitor tests  │  │ • Store logs     │                │
│  │ • Open PRs      │  │ • Get results    │  │ • Store artifacts│                │
│  │ • Add labels    │  │ • Wait for completion│ • Retrieve data │                │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────────┘
          │
          │ Actions
          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Execution Results                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │   GitHub PR      │  │  Test Results   │  │   S3 Artifacts  │                │
│  │                  │  │                  │  │                  │                │
│  │ • Auto-created   │  │ • Pass/Fail      │  │ • Patches        │                │
│  │ • With reasoning │  │ • Logs           │  │ • Logs           │                │
│  │ • Labeled        │  │ • Coverage       │  │ • Memory         │                │
│  │ • Ready to merge │  │ • Performance    │  │ • Metrics        │                │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────────┘
          │
          │ Monitoring & Learning
          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Data Storage                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │   DynamoDB      │  │   Amazon S3     │  │  CloudWatch     │                │
│  │                 │  │                  │  │                  │                │
│  │ • Agent Memory  │  │ • Artifacts      │  │ • Logs           │                │
│  │ • Past Fixes    │  │ • Patches        │  │ • Metrics        │                │
│  │ • Patterns      │  │ • Test Results  │  │ • Alarms        │                │
│  │ • Learning      │  │ • Logs           │  │ • Dashboards     │                │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────────┘
          │
          │ Human Oversight (Optional)
          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Human Interface                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │   Dashboard     │  │   Amazon Q      │  │   GitHub UI     │                │
│  │   (S3 + CF)     │  │   Chat          │  │   Integration   │                │
│  │                 │  │                  │  │                  │                │
│  │ • Status        │  │ • Chat with     │  │ • Review PRs    │                │
│  │ • Metrics       │  │   agent         │  │ • Approve       │                │
│  │ • History       │  │ • Inspect       │  │ • Merge         │                │
│  │ • Real-time     │  │   reasoning     │  │ • Feedback      │                │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. **GitHub Integration**
- **Webhook Events**: Issues opened, edited, reopened
- **API Operations**: Branch creation, file updates, PR creation
- **Security**: Token-based authentication, signature verification

### 2. **AWS Bedrock AgentCore**
- **Memory Primitive**: Learns from past fixes and patterns
- **Tools Primitive**: Integrates with GitHub, CodeBuild, S3
- **Reasoning Primitive**: Claude 3.5 Sonnet for decision making

### 3. **Lambda Functions**
- **Webhook Handler**: Validates and routes GitHub events
- **Agent Orchestrator**: Manages the complete agent workflow

### 4. **Storage & Persistence**
- **DynamoDB**: Agent memory and learning data
- **S3**: Artifacts, patches, logs, test results
- **CloudWatch**: Monitoring, logging, metrics

### 5. **Testing & Validation**
- **CodeBuild**: Automated test execution
- **GitHub Actions**: CI/CD integration
- **Quality Gates**: Pass/fail criteria

## Data Flow

1. **Issue Creation** → GitHub webhook → API Gateway
2. **Event Processing** → Lambda webhook handler → validation
3. **Agent Invocation** → Lambda orchestrator → Bedrock AgentCore
4. **Reasoning** → Claude 3.5 → decision making
5. **Tool Execution** → GitHub API → branch creation, patches
6. **Testing** → CodeBuild → automated validation
7. **PR Creation** → GitHub API → pull request with explanation
8. **Learning** → DynamoDB → memory storage for future improvements

## Security Architecture

- **IAM Roles**: Least privilege access for each component
- **Secrets Management**: GitHub tokens in environment variables
- **Network Security**: VPC endpoints (optional)
- **Data Encryption**: At rest and in transit
- **Audit Logging**: Complete action trail

## Scalability Features

- **Serverless**: Auto-scaling Lambda functions
- **Async Processing**: Non-blocking operations
- **Memory Management**: Efficient DynamoDB queries
- **Artifact Cleanup**: S3 lifecycle policies
- **Rate Limiting**: GitHub API rate limit handling

## Monitoring & Observability

- **CloudWatch Logs**: Detailed execution logs
- **CloudWatch Metrics**: Performance and success rates
- **S3 Artifacts**: Complete audit trail
- **Dashboard**: Real-time status and metrics
- **Alarms**: Automated alerting for failures

## Cost Optimization

- **Serverless**: Pay-per-use model
- **S3 Lifecycle**: Automatic cleanup of old artifacts
- **DynamoDB**: On-demand billing
- **Lambda**: Optimized memory and timeout settings
- **CodeBuild**: Minimal build time and resources
