# Azure Deployment Command Log

Chronological record of Azure/GitHub deployment commands used or attempted for MatchSense, plus the next proposed command block. Commands are intended for PowerShell. Resource identifiers are recorded; do not add passwords, access tokens, client secrets, or one-time codes. Update this file whenever we use another deployment command.

## 1. Install Azure CLI

```powershell
winget install --id Microsoft.AzureCLI --exact
```

## 2. Sign in and select subscription

```powershell
az login --tenant 4b4e16d6-b388-4483-809b-e7d6d74edc16
```

Selected `Azure subscription 1` (`9109b654-0666-477d-9f31-feafb5e4057a`).

## 3. Check active subscription

```powershell
az account show --output table
```

## 4. Register Azure resource providers

```powershell
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.ContainerRegistry
```

Check provider status with:

```powershell
az provider show --namespace Microsoft.App --query registrationState --output tsv
az provider show --namespace Microsoft.ContainerRegistry --query registrationState --output tsv
az provider show --namespace Microsoft.OperationalInsights --query registrationState --output tsv
```

All three providers were confirmed as `Registered`.

## 5. Create resource group and Azure Container Registry

```powershell
$RG = "rg-matchsense-demo"
$LOCATION = "centralindia"
$ACR = "matchsenseacr$(Get-Random -Minimum 10000 -Maximum 99999)"

az group create --name $RG --location $LOCATION
az acr create --name $ACR --resource-group $RG --location $LOCATION --sku Basic --admin-enabled false

Write-Output "Resource group: $RG"
Write-Output "Registry: $ACR"
az acr show --name $ACR --resource-group $RG --query "{name:name,loginServer:loginServer,sku:sku.name}" --output table
```

Created resource group `rg-matchsense-demo` and Basic ACR `matchsenseacr77036` (`matchsenseacr77036.azurecr.io`) in Central India.

## 6. Verify deployment prerequisites

```powershell
az account show --query "{subscription:name,tenant:tenantId}" --output table
az acr show --name matchsenseacr77036 --resource-group rg-matchsense-demo --query "{registry:name,loginServer:loginServer,id:id}" --output table
gh auth status
```

Confirmed Azure subscription and registry; GitHub CLI authenticated as `Roy-developer`.

## 7. Build and publish image

Build and publish the image with GitHub Actions using its hosted runner and Azure Container Registry. This avoids using local disk for Docker builds.

## 9. Create GitHub Actions deployment identity (completed)

```powershell
$appId = az ad app create `
  --display-name "matchsense-github-actions" `
  --query appId --output tsv

az ad sp create --id $appId

$spObjectId = az ad sp show `
  --id $appId `
  --query id --output tsv

Write-Output "Application (client) ID: $appId"
Write-Output "Service principal object ID: $spObjectId"
```

Created successfully. Application/client ID: `8a5fc722-806e-4806-a222-f42f9222bcb4`; service principal object ID: `cadce3eb-6d2a-4036-a426-79d5b6ea253d`.

## Current deployment identifiers

- Subscription: `Azure subscription 1` (`9109b654-0666-477d-9f31-feafb5e4057a`)
- Tenant: `4b4e16d6-b388-4483-809b-e7d6d74edc16`
- Resource group: `rg-matchsense-demo`
- Region: `centralindia`
- ACR: `matchsenseacr77036`
- ACR login server: `matchsenseacr77036.azurecr.io`
- GitHub repository: `Roy-developer/matchsense-ai`

## 10. Configure GitHub Actions OIDC trust (completed)

```powershell
$paramsFile = Join-Path $env:TEMP "github-main-federation.json"
@'
{
  "name": "github-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:Roy-developer/matchsense-ai:ref:refs/heads/main",
  "description": "GitHub Actions deployment from main",
  "audiences": ["api://AzureADTokenExchange"]
}
'@ | Set-Content -Path $paramsFile -Encoding utf8

az ad app federated-credential create `
  --id 8a5fc722-806e-4806-a222-f42f9222bcb4 `
  --parameters "@$paramsFile"

if ($LASTEXITCODE -eq 0) {
  Remove-Item $paramsFile
}
```

Created successfully. Federated credential ID: `f8893940-ed26-4273-8392-5c7ab4637eff`. GitHub Actions tokens from `Roy-developer/matchsense-ai` on branch `main` are now trusted by this app registration. This does not grant Azure resource permissions by itself.

## 11. Grant ACR push permission (completed)

```powershell
$ACR_ID = az acr show --name matchsenseacr77036 --resource-group rg-matchsense-demo --query id --output tsv

az role assignment create `
  --assignee-object-id cadce3eb-6d2a-4036-a426-79d5b6ea253d `
  --assignee-principal-type ServicePrincipal `
  --role AcrPush `
  --scope $ACR_ID
```

`AcrPush` grants push/pull access at this registry's scope only. `$ACR_ID` resolves the registry resource ID; the assignee is the deployment service principal object ID. It does not grant Container Apps deployment rights. Created successfully; role assignment ID: `eba037e2-9384-4fcc-9d19-d8dd33b341a2`.

