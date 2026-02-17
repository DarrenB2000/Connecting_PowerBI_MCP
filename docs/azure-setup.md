# Azure App Registration Setup Guide

This guide explains how to create and configure a custom Azure App Registration for the PowerBI MCP CLI application.

## Table of Contents

- [Why Use Custom App Registration?](#why-use-custom-app-registration)
- [Prerequisites](#prerequisites)
- [Step-by-Step Setup](#step-by-step-setup)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Why Use Custom App Registration?

**Default Device Code Flow (Recommended for Getting Started)**
- No Azure setup required
- Uses Microsoft's public client ID
- Works with any Microsoft account
- Good for personal use and testing

**Custom App Registration (Recommended for Production)**
- Full control over permissions and security
- Better for organizational/enterprise use
- Can restrict to specific tenants
- Audit logs and monitoring in your Azure tenant
- Required for some compliance scenarios

## Prerequisites

Before you begin, you need:

1. **Azure Account** with permissions to create app registrations
   - Global Administrator, Application Administrator, or Cloud Application Administrator role
   - Or a user with "App registrations" create permission

2. **PowerBI Access** in your Microsoft 365 tenant
   - PowerBI Pro or Premium license
   - Access to at least one workspace

3. **Azure Portal Access**
   - Navigate to [portal.azure.com](https://portal.azure.com)

## Step-by-Step Setup

### Step 1: Create App Registration

1. Navigate to [Azure Portal](https://portal.azure.com)

2. Go to **Azure Active Directory** (or **Microsoft Entra ID**)
   - Use the search bar at the top or find it in the left menu

3. Click **App registrations** in the left sidebar

4. Click **+ New registration** at the top

5. Fill in the registration form:
   ```
   Name: PowerBI MCP CLI
   Supported account types:
     ○ Accounts in this organizational directory only (Single tenant)
     ● Accounts in any organizational directory (Multi-tenant)  [RECOMMENDED]
     ○ Accounts in any organizational directory and personal Microsoft accounts

   Redirect URI: Leave blank (not needed for device code flow)
   ```

6. Click **Register**

### Step 2: Note Your IDs

After registration, you'll see the **Overview** page. Copy these values:

- **Application (client) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Directory (tenant) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

You'll need these for your `.env` file.

### Step 3: Configure API Permissions

1. In your app registration, click **API permissions** in the left sidebar

2. You should see "Microsoft Graph" with "User.Read" - that's fine to keep

3. Click **+ Add a permission**

4. Select **APIs my organization uses**

5. Search for **Power BI Service** and select it

6. Select **Delegated permissions**

7. Expand and check these permissions:
   ```
   ✓ Dataset.Read.All
   ✓ Dataset.ReadWrite.All
   ✓ Workspace.Read.All
   ✓ Workspace.ReadWrite.All
   ✓ Content.Create
   ✓ Dataflow.Read.All
   ✓ Report.Read.All
   ```

   **Note**: The exact permissions needed depend on what you want to do:
   - **Minimum (read-only)**: `Dataset.Read.All`, `Workspace.Read.All`
   - **Full access**: All permissions listed above

8. Click **Add permissions**

9. (Optional but recommended) Click **Grant admin consent for [Your Organization]**
   - This pre-approves permissions for all users
   - Requires admin privileges
   - If you can't do this, users will be prompted to consent individually

### Step 4: Enable Public Client Flow

1. Click **Authentication** in the left sidebar

2. Scroll down to **Advanced settings**

3. Under **Allow public client flows**, set to **Yes**

4. Click **Save** at the top

### Step 5: Configure Token Settings (Optional)

1. Click **Token configuration** in the left sidebar

2. (Optional) Click **+ Add optional claim**
   - Token type: **ID**
   - Select: `email`, `preferred_username`
   - Click **Add**

3. This helps identify which user authenticated

## Configuration

### Update Your `.env` File

1. Open your `.env` file in the project root

2. Add your Azure app registration details:

   ```bash
   # Required: Claude API Key
   CLAUDE_API_KEY=sk-ant-your-key-here

   # Custom Azure App Registration
   AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

3. Save the file

### Test Your Configuration

1. Delete any cached tokens:
   ```bash
   rm -rf ~/.powerbi-mcp/token_cache.bin
   ```

2. Run the application:
   ```bash
   python main.py
   ```

3. You should see the device code authentication flow using **your** app registration

4. After authenticating, verify you can connect to PowerBI

## Configuration Options

### Using Specific Scopes

If you need to customize the OAuth scopes, you can set them in `.env`:

```bash
# Custom scopes (comma-separated)
AZURE_SCOPES=https://analysis.windows.net/powerbi/api/Dataset.Read.All,https://analysis.windows.net/powerbi/api/Workspace.Read.All
```

**Note**: The current application uses the scope `https://analysis.windows.net/powerbi/api/.default` which automatically includes all permissions you've granted in the Azure portal.

### Single Tenant vs Multi-Tenant

**Single Tenant** (`AZURE_TENANT_ID=your-specific-tenant-id`)
- Only users from your organization can authenticate
- More secure for enterprise use
- Set tenant ID to your organization's tenant ID

**Multi-Tenant** (`AZURE_TENANT_ID=common`)
- Users from any organization can authenticate
- More flexible for multi-org scenarios
- Set tenant ID to "common" or leave blank

## Comparison: Default vs Custom App

| Feature | Default Device Code Flow | Custom App Registration |
|---------|-------------------------|------------------------|
| Azure setup required | ❌ No | ✅ Yes |
| Works immediately | ✅ Yes | ❌ Requires setup |
| Full permission control | ❌ No | ✅ Yes |
| Audit logs in your tenant | ❌ No | ✅ Yes |
| Tenant restrictions | ❌ No | ✅ Yes |
| Production use | ⚠️ OK for testing | ✅ Recommended |
| Admin consent required | ❌ No | ⚠️ Optional but recommended |

## Troubleshooting

### Error: "AADSTS700016: Application not found"

**Solution**: Double-check your `AZURE_CLIENT_ID` in `.env` - it should match exactly what's shown in Azure Portal.

### Error: "AADSTS50020: User account from identity provider does not exist in tenant"

**Solution**:
- If using single-tenant app, ensure `AZURE_TENANT_ID` matches your organization
- Or change to multi-tenant and use `AZURE_TENANT_ID=common`

### Error: "Insufficient privileges to complete the operation"

**Solution**:
1. Verify API permissions in Azure Portal
2. Grant admin consent for the permissions
3. Or have the user consent during authentication

### Error: "The user or administrator has not consented to use the application"

**Solution**:
1. Have an admin grant consent in Azure Portal
2. Or users will be prompted to consent on first login
3. Make sure "Allow public client flows" is enabled

### Authentication works but can't access PowerBI

**Solution**:
1. Verify the user has PowerBI Pro/Premium license
2. Check API permissions include the necessary PowerBI scopes
3. Ensure the user has access to at least one PowerBI workspace

### Want to switch back to default device code flow

**Solution**: Comment out or remove these lines from `.env`:
```bash
# AZURE_TENANT_ID=...
# AZURE_CLIENT_ID=...
```

The application will automatically fall back to default device code flow.

## Security Best Practices

1. **Never commit `.env` to source control**
   - Already included in `.gitignore`
   - Keep your tenant/client IDs secure

2. **Use admin consent in production**
   - Reduces user friction
   - Better security oversight

3. **Regularly review app permissions**
   - Remove unnecessary permissions
   - Monitor usage in Azure Portal

4. **Consider using managed identities**
   - For server-based deployments
   - Eliminates credential management

5. **Enable conditional access policies**
   - Require MFA
   - Restrict by location/device
   - Available in Azure AD Premium

## Additional Resources

- [Microsoft Authentication Library (MSAL) Documentation](https://learn.microsoft.com/en-us/azure/active-directory/develop/msal-overview)
- [PowerBI REST API Documentation](https://learn.microsoft.com/en-us/rest/api/power-bi/)
- [Azure AD App Registration Best Practices](https://learn.microsoft.com/en-us/azure/active-directory/develop/security-best-practices-for-app-registration)
- [Device Code Flow Documentation](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-device-code)

## Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review Azure Portal's sign-in logs: **Azure AD** → **Sign-in logs**
3. Check the application logs in your terminal
4. Verify configuration with: `python test_config.py`

For application-specific issues, see the main [README.md](../README.md).
