#!/usr/bin/env node

/**
 * FSG Walmart MCP Server — Local / Claude Desktop version
 * Uses stdio transport (no HTTP server needed)
 * Run via Claude Desktop claude_desktop_config.json
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";

// ─── Brand Credentials ────────────────────────────────────────────────────────
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
const tokenCache = {};

async function getToken(brand) {
  const creds = BRANDS[brand];
  if (!creds?.clientId) throw new Error(`No credentials for brand: ${brand}`);

  if (tokenCache[brand]?.expiresAt > Date.now()) return tokenCache[brand].token;

  const auth = Buffer.from(`${creds.clientId}:${creds.clientSecret}`).toString("base64");
  const res = await fetch(`${BASE_URL}/v3/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
      Authorization: `Basic ${auth}`,
      "WM_SVC.NAME": "FSG-Local-MCP",
      "WM_QOS.CORRELATION_ID": `fsg-${Date.now()}`,
    },
    body: "grant_type=client_credentials",
  });

  if (!res.ok) throw new Error(`Auth failed for ${brand}: ${await res.text()}`);
  const data = await res.json();
  tokenCache[brand] = { token: data.access_token, expiresAt: Date.now() + (data.expires_in - 60) * 1000 };
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
      "WM_SVC.NAME": "FSG-Local-MCP",
      "WM_QOS.CORRELATION_ID": `fsg-${Date.now()}`,
      "WM_SEC.ACCESS_TOKEN": token,
    },
  });

  if (!res.ok) throw new Error(`Walmart API error (${res.status}): ${await res.text()}`);
  return res.json();
}

// ─── Order summarizer ─────────────────────────────────────────────────────────
function summarizeOrders(orders, statusFilter = ["Delivered"]) {
  const filtered = orders.filter((o) =>
    o.orderLines?.orderLine?.some((l) =>
      statusFilter.includes(l.orderLineStatuses?.orderLineStatus?.[0]?.status)
    )
  );

  let totalRevenue = 0, totalUnits = 0;
  const byDay = {}, bySku = {};

  for (const order of filtered) {
    const shipDate = order.shippingInfo?.estimatedShipDate
      ? new Date(Number(order.shippingInfo.estimatedShipDate)).toISOString().split("T")[0]
      : order.orderDate
      ? new Date(Number(order.orderDate)).toISOString().split("T")[0]
      : "unknown";

    for (const line of order.orderLines?.orderLine || []) {
      const status = line.orderLineStatuses?.orderLineStatus?.[0]?.status;
      if (!statusFilter.includes(status)) continue;

      const lineDate = line.fulfillment?.estimatedShipDate
        ? new Date(Number(line.fulfillment.estimatedShipDate)).toISOString().split("T")[0]
        : shipDate;

      const qty = Number(line.orderLineQuantity?.amount || 0);
      const price = Number(line.charges?.charge?.[0]?.chargeAmount?.amount || 0);
      const sku = line.item?.sku || "unknown";
      const name = line.item?.productName || sku;

      totalRevenue += price;
      totalUnits += qty;

      byDay[lineDate] = byDay[lineDate] || { revenue: 0, units: 0, orders: new Set() };
      byDay[lineDate].revenue += price;
      byDay[lineDate].units += qty;
      byDay[lineDate].orders.add(order.purchaseOrderId);

      bySku[sku] = bySku[sku] || { name, units: 0, revenue: 0 };
      bySku[sku].units += qty;
      bySku[sku].revenue += price;
    }
  }

  return { totalRevenue, totalUnits, byDay, bySku };
}

// ─── Paginate orders ──────────────────────────────────────────────────────────
async function getAllOrders(brand, dateFrom, dateTo) {
  const allOrders = [];
  let nextCursor = null;

  do {
    const params = {
      createdStartDate: `${dateFrom}T00:00:00Z`,
      createdEndDate: `${dateTo}T23:59:59Z`,
      limit: 200,
    };
    if (nextCursor) params.nextCursor = nextCursor;

    const data = await walmartFetch(brand, "/v3/orders", params);
    const orders = data.list?.elements?.order || [];
    allOrders.push(...orders);
    nextCursor = data.list?.meta?.nextCursor || null;
  } while (nextCursor);

  return allOrders;
}

// ─── MCP Server ───────────────────────────────────────────────────────────────
const server = new Server(
  { name: "fsg-walmart-mcp-local", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "walmart_list_brands",
      description: "List all configured Walmart brands.",
      inputSchema: { type: "object", properties: {}, required: [] },
    },
    {
      name: "walmart_get_sales_summary",
      description:
        "Get total GMV, units sold, daily breakdown and SKU breakdown for a Walmart brand. Uses estimated ship date for daily attribution (matches Seller Center). Paginates automatically.",
      inputSchema: {
        type: "object",
        properties: {
          brand: { type: "string", enum: Object.keys(BRANDS) },
          date_from: { type: "string", description: "YYYY-MM-DD" },
          date_to: { type: "string", description: "YYYY-MM-DD" },
          status: { type: "string", default: "Delivered" },
        },
        required: ["brand", "date_from", "date_to"],
      },
    },
    {
      name: "walmart_get_orders",
      description: "Get raw order list for a brand and date range.",
      inputSchema: {
        type: "object",
        properties: {
          brand: { type: "string", enum: Object.keys(BRANDS) },
          date_from: { type: "string" },
          date_to: { type: "string" },
        },
        required: ["brand", "date_from", "date_to"],
      },
    },
    {
      name: "walmart_get_items",
      description: "Get catalog items for a brand.",
      inputSchema: {
        type: "object",
        properties: {
          brand: { type: "string", enum: Object.keys(BRANDS) },
          limit: { type: "number", default: 50 },
        },
        required: ["brand"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    if (name === "walmart_list_brands") {
      return {
        content: [{
          type: "text",
          text: JSON.stringify(
            Object.entries(BRANDS).map(([k, v]) => ({ brand: k, configured: !!(v.clientId && v.clientSecret) })),
            null, 2
          ),
        }],
      };
    }

    if (name === "walmart_get_items") {
      const data = await walmartFetch(args.brand, "/v3/items", { limit: args.limit || 50 });
      const items = (data.ItemResponse || []).map((i) => ({
        sku: i.sku, wpid: i.wpid, productName: i.productName,
        price: i.price?.amount, availability: i.availability, publishedStatus: i.publishedStatus,
      }));
      return { content: [{ type: "text", text: JSON.stringify(items, null, 2) }] };
    }

    if (name === "walmart_get_orders") {
      const orders = await getAllOrders(args.brand, args.date_from, args.date_to);
      const result = orders.map((o) => ({
        orderId: o.purchaseOrderId,
        orderDate: o.orderDate ? new Date(Number(o.orderDate)).toISOString().split("T")[0] : null,
        lines: (o.orderLines?.orderLine || []).map((l) => ({
          sku: l.item?.sku,
          productName: l.item?.productName,
          quantity: l.orderLineQuantity?.amount,
          price: l.charges?.charge?.[0]?.chargeAmount?.amount,
          status: l.orderLineStatuses?.orderLineStatus?.[0]?.status,
        })),
      }));
      return { content: [{ type: "text", text: JSON.stringify({ total: result.length, orders: result }, null, 2) }] };
    }

    if (name === "walmart_get_sales_summary") {
      const orders = await getAllOrders(args.brand, args.date_from, args.date_to);
      const statusFilter = args.status ? [args.status] : ["Delivered"];
      const summary = summarizeOrders(orders, statusFilter);

      const dailySales = Object.entries(summary.byDay)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([date, v]) => ({
          date,
          revenue: Math.round(v.revenue * 100) / 100,
          units: v.units,
          orders: v.orders instanceof Set ? v.orders.size : v.orders,
        }));

      const skuSales = Object.entries(summary.bySku)
        .sort(([, a], [, b]) => b.revenue - a.revenue)
        .map(([sku, v]) => ({ sku, productName: v.name, units: v.units, revenue: Math.round(v.revenue * 100) / 100 }));

      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            brand: args.brand,
            period: `${args.date_from} to ${args.date_to}`,
            statusFilter,
            summary: {
              totalRevenue: Math.round(summary.totalRevenue * 100) / 100,
              totalUnits: summary.totalUnits,
            },
            dailySales,
            skuBreakdown: skuSales,
          }, null, 2),
        }],
      };
    }

    throw new Error(`Unknown tool: ${name}`);
  } catch (err) {
    return { content: [{ type: "text", text: `Error: ${err.message}` }], isError: true };
  }
});

// ─── Start stdio transport ────────────────────────────────────────────────────
const transport = new StdioServerTransport();
await server.connect(transport);
