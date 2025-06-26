/**
 * API Versioning System for SignalOS
 * Addresses missing API versioning (Issue #30)
 */

import { Express, Request, Response, NextFunction } from 'express';

export interface VersionedRequest extends Request {
  apiVersion: string;
  isLatestVersion: boolean;
  deprecationWarning?: string;
}

export interface ApiVersionConfig {
  version: string;
  supported: boolean;
  deprecated: boolean;
  deprecationDate?: Date;
  endOfLifeDate?: Date;
  migrationGuide?: string;
}

export class ApiVersionManager {
  private versions: Map<string, ApiVersionConfig> = new Map();
  private currentVersion: string = 'v1';
  private defaultVersion: string = 'v1';

  constructor() {
    // Define supported API versions
    this.addVersion('v1', {
      version: 'v1',
      supported: true,
      deprecated: false
    });

    // Future versions can be added here
    // this.addVersion('v2', {
    //   version: 'v2',
    //   supported: true,
    //   deprecated: false
    // });
  }

  /**
   * Add a new API version
   */
  addVersion(version: string, config: ApiVersionConfig): void {
    this.versions.set(version, config);
  }

  /**
   * Deprecate an API version
   */
  deprecateVersion(version: string, deprecationDate: Date, endOfLifeDate?: Date, migrationGuide?: string): void {
    const config = this.versions.get(version);
    if (config) {
      config.deprecated = true;
      config.deprecationDate = deprecationDate;
      config.endOfLifeDate = endOfLifeDate;
      config.migrationGuide = migrationGuide;
      this.versions.set(version, config);
    }
  }

  /**
   * Get version from request headers or URL
   */
  extractVersion(req: Request): string {
    // Check Accept header first (preferred method)
    const acceptHeader = req.headers.accept;
    if (acceptHeader) {
      const versionMatch = acceptHeader.match(/application\/vnd\.signalos\.(v\d+)\+json/);
      if (versionMatch) {
        return versionMatch[1];
      }
    }

    // Check custom header
    const versionHeader = req.headers['api-version'] as string;
    if (versionHeader) {
      return versionHeader;
    }

    // Check URL path
    const pathVersion = req.path.match(/^\/api\/(v\d+)\//);
    if (pathVersion) {
      return pathVersion[1];
    }

    // Return default version
    return this.defaultVersion;
  }

  /**
   * Validate if version is supported
   */
  isVersionSupported(version: string): boolean {
    const config = this.versions.get(version);
    return config ? config.supported : false;
  }

  /**
   * Check if version is deprecated
   */
  isVersionDeprecated(version: string): boolean {
    const config = this.versions.get(version);
    return config ? config.deprecated : false;
  }

  /**
   * Get deprecation warning message
   */
  getDeprecationWarning(version: string): string | undefined {
    const config = this.versions.get(version);
    if (config && config.deprecated) {
      let warning = `API version ${version} is deprecated`;
      
      if (config.endOfLifeDate) {
        warning += ` and will be removed on ${config.endOfLifeDate.toISOString().split('T')[0]}`;
      }
      
      if (config.migrationGuide) {
        warning += `. Migration guide: ${config.migrationGuide}`;
      }
      
      return warning;
    }
    return undefined;
  }

  /**
   * Express middleware for API versioning
   */
  middleware() {
    return (req: Request, res: Response, next: NextFunction) => {
      const versionedReq = req as VersionedRequest;
      const version = this.extractVersion(req);

      // Check if version is supported
      if (!this.isVersionSupported(version)) {
        return res.status(400).json({
          error: 'Unsupported API version',
          message: `API version '${version}' is not supported`,
          supportedVersions: Array.from(this.versions.keys()).filter(v => 
            this.versions.get(v)?.supported
          ),
          currentVersion: this.currentVersion
        });
      }

      // Set version information on request
      versionedReq.apiVersion = version;
      versionedReq.isLatestVersion = version === this.currentVersion;

      // Add deprecation warning if applicable
      if (this.isVersionDeprecated(version)) {
        const warning = this.getDeprecationWarning(version);
        if (warning) {
          versionedReq.deprecationWarning = warning;
          res.setHeader('X-API-Deprecation-Warning', warning);
        }
      }

      // Set version headers
      res.setHeader('X-API-Version', version);
      res.setHeader('X-API-Current-Version', this.currentVersion);

      next();
    };
  }

  /**
   * Create versioned route handler
   */
  createVersionedHandler(handlers: Record<string, Function>) {
    return (req: VersionedRequest, res: Response, next: NextFunction) => {
      const version = req.apiVersion || this.defaultVersion;
      const handler = handlers[version] || handlers[this.defaultVersion];

      if (!handler) {
        return res.status(501).json({
          error: 'Version not implemented',
          message: `Handler for API version '${version}' is not implemented`,
          availableVersions: Object.keys(handlers)
        });
      }

      // Call the appropriate version handler
      handler(req, res, next);
    };
  }

  /**
   * Get API version information
   */
  getVersionInfo() {
    return {
      currentVersion: this.currentVersion,
      defaultVersion: this.defaultVersion,
      supportedVersions: Array.from(this.versions.entries()).map(([version, config]) => ({
        version,
        supported: config.supported,
        deprecated: config.deprecated,
        deprecationDate: config.deprecationDate,
        endOfLifeDate: config.endOfLifeDate
      }))
    };
  }
}

// Global instance
export const apiVersionManager = new ApiVersionManager();

/**
 * Utility function to create versioned API routes
 */
export function versionedRoute(app: Express, path: string, handlers: Record<string, Function>) {
  // Create versioned URLs (e.g., /api/v1/signals, /api/v2/signals)
  Object.keys(handlers).forEach(version => {
    const versionedPath = `/api/${version}${path}`;
    app.use(versionedPath, (req: Request, res: Response, next: NextFunction) => {
      (req as VersionedRequest).apiVersion = version;
      handlers[version](req, res, next);
    });
  });

  // Default route without version prefix
  app.use(`/api${path}`, apiVersionManager.createVersionedHandler(handlers));
}

/**
 * Helper to check if feature is available in version
 */
export function isFeatureAvailable(version: string, feature: string): boolean {
  const featureMatrix: Record<string, string[]> = {
    'v1': [
      'basic-signals',
      'basic-trades',
      'basic-channels',
      'websockets',
      'authentication'
    ],
    'v2': [
      'basic-signals',
      'basic-trades', 
      'basic-channels',
      'websockets',
      'authentication',
      'advanced-analytics',
      'bulk-operations',
      'real-time-notifications'
    ]
  };

  const availableFeatures = featureMatrix[version] || [];
  return availableFeatures.includes(feature);
}

/**
 * Response wrapper that includes version metadata
 */
export function versionedResponse(req: VersionedRequest, data: any, meta: any = {}) {
  const response: any = {
    data,
    meta: {
      apiVersion: req.apiVersion,
      isLatestVersion: req.isLatestVersion,
      ...meta
    }
  };

  if (req.deprecationWarning) {
    response.warnings = [req.deprecationWarning];
  }

  return response;
}