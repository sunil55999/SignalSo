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

// Optimized connection pool for better performance
export const pool = new Pool({ 
  connectionString: DATABASE_URL,
  max: 20,                      // Maximum connections
  idleTimeoutMillis: 30000,     // Close idle connections after 30s
  connectionTimeoutMillis: 5000, // Connection timeout 5s
  maxUses: 7500,                // Refresh connections after 7500 uses
  allowExitOnIdle: true         // Allow pool to close when idle
});

export const db = drizzle({ client: pool, schema });