# FSG Walmart MCP Server

Custom MCP server for Claude to pull Walmart Marketplace data directly — no Windsor.ai needed.

## Setup

### 1. Install dependencies
```bash
npm install
```

### 2. Configure credentials
```bash
cp .env.example .env
# Fill in each brand's Client ID and Secret
```

### 3. Add to Claude Desktop config
Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fsg-walmart": {
      "command": "node",
      "args": ["/path/to/fsg-walmart-mcp/index.js"],
      "env": {
        "WALMART_OPOPOP_CLIENT_ID": "bf148d89-df6a-428a-89dc-9608ed893727",
        "WALMART_OPOPOP_CLIENT_SECRET": "your_secret_here",
        "WALMART_RESHOEVN8R_CLIENT_ID": "your_client_id_here",
        "WALMART_RESHOEVN8R_CLIENT_SECRET": "your_secret_here",
        "WALMART_CADDYO_CLIENT_ID": "your_client_id_here",
        "WALMART_CADDYO_CLIENT_SECRET": "your_secret_here"
      }
    }
  }
}
```

### 4. Restart Claude Desktop

## Available Tools

| Tool | Description |
|------|-------------|
| `walmart_list_brands` | List all configured brands |
| `walmart_get_sales_summary` | Total sales, units, daily + SKU breakdown |
| `walmart_get_orders` | Raw order details |
| `walmart_get_items` | Catalog items, prices, availability |

## Example Usage in Claude

```
Get Opopop Walmart sales summary for Nov 8-14 2026
→ calls walmart_get_sales_summary(brand="opopop", date_from="2026-11-08", date_to="2026-11-14")
```

## Adding New Brands

1. Get API keys from: developer.walmart.com → API Keys
2. Add to BRANDS config in index.js
3. Add env vars to claude_desktop_config.json

## Roadmap
- [ ] Walmart Ads API endpoints (pending FSG partner approval)
- [ ] Inventory/WFS data
- [ ] Multi-page order pagination for large date ranges
