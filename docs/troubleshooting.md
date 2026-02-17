# Troubleshooting Guide

Comprehensive troubleshooting guide for PowerBI MCP CLI issues.

## Table of Contents

- [Schema Not Returned](#schema-not-returned)
- [Authentication Issues](#authentication-issues)
- [Connection Problems](#connection-problems)
- [Tool Execution Failures](#tool-execution-failures)
- [Debug Mode](#debug-mode)

---

## Schema Not Returned

**Symptom**: MCP server connects but `GetSemanticModelSchema` returns no data or empty response.

### Quick Diagnostic Test

Run the diagnostic script:

```bash
python test_powerbi_tools.py
```

This will test each tool and show exactly what's happening.

### Common Causes

#### 1. Tool Requires Parameters

**Issue**: `GetSemanticModelSchema` requires specific parameters (workspace ID, dataset ID, etc.)

**Solution**: Check what parameters are required:

```bash
python test_powerbi_tools.py
```

Look for the tool's parameter requirements in the output.

**Example**: If the tool requires `workspaceId` and `datasetId`:
- You need to know these IDs first
- Ask Claude to list workspaces/datasets first
- Then use those IDs to get the schema

#### 2. No PowerBI Workspaces Accessible

**Issue**: Your account doesn't have access to any PowerBI workspaces.

**Check**:
1. Log into [powerbi.microsoft.com](https://powerbi.microsoft.com)
2. Verify you can see at least one workspace
3. Check you have at least "Viewer" role in that workspace

**Solution**:
- Create a workspace in PowerBI
- Or request access to an existing workspace
- Ensure you have PowerBI Pro or Premium license

#### 3. Missing PowerBI Permissions

**Issue**: Azure app doesn't have the necessary PowerBI API permissions.

**Check**: In Azure Portal → Your App → API Permissions, verify:
- `Dataset.Read.All` (minimum for schema)
- `Workspace.Read.All` (to list workspaces)

**Solution**: See [Azure Setup Guide](azure-setup.md) Step 3 to add permissions.

#### 4. Empty Dataset

**Issue**: The dataset exists but has no schema/tables.

**Solution**: Verify the dataset has published schema in PowerBI portal.

#### 5. Result Format Issue

**Issue**: Schema is returned but not displayed correctly.

**Check**: Run with debug logging (see [Debug Mode](#debug-mode))

### Step-by-Step Troubleshooting

```bash
# 1. Run diagnostic test
python test_powerbi_tools.py

# 2. Check what parameters GetSemanticModelSchema needs
# (Output will show required parameters)

# 3. If it needs workspace/dataset IDs, try a simpler query first
# In the app, ask: "What workspaces do I have access to?"

# 4. Once you have IDs, ask for schema
# "Get the schema for dataset <id> in workspace <id>"
```

---

## Authentication Issues

### Error: "AADSTS7000218: client_assertion or client_secret required"

**Cause**: Azure app not configured for public client flows.

**Solution**:
1. Azure Portal → Your App → Authentication
2. Advanced Settings → Allow public client flows → **Yes**
3. Save
4. Clear cache: `rm -rf ~/.powerbi-mcp/token_cache.bin`
5. Retry

See [Azure Setup Guide](azure-setup.md#step-4-enable-public-client-flow) for details.

### Error: "AADSTS50020: User account does not exist in tenant"

**Cause**: Tenant ID mismatch or multi-tenant issue.

**Solution**: Change `.env` to use common tenant:
```bash
AZURE_TENANT_ID=common
AZURE_CLIENT_ID=your-client-id
```

### Error: "Authentication timeout" or "Device code expired"

**Cause**: Didn't complete browser authentication within time limit.

**Solution**:
1. Run app again
2. Complete authentication within 15 minutes
3. If still failing, clear cache and retry

### Error: "Insufficient privileges"

**Cause**: User doesn't have PowerBI access or app lacks permissions.

**Solution**:
1. Verify user has PowerBI Pro/Premium license
2. Check Azure app permissions include PowerBI scopes
3. Grant admin consent in Azure Portal (if possible)

---

## Connection Problems

### Error: "Failed to connect to MCP server: 405 Method Not Allowed"

**Cause**: This was a known issue, should be fixed with HTTPTransport.

**Check**: Verify you have the latest `clients/http_transport.py`

**Solution**: The code should use HTTP POST with SSE parsing. If seeing this error, report it as a bug.

### Error: "Connection timeout"

**Cause**: Network issue or server unavailable.

**Check**:
```bash
# Test if endpoint is reachable
curl -I https://api.fabric.microsoft.com/v1/mcp/powerbi
```

**Solution**:
- Check internet connection
- Verify PowerBI MCP service is available
- Try again later

### Error: "SSL Certificate verification failed"

**Cause**: Corporate proxy or certificate issue.

**Solution**:
1. Check if behind corporate proxy
2. Configure proxy settings if needed
3. Contact IT if persistent

---

## Tool Execution Failures

### Error: "Tool requires parameter: X"

**Cause**: Tool needs specific input that wasn't provided.

**Solution**:
1. Run `python test_powerbi_tools.py` to see required parameters
2. Get the needed information first (workspace ID, dataset ID, etc.)
3. Provide complete parameters to Claude

### Error: "Resource not found (404)"

**Cause**: Workspace/dataset ID doesn't exist or you don't have access.

**Solution**:
1. Verify IDs are correct
2. Check you have access to the resource in PowerBI portal
3. List available resources first before trying to access specific ones

### Error: "Unauthorized (401/403)"

**Cause**: Token expired or insufficient permissions.

**Solution**:
1. Clear token cache: `rm -rf ~/.powerbi-mcp/token_cache.bin`
2. Re-authenticate
3. Check Azure app permissions
4. Verify PowerBI license is active

### No Error But No Data Returned

**Cause**: Various - empty dataset, wrong parameters, silent failure.

**Troubleshoot**:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG  # Linux/Mac
set LOG_LEVEL=DEBUG     # Windows

# Run with verbose output
python main.py
```

---

## Debug Mode

### Enable Debug Logging

**Option 1: Environment Variable**
```bash
# Linux/Mac
export LOG_LEVEL=DEBUG

# Windows
set LOG_LEVEL=DEBUG

# Or in .env file
LOG_LEVEL=DEBUG
```

**Option 2: Modify Code Temporarily**

In `main.py`, add at the top:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### What Debug Logging Shows

- Exact HTTP requests to PowerBI MCP server
- Full request/response bodies
- Authentication token details (redacted)
- Tool call parameters and results
- Error stack traces

### Diagnostic Test Script

Always run this first when troubleshooting:

```bash
python test_powerbi_tools.py
```

This shows:
- ✅ Which tools are available
- ✅ What parameters each tool needs
- ✅ Test execution of each tool
- ✅ Actual results or errors
- ✅ Helpful next steps

### Capture Full Session Log

```bash
# Redirect all output to file
python main.py 2>&1 | tee session.log

# Then review session.log for issues
```

---

## Common Scenarios

### "Claude says it can help but doesn't call any tools"

**Issue**: Claude responds conversationally but doesn't use PowerBI tools.

**Possible Causes**:
1. Question wasn't specific enough
2. Tools aren't being passed to Claude properly
3. System prompt isn't clear about tool use

**Solution**:
- Be very specific: "Use the GetSemanticModelSchema tool to get the schema for dataset X"
- Check orchestrator is passing tools correctly
- Verify tools are in Claude format (not MCP format)

### "Tool executes but result isn't displayed"

**Issue**: Tool call succeeds but output isn't shown to user.

**Check**:
1. Run `test_powerbi_tools.py` - does it show results?
2. Check `orchestrator.py` - is it passing results back to Claude?
3. Verify Claude is processing tool results

**Debug**:
```python
# In orchestrator.py, add logging
console.print(f"[debug] Tool result: {result}")
```

### "Works in test script but not in main app"

**Issue**: `test_powerbi_tools.py` works but `main.py` doesn't.

**Cause**: Likely orchestrator or Claude integration issue.

**Check**:
1. Verify orchestrator is calling MCP client correctly
2. Check tool format conversion (MCP → Claude)
3. Ensure tool results are formatted properly for Claude

---

## Getting Help

If you're still stuck:

### 1. Gather Information

Run these commands and save output:

```bash
# Configuration check
python test_config.py > config_check.txt

# Tool diagnostic
python test_powerbi_tools.py > tools_test.txt

# Main app with debug
LOG_LEVEL=DEBUG python main.py 2>&1 > debug_session.txt
```

### 2. Check These

- [ ] PowerBI Pro/Premium license active?
- [ ] Can access workspaces in PowerBI portal?
- [ ] Azure app has "Allow public client flows" = Yes?
- [ ] Azure app has PowerBI API permissions?
- [ ] Authentication completes successfully?
- [ ] MCP connection established?
- [ ] Tools discovered (should see 3)?

### 3. Review Logs

Look for:
- Error messages (search for "Error", "Failed", "Exception")
- Tool execution logs ("Executing tool:", "Tool result:")
- Authentication issues ("401", "403", "AADSTS")

### 4. Common Fixes

Try these in order:
```bash
# 1. Clear cache and re-authenticate
rm -rf ~/.powerbi-mcp/token_cache.bin

# 2. Verify configuration
python test_config.py

# 3. Test tools directly
python test_powerbi_tools.py

# 4. Check Azure app settings
# - Public client flows enabled
# - PowerBI permissions granted
# - Admin consent given (if possible)

# 5. Run main app with debug logging
LOG_LEVEL=DEBUG python main.py
```

---

## Quick Reference

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| No schema returned | Tool needs parameters | Ask for workspace/dataset list first |
| "client_secret required" | Public flows disabled | Enable in Azure Portal → Authentication |
| "Unauthorized" | Permissions missing | Add PowerBI scopes in Azure Portal |
| "No workspaces" | No PowerBI access | Get PowerBI license, create workspace |
| Tool executes but no data | Empty resource | Verify resource has data in PowerBI portal |
| Authentication loops | Token cache corrupt | Delete `~/.powerbi-mcp/token_cache.bin` |
| Connection fails | Network/proxy | Check internet, corporate proxy settings |

---

## Still Need Help?

1. Review the main [README.md](../README.md)
2. Check [Azure Setup Guide](azure-setup.md)
3. Run all diagnostic tests and save output
4. Check Azure Portal sign-in logs for auth issues
5. Verify PowerBI portal access independently

