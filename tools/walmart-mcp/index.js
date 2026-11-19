#!/usr/bin/env node

/**
 * FSG Walmart Marketplace MCP Server
 * Provides Claude with direct access to Walmart Marketplace API
 * Covers: orders, sales, items, inventory
 * Future: Walmart Ads API (pending FSG partner approval)
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";
import http from "http";

// ─── Brand Credentials Config ─────────────────────────────────────────────────
// Add each brand's Walmart Marketplace API credentials here
const BRANDS = {
  opopop: {
    clientId: process.env.WALMART_OPOPOP_CLIENT_ID || "",
    clientSecret: process.env.WALMART_OPOPOP_CLIENT_SECRET || "",
  },
  reshoevn8r: {
    clientId: process.env.WALMART_RESHOEVN8R_CLIENT_ID || "",
    clientSecret: process.env.WALMART_RESHOEVN8R_CLIENT_SECRET || "",
  },
  caddyo: {
    clientId: process.env.WALMART_CADDYO_CLIENT_ID || "",
    clientSecret: process.env.WALMART_CADDYO_CLIENT_SECRET || "",
  },
};

const BASE_URL = "https://marketplace.walmartapis.com";

// ─── Token Cache ───────────────────────────────────────────────────────────────
const tokenCache = {};

async function getToken(brand) {
  const creds = BRANDS[brand];
  if (!creds || !creds.clientId) {
    throw new Error(`No credentials found for brand: ${brand}`);
  }

  // Return cached token if still valid (tokens expire in 15 min)
  if (tokenCache[brand] && tokenCache[brand].expiresAt > Date.now()) {
    return tokenCache[brand].token;
  }

  const auth = Buffer.from(`${creds.clientId}:${creds.clientSecret}`).toString("base64");
  const res = await fetch(`${BASE_URL}/v3/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
      Authorization: `Basic ${auth}`,
      "WM_SVC.NAME": "FSG Walmart MCP",
      "WM_QOS.CORRELATION_ID": `fsg-${Date.now()}`,
    },
    body: "grant_type=client_credentials",
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Auth failed for ${brand}: ${err}`);
  }

  const data = await res.json();
  tokenCache[brand] = {
    token: data.access_token,
    expiresAt: Date.now() + (data.expires_in - 60) * 1000, // buffer 60s
  };

  return data.access_token;
}

async function walmartFetch(brand, path, params = {}) {
  const token = await getToken(brand);
  const url = new URL(`${BASE_URL}${path}`);
  Object.entries(params).forEach(([k, v]) => v && url.searchParams.set(k, v));

  const res = await fetch(url.toString(), {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
      "WM_SVC.NAME": "FSG Walmart MCP",
      "WM_QOS.CORRELATION_ID": `fsg-${Date.now()}`,
      "WM_SEC.ACCESS_TOKEN": token,
    },
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Walmart API error (${res.status}): ${err}`);
  }

  return res.json();
}

// ─── Helper: Summarize Orders ─────────────────────────────────────────────────
// Uses shipping_estimated_ship_date for daily attribution — matches Seller Center exactly
function summarizeOrders(orders, statusFilter = ["Delivered"]) {
  const lines = orders.filter((o) =>
    o.orderLines?.orderLine?.some((l) =>
      statusFilter.includes(l.orderLineStatuses?.orderLineStatus?.[0]?.status)
    )
  );

  let totalRevenue = 0;
  let totalUnits = 0;
  const byDay = {};
  const bySku = {};

  for (const order of lines) {
    // Use estimated ship date for daily breakdown — matches Walmart Seller Center
    const shipDate = order.shippingInfo?.estimatedShipDate
      ? new Date(Number(order.shippingInfo.estimatedShipDate)).toISOString().split("T")[0]
      : order.orderDate
      ? new Date(Number(order.orderDate)).toISOString().split("T")[0]
      : "unknown";

    for (const line of order.orderLines?.orderLine || []) {
      const status = line.orderLineStatuses?.orderLineStatus?.[0]?.status;
      if (!statusFilter.includes(status)) continue;

      // Per-line ship date (more accurate for multi-line orders)
      const lineShipDate = line.fulfillment?.estimatedShipDate
        ? new Date(Number(line.fulfillment.estimatedShipDate)).toISOString().split("T")[0]
        : shipDate;

      const qty = Number(line.orderLineQuantity?.amount || 0);
      const price = Number(line.charges?.charge?.[0]?.chargeAmount?.amount || 0);
      const sku = line.item?.sku || "unknown";
      const name = line.item?.productName || sku;

      totalRevenue += price;
      totalUnits += qty;

      byDay[lineShipDate] = byDay[lineShipDate] || { revenue: 0, units: 0, orders: new Set() };
      byDay[lineShipDate].revenue += price;
      byDay[lineShipDate].units += qty;
      byDay[lineShipDate].orders.add(order.purchaseOrderId);

      bySku[sku] = bySku[sku] || { name, units: 0, revenue: 0 };
      bySku[sku].units += qty;
      bySku[sku].revenue += price;
    }
  }

  return { totalRevenue, totalUnits, byDay, bySku };
}

// ─── MCP Server ───────────────────────────────────────────────────────────────
const server = new Server(
  { name: "fsg-walmart-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// ─── Tool Definitions ─────────────────────────────────────────────────────────
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "walmart_get_sales_summary",
      description:
        "Get total sales, units sold, and daily/SKU breakdown for a Walmart brand over a date range. Returns Delivered orders only by default.",
      inputSchema: {
        type: "object",
        properties: {
          brand: {
            type: "string",
            enum: Object.keys(BRANDS),
            description: "Brand name (e.g. opopop, reshoevn8r, caddyo)",
          },
          date_from: {
            type: "string",
            description: "Start date in YYYY-MM-DD format",
          },
          date_to: {
            type: "string",
            description: "End date in YYYY-MM-DD format",
          },
          status: {
            type: "string",
            description: "Order status filter (default: Delivered)",
            default: "Delivered",
          },
        },
        required: ["brand", "date_from", "date_to"],
      },
    },
    {
      name: "walmart_get_orders",
      description:
        "Get raw order details for a Walmart brand over a date range including SKU, product name, quantity, price, status.",
      inputSchema: {
        type: "object",
        properties: {
          brand: {
            type: "string",
            enum: Object.keys(BRANDS),
            description: "Brand name",
          },
          date_from: {
            type: "string",
            description: "Start date in YYYY-MM-DD format",
          },
          date_to: {
            type: "string",
            description: "End date in YYYY-MM-DD format",
          },
          limit: {
            type: "number",
            description: "Max number of orders to return (default 200)",
            default: 200,
          },
        },
        required: ["brand", "date_from", "date_to"],
      },
    },
    {
      name: "walmart_get_items",
      description:
        "Get catalog items for a Walmart brand including SKU, product name, price, availability, and published status.",
      inputSchema: {
        type: "object",
        properties: {
          brand: {
            type: "string",
            enum: Object.keys(BRANDS),
            description: "Brand name",
          },
          limit: {
            type: "number",
            description: "Max number of items to return (default 50)",
            default: 50,
          },
        },
        required: ["brand"],
      },
    },
    {
      name: "walmart_list_brands",
      description: "List all configured Walmart brands available in this MCP.",
      inputSchema: {
        type: "object",
        properties: {},
        required: [],
      },
    },
  ],
}));

// ─── Tool Handlers ────────────────────────────────────────────────────────────
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    // ── walmart_list_brands ──────────────────────────────────────────────────
    if (name === "walmart_list_brands") {
      const brands = Object.entries(BRANDS).map(([key, creds]) => ({
        brand: key,
        configured: !!(creds.clientId && creds.clientSecret),
      }));
      return {
        content: [{ type: "text", text: JSON.stringify(brands, null, 2) }],
      };
    }

    // ── walmart_get_items ────────────────────────────────────────────────────
    if (name === "walmart_get_items") {
      const data = await walmartFetch(args.brand, "/v3/items", {
        limit: args.limit || 50,
      });

      const items = (data.ItemResponse || []).map((item) => ({
        sku: item.sku,
        wpid: item.wpid,
        productName: item.productName,
        price: item.price?.amount,
        currency: item.price?.currency,
        availability: item.availability,
        publishedStatus: item.publishedStatus,
        lifecycleStatus: item.lifecycleStatus,
      }));

      return {
        content: [{ type: "text", text: JSON.stringify(items, null, 2) }],
      };
    }

    // ── walmart_get_orders ───────────────────────────────────────────────────
    if (name === "walmart_get_orders") {
      const data = await walmartFetch(args.brand, "/v3/orders", {
        createdStartDate: `${args.date_from}T00:00:00Z`,
        createdEndDate: `${args.date_to}T23:59:59Z`,
        limit: args.limit || 200,
      });

      const orders = data.list?.elements?.order || [];
      const result = orders.map((o) => ({
        orderId: o.purchaseOrderId,
        orderDate: o.orderDate
          ? new Date(Number(o.orderDate)).toISOString().split("T")[0]
          : null,
        lines: (o.orderLines?.orderLine || []).map((l) => ({
          sku: l.item?.sku,
          productName: l.item?.productName,
          quantity: l.orderLineQuantity?.amount,
          price: l.charges?.charge?.[0]?.chargeAmount?.amount,
          currency: l.charges?.charge?.[0]?.chargeAmount?.currency,
          status: l.orderLineStatuses?.orderLineStatus?.[0]?.status,
          fulfillmentType: l.fulfillment?.fulfillmentOption,
        })),
      }));

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              { total: result.length, orders: result },
              null,
              2
            ),
          },
        ],
      };
    }

    // ── walmart_get_sales_summary ────────────────────────────────────────────
    if (name === "walmart_get_sales_summary") {
      const data = await walmartFetch(args.brand, "/v3/orders", {
        createdStartDate: `${args.date_from}T00:00:00Z`,
        createdEndDate: `${args.date_to}T23:59:59Z`,
        limit: 200,
      });

      const orders = data.list?.elements?.order || [];
      const statusFilter = args.status ? [args.status] : ["Delivered"];
      const summary = summarizeOrders(orders, statusFilter);

      // Format daily breakdown (grouped by shipping_estimated_ship_date — matches Seller Center)
      const dailySales = Object.entries(summary.byDay)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([date, v]) => ({
          date,
          revenue: Math.round(v.revenue * 100) / 100,
          units: v.units,
          orders: v.orders instanceof Set ? v.orders.size : v.orders,
        }));

      // Format SKU breakdown
      const skuSales = Object.entries(summary.bySku)
        .sort(([, a], [, b]) => b.revenue - a.revenue)
        .map(([sku, v]) => ({
          sku,
          productName: v.name,
          units: v.units,
          revenue: Math.round(v.revenue * 100) / 100,
        }));

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              {
                brand: args.brand,
                period: `${args.date_from} to ${args.date_to}`,
                statusFilter,
                summary: {
                  totalRevenue: Math.round(summary.totalRevenue * 100) / 100,
                  totalUnits: summary.totalUnits,
                },
                dailySales,
                skuBreakdown: skuSales,
              },
              null,
              2
            ),
          },
        ],
      };
    }

    throw new Error(`Unknown tool: ${name}`);
  } catch (err) {
    return {
      content: [{ type: "text", text: `Error: ${err.message}` }],
      isError: true,
    };
  }
});

// ─── Start Streamable HTTP Server ────────────────────────────────────────────
const PORT = process.env.PORT || 3000;

const httpServer = http.createServer(async (req, res) => {
  // CORS headers
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, mcp-session-id");
  res.setHeader("Access-Control-Expose-Headers", "mcp-session-id");

  if (req.method === "OPTIONS") {
    res.writeHead(200);
    res.end();
    return;
  }

  // Health check
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", service: "fsg-walmart-mcp" }));
    return;
  }

  // OAuth metadata — tells Claude.ai no auth is required
  if (req.url === "/.well-known/oauth-authorization-server" || req.url === "/.well-known/openid-configuration") {
    res.writeHead(404);
    res.end("Not found");
    return;
  }

  // MCP endpoint
  if (req.url === "/mcp") {
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined, // stateless
    });
    await server.connect(transport);
    await transport.handleRequest(req, res);
    return;
  }

  res.writeHead(404);
  res.end("Not found");
});

httpServer.listen(PORT, () => {
  console.log(`FSG Walmart MCP server running on port ${PORT}`);
  console.log(`MCP endpoint: http://localhost:${PORT}/mcp`);
});

// ─── Keep-alive ping (prevents Railway free tier from sleeping) ───────────────
setInterval(() => {
  const req = http.request({ hostname: "localhost", port: PORT, path: "/health", method: "GET" }, (res) => {
    res.resume();
  });
  req.on("error", () => {});
  req.end();
}, 5 * 60 * 1000); // ping every 5 minutes