```powershell
$paramsFile = Join-Path $env:TEMP "github-main-federation.json"
@'
{
  "name": "github-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:Roy-developer/matchsense-ai:ref:refs/heads/main",
  "description": "GitHub Actions deployment from main",
  "audiences": ["api://AzureADTokenExchange"]
}
'@ | Set-Content -Path $paramsFile -Encoding utf8

az ad app federated-credential create --id 8a5fc722-806e-4806-a222-f42f9222bcb4 --parameters "@$paramsFile"
if ($LASTEXITCODE -eq 0) { Remove-Item $paramsFile }
```

This trusts only GitHub Actions tokens from `Roy-developer/matchsense-ai` on branch `main`. It does not grant Azure resource permissions by itself. Do not record tokens or credentials in this log.

## 12. Grant Contributor on the MatchSense resource group (completed)

First resolve the resource group's full Azure resource ID, then create a role assignment for the GitHub Actions service principal.

```powershell
$RG_ID = az group show --name rg-matchsense-demo --query id --output tsv
Write-Output "Resource group scope: $RG_ID"

az role assignment create `
  --assignee-object-id cadce3eb-6d2a-4036-a426-79d5b6ea253d `
  --assignee-principal-type ServicePrincipal `
  --role Contributor `
  --scope $RG_ID
```

This grants the GitHub Actions service principal permission to manage resources inside `rg-matchsense-demo` only. It can create, update, or delete resources there, but cannot grant roles to identities. It does not grant access to resources outside this group or to the subscription itself. Created successfully. Role assignment ID: `7a818c6a-4157-445b-88ab-c3014dc820e9`.
## 13. Verify Contributor assignment (next; user runs after step 12 succeeds)

```powershell
$RG_ID = az group show --name rg-matchsense-demo --query id --output tsv
az role assignment list --scope $RG_ID --include-inherited --query "[?principalId=='cadce3eb-6d2a-4036-a426-79d5b6ea253d'].{role:roleDefinitionName,principal:principalId,scope:scope}" --output table
```

Verified: `Contributor` appears for service principal `cadce3eb-6d2a-4036-a426-79d5b6ea253d` at `/subscriptions/9109b654-0666-477d-9f31-feafb5e4057a/resourceGroups/rg-matchsense-demo`.

## 14. Set GitHub repository variables for Azure (completed)

```powershell
gh variable set AZURE_CLIENT_ID --body "8a5fc722-806e-4806-a222-f42f9222bcb4" --repo Roy-developer/matchsense-ai
gh variable set AZURE_TENANT_ID --body "4b4e16d6-b388-4483-809b-e7d6d74edc16" --repo Roy-developer/matchsense-ai
gh variable set AZURE_SUBSCRIPTION_ID --body "9109b654-0666-477d-9f31-feafb5e4057a" --repo Roy-developer/matchsense-ai
gh variable set AZURE_RESOURCE_GROUP --body "rg-matchsense-demo" --repo Roy-developer/matchsense-ai
gh variable set AZURE_LOCATION --body "centralindia" --repo Roy-developer/matchsense-ai
gh variable set ACR_NAME --body "matchsenseacr77036" --repo Roy-developer/matchsense-ai
gh variable set ACR_LOGIN_SERVER --body "matchsenseacr77036.azurecr.io" --repo Roy-developer/matchsense-ai
```

These are repository-level configuration variables, not secrets. They let GitHub Actions identify the Azure app, subscription, resource group, region, and registry. No credentials are stored. Created and verified with `gh variable list --repo Roy-developer/matchsense-ai`; all seven variables are present.

## 15. Create manual workflow to test and publish image (created locally; not yet pushed)

Created `.github/workflows/publish-image.yml`. It triggers manually, runs tests, then uses GitHub OIDC on `main` to authenticate to Azure, logs into ACR, and builds/pushes `matchsense-ai` tagged with the commit SHA and `latest`. The existing CI workflow remains unchanged. No Container Apps deployment is included yet. The workflow must be reviewed, committed, and pushed before it can be run on GitHub. Include the Dockerfile data-path correction and `.dockerignore` in that push as well.

## 16. Review, commit, and push workflow changes (in progress)

The first commit attempt stopped because Git has no `user.name`/`user.email` configured in this checkout. The latest repository commit uses `Debadyuti Saha Roy <saharoydebdyuti1991@gmail.com>`. Configure that identity locally for this repository only, then retry the commit/push. Do not change global Git identity.

```powershell
git config user.name "Debadyuti Saha Roy"
git config user.email "saharoydebdyuti1991@gmail.com"
```

Reviewed with `git status --short`, `git diff --check`, `git diff -- Dockerfile`, `Get-Content .dockerignore`, and `Get-Content .github/workflows/publish-image.yml`. Pending files are the Dockerfile data-path fix, `.dockerignore`, the manual publish workflow, and this command log.

```powershell
git add Dockerfile .dockerignore .github/workflows/publish-image.yml azure-deployment-commands.md
git commit -m "Add Azure image publishing workflow" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git push origin main
```

After push succeeds, manually dispatch with `gh workflow run publish-image.yml --repo Roy-developer/matchsense-ai --ref main`; inspect runs with `gh run list --repo Roy-developer/matchsense-ai --workflow publish-image.yml --limit 3` and `gh run watch <run-id> --repo Roy-developer/matchsense-ai --exit-status`. This publish-only workflow does not deploy Container Apps.
