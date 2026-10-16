#!/usr/bin/env bash
# One-time Azure setup for the demo, to be run in Azure Cloud Shell (the ">_" icon at the top of portal.azure.com,
# choose Bash; the Azure command-line tool is already there, nothing to install):
#
#     bash azure_setup.sh REGION          # for example: uksouth or westeurope
#
# It registers the services, creates a resource group, a Container Apps environment with no log workspace (so no
# request logs are collected or billed), the app (a placeholder image until the first deploy, at most one replica
# and none kept idle, 1 vCPU and 2 GiB) with the Gemini key and the access code stored as the app's own secrets
# (typed hidden), and a keyless sign-in for GitHub Actions that only this repository's main branch can use and that
# can change only this resource group. Safe to run again: steps that already exist are skipped. It was written
# without being run (there was no Azure account to run it in), so read the output, and check a command against
# Microsoft's documentation if one fails. At the end it prints the five values to enter as GitHub repository
# variables.
set -euo pipefail

LOCATION="${1:-}"
if [ -z "$LOCATION" ]; then
  echo "Usage: bash azure_setup.sh REGION (for example uksouth or westeurope; 'az account list-locations -o table' lists them)" >&2
  exit 1
fi

RESOURCE_GROUP="law-assistant-rg"
ENV_NAME="law-assistant-env"
APP="law-assistant"
REGISTRATION="law-assistant-deploy"
GITHUB_REPO="kevinpinoarias/eu-uk-data-ai-law-assistant"

echo "== Registering the services (the first time this can take a few minutes)"
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait

echo "== Resource group in $LOCATION"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

echo "== Container Apps environment (no log workspace)"
az containerapp env show --name "$ENV_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1 \
  || az containerapp env create --name "$ENV_NAME" --resource-group "$RESOURCE_GROUP" \
       --location "$LOCATION" --logs-destination none --output none

echo "== Secrets (typed hidden)"
read -rsp "Paste the Gemini API key for this project, then press Enter: " KEY
echo
read -rsp "Choose an access code for invited visitors (letters and digits, no spaces), then press Enter: " CODE
echo

echo "== The app"
if az containerapp show --name "$APP" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az containerapp secret set --name "$APP" --resource-group "$RESOURCE_GROUP" \
    --secrets "gemini-key=$KEY" "access-code=$CODE" --output none
else
  az containerapp create --name "$APP" --resource-group "$RESOURCE_GROUP" --environment "$ENV_NAME" \
    --image mcr.microsoft.com/k8se/quickstart:latest --target-port 80 --ingress external \
    --min-replicas 0 --max-replicas 1 --cpu 1.0 --memory 2.0Gi \
    --secrets "gemini-key=$KEY" "access-code=$CODE" \
    --env-vars GEMINI_API_KEY=secretref:gemini-key ACCESS_CODE=secretref:access-code --output none
fi
unset KEY CODE

echo "== Keyless sign-in for GitHub Actions"
APP_ID="$(az ad app list --display-name "$REGISTRATION" --query '[0].appId' --output tsv)"
if [ -z "$APP_ID" ]; then
  APP_ID="$(az ad app create --display-name "$REGISTRATION" --query appId --output tsv)"
  az ad sp create --id "$APP_ID" --output none
fi
SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
TENANT_ID="$(az account show --query tenantId --output tsv)"
# Only this resource group, nothing else in the subscription.
az role assignment create --assignee "$APP_ID" --role Contributor \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" --output none \
  || echo "(the role assignment already exists)"
# Only this repository's main branch can sign in.
az ad app federated-credential create --id "$APP_ID" --parameters "{
  \"name\": \"github-main\",
  \"issuer\": \"https://token.actions.githubusercontent.com\",
  \"subject\": \"repo:${GITHUB_REPO}:ref:refs/heads/main\",
  \"audiences\": [\"api://AzureADTokenExchange\"]
}" --output none || echo "(the federated credential already exists)"

echo
echo "Done. In GitHub: Settings, Secrets and variables, Actions, tab Variables, New repository variable. Add:"
echo "  AZURE_CLIENT_ID        = $APP_ID"
echo "  AZURE_TENANT_ID        = $TENANT_ID"
echo "  AZURE_SUBSCRIPTION_ID  = $SUBSCRIPTION_ID"
echo "  AZURE_RESOURCE_GROUP   = $RESOURCE_GROUP"
echo "  AZURE_CONTAINER_APP    = $APP"
echo "These are identifiers, not secrets. The sign-in can take a few minutes to start working."
