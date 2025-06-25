import { Pool, neonConfig } from '@neondatabase/serverless';
import { drizzle } from 'drizzle-orm/neon-serverless';
import ws from "ws";
import * as schema from "@shared/schema";

neonConfig.webSocketConstructor = ws;

// Use provided NeonDB URL or fallback for development
const DATABASE_URL = process.env.DATABASE_URL || 
  "postgresql://neondb_owner:npg_RSnlNDXT1Ir9@ep-curly-feather-a822dc0p-pooler.eastus2.azure.neon.tech/neondb?sslmode=require&channel_binding=require";

if (!DATABASE_URL) {
  throw new Error(
    "DATABASE_URL must be set. Did you forget to provision a database?",
  );
}

export const pool = new Pool({ connectionString: DATABASE_URL });
export const db = drizzle({ client: pool, schema });