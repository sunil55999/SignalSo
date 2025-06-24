import { Pool, neonConfig } from '@neondatabase/serverless';
import { drizzle } from 'drizzle-orm/neon-serverless';
import ws from "ws";
import * as schema from "@shared/schema";

neonConfig.webSocketConstructor = ws;

// For development, use a fallback database URL if not provided
const DATABASE_URL = process.env.DATABASE_URL || 'postgresql://localhost:5432/signalos_dev';

if (!DATABASE_URL) {
  console.warn(
    "DATABASE_URL not set. Database operations will be limited until database is provisioned.",
  );
}

export const pool = DATABASE_URL ? new Pool({ connectionString: DATABASE_URL }) : null;
export const db = pool ? drizzle({ client: pool, schema }) : null;