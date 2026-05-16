/**
 * Membra Money Protocol — Devnet Smoke Test
 *
 * Usage:
 *   npx ts-node scripts/devnet_smoke_test.ts
 *
 * This script checks backend health, reserves, and risk disclosure.
 * It exits non-zero on hard errors.
 */

import fetch from "node-fetch";

const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";

interface Check {
  name: string;
  path: string;
  expectStatus: number;
  validate?: (body: any) => string | null;
}

const checks: Check[] = [
  {
    name: "Health",
    path: "/health",
    expectStatus: 200,
    validate: (b) => (b.devnet === true ? null : "expected devnet=true"),
  },
  {
    name: "Ready",
    path: "/ready",
    expectStatus: 200,
  },
  {
    name: "Risk Disclosure",
    path: "/api/v1/risk-disclosure",
    expectStatus: 200,
    validate: (b) => (b.version ? null : "missing version"),
  },
  {
    name: "Reserves",
    path: "/api/v1/reserves",
    expectStatus: 200,
    validate: (b) => (b.devnet_only === true ? null : "expected devnet_only=true"),
  },
  {
    name: "Stats",
    path: "/api/v1/stats",
    expectStatus: 200,
    validate: (b) => (b.devnet === true ? null : "expected devnet=true"),
  },
];

async function runChecks() {
  let failures = 0;
  for (const check of checks) {
    const url = `${API_BASE}${check.path}`;
    try {
      const res = await fetch(url, { timeout: 10000 } as any);
      if (res.status !== check.expectStatus) {
        console.error(`FAIL ${check.name}: status ${res.status}, expected ${check.expectStatus}`);
        failures++;
        continue;
      }
      const body = await res.json();
      if (check.validate) {
        const err = check.validate(body);
        if (err) {
          console.error(`FAIL ${check.name}: ${err}`);
          failures++;
          continue;
        }
      }
      console.log(`PASS ${check.name}`);
    } catch (e: any) {
      console.error(`FAIL ${check.name}: ${e.message}`);
      failures++;
    }
  }

  if (failures > 0) {
    console.error(`\n${failures} check(s) failed.`);
    process.exit(1);
  }
  console.log("\nAll checks passed.");
  process.exit(0);
}

runChecks();
