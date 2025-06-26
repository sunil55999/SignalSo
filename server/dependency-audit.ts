/**
 * Dependency Security Audit System
 * Addresses vulnerable dependencies (Issue #25)
 */

import fs from 'fs/promises';
import path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export interface VulnerabilityReport {
  package: string;
  version: string;
  severity: 'low' | 'moderate' | 'high' | 'critical';
  title: string;
  overview: string;
  recommendation: string;
  references: string[];
  patched_versions?: string;
}

export interface AuditResult {
  timestamp: Date;
  totalDependencies: number;
  vulnerabilities: VulnerabilityReport[];
  summary: {
    critical: number;
    high: number;
    moderate: number;
    low: number;
  };
  recommendations: string[];
}

export class DependencyAuditor {
  private packageJsonPath: string;
  private lockFilePath: string;

  constructor(projectRoot: string = '.') {
    this.packageJsonPath = path.join(projectRoot, 'package.json');
    this.lockFilePath = path.join(projectRoot, 'package-lock.json');
  }

  /**
   * Run comprehensive dependency audit
   */
  async runFullAudit(): Promise<AuditResult> {
    const timestamp = new Date();
    const vulnerabilities: VulnerabilityReport[] = [];
    let totalDependencies = 0;

    try {
      // Check if package.json exists
      await fs.access(this.packageJsonPath);
      
      // Get total dependency count
      totalDependencies = await this.getDependencyCount();

      // Run npm audit
      const npmVulns = await this.runNpmAudit();
      vulnerabilities.push(...npmVulns);

      // Check for known vulnerable packages
      const knownVulns = await this.checkKnownVulnerablePackages();
      vulnerabilities.push(...knownVulns);

      // Check for outdated packages
      const outdatedVulns = await this.checkOutdatedPackages();
      vulnerabilities.push(...outdatedVulns);

    } catch (error) {
      console.error('Audit failed:', error);
    }

    const summary = this.categorizeVulnerabilities(vulnerabilities);
    const recommendations = this.generateRecommendations(vulnerabilities);

    return {
      timestamp,
      totalDependencies,
      vulnerabilities,
      summary,
      recommendations
    };
  }

  /**
   * Get total dependency count
   */
  private async getDependencyCount(): Promise<number> {
    try {
      const packageJson = JSON.parse(await fs.readFile(this.packageJsonPath, 'utf-8'));
      const deps = Object.keys(packageJson.dependencies || {});
      const devDeps = Object.keys(packageJson.devDependencies || {});
      return deps.length + devDeps.length;
    } catch (error) {
      return 0;
    }
  }

  /**
   * Run npm audit and parse results
   */
  private async runNpmAudit(): Promise<VulnerabilityReport[]> {
    try {
      const { stdout } = await execAsync('npm audit --json', {
        cwd: path.dirname(this.packageJsonPath)
      });

      const auditData = JSON.parse(stdout);
      const vulnerabilities: VulnerabilityReport[] = [];

      if (auditData.vulnerabilities) {
        for (const [packageName, vulnData] of Object.entries(auditData.vulnerabilities as any)) {
          const vuln = vulnData as any;
          vulnerabilities.push({
            package: packageName,
            version: vuln.range || 'unknown',
            severity: vuln.severity || 'moderate',
            title: vuln.title || 'Security vulnerability',
            overview: vuln.overview || 'No details available',
            recommendation: vuln.recommendation || 'Update to latest version',
            references: vuln.references || [],
            patched_versions: vuln.patched_versions
          });
        }
      }

      return vulnerabilities;
    } catch (error) {
      // npm audit may exit with non-zero code if vulnerabilities found
      if (error instanceof Error && 'stdout' in error) {
        try {
          const auditData = JSON.parse((error as any).stdout);
          return this.parseNpmAuditOutput(auditData);
        } catch (parseError) {
          console.warn('Failed to parse npm audit output:', parseError);
        }
      }
      return [];
    }
  }

  /**
   * Parse npm audit output
   */
  private parseNpmAuditOutput(auditData: any): VulnerabilityReport[] {
    const vulnerabilities: VulnerabilityReport[] = [];

    if (auditData.vulnerabilities) {
      for (const [packageName, vulnData] of Object.entries(auditData.vulnerabilities)) {
        const vuln = vulnData as any;
        vulnerabilities.push({
          package: packageName,
          version: vuln.range || 'unknown',
          severity: vuln.severity || 'moderate',
          title: vuln.title || 'Security vulnerability',
          overview: vuln.overview || 'No details available',
          recommendation: vuln.recommendation || 'Update to latest version',
          references: vuln.references || [],
          patched_versions: vuln.patched_versions
        });
      }
    }

    return vulnerabilities;
  }

  /**
   * Check for known vulnerable packages
   */
  private async checkKnownVulnerablePackages(): Promise<VulnerabilityReport[]> {
    const vulnerabilities: VulnerabilityReport[] = [];
    
    try {
      const packageJson = JSON.parse(await fs.readFile(this.packageJsonPath, 'utf-8'));
      const allDeps = {
        ...packageJson.dependencies,
        ...packageJson.devDependencies
      };

      // Known vulnerable packages to check
      const knownVulnerablePackages = [
        {
          name: 'lodash',
          vulnerableVersions: ['<4.17.21'],
          severity: 'high' as const,
          issue: 'Prototype pollution vulnerability'
        },
        {
          name: 'express',
          vulnerableVersions: ['<4.18.0'],
          severity: 'moderate' as const,
          issue: 'Open redirect vulnerability'
        },
        {
          name: 'axios',
          vulnerableVersions: ['<0.28.0'],
          severity: 'moderate' as const,
          issue: 'SSRF vulnerability'
        }
      ];

      for (const pkg of knownVulnerablePackages) {
        if (allDeps[pkg.name]) {
          vulnerabilities.push({
            package: pkg.name,
            version: allDeps[pkg.name],
            severity: pkg.severity,
            title: `Known vulnerability in ${pkg.name}`,
            overview: pkg.issue,
            recommendation: `Update ${pkg.name} to latest version`,
            references: []
          });
        }
      }

    } catch (error) {
      console.warn('Failed to check known vulnerable packages:', error);
    }

    return vulnerabilities;
  }

  /**
   * Check for critically outdated packages
   */
  private async checkOutdatedPackages(): Promise<VulnerabilityReport[]> {
    const vulnerabilities: VulnerabilityReport[] = [];

    try {
      const { stdout } = await execAsync('npm outdated --json', {
        cwd: path.dirname(this.packageJsonPath)
      });

      const outdatedData = JSON.parse(stdout);
      
      for (const [packageName, info] of Object.entries(outdatedData)) {
        const pkg = info as any;
        const currentVersion = pkg.current;
        const latestVersion = pkg.latest;
        
        // Check if package is significantly outdated (major version behind)
        if (this.isMajorVersionBehind(currentVersion, latestVersion)) {
          vulnerabilities.push({
            package: packageName,
            version: currentVersion,
            severity: 'moderate',
            title: `Outdated package: ${packageName}`,
            overview: `Package is significantly outdated (${currentVersion} vs ${latestVersion})`,
            recommendation: `Update to latest version: ${latestVersion}`,
            references: []
          });
        }
      }

    } catch (error) {
      // npm outdated exits with code 1 when outdated packages found
      if (error instanceof Error && 'stdout' in error) {
        try {
          const outdatedData = JSON.parse((error as any).stdout);
          return this.parseOutdatedPackages(outdatedData);
        } catch (parseError) {
          // Ignore parsing errors for outdated check
        }
      }
    }

    return vulnerabilities;
  }

  /**
   * Parse outdated packages output
   */
  private parseOutdatedPackages(outdatedData: any): VulnerabilityReport[] {
    const vulnerabilities: VulnerabilityReport[] = [];

    for (const [packageName, info] of Object.entries(outdatedData)) {
      const pkg = info as any;
      const currentVersion = pkg.current;
      const latestVersion = pkg.latest;
      
      if (this.isMajorVersionBehind(currentVersion, latestVersion)) {
        vulnerabilities.push({
          package: packageName,
          version: currentVersion,
          severity: 'moderate',
          title: `Outdated package: ${packageName}`,
          overview: `Package is significantly outdated (${currentVersion} vs ${latestVersion})`,
          recommendation: `Update to latest version: ${latestVersion}`,
          references: []
        });
      }
    }

    return vulnerabilities;
  }

  /**
   * Check if package is major version behind
   */
  private isMajorVersionBehind(current: string, latest: string): boolean {
    try {
      const currentMajor = parseInt(current.split('.')[0]);
      const latestMajor = parseInt(latest.split('.')[0]);
      return latestMajor > currentMajor;
    } catch (error) {
      return false;
    }
  }

  /**
   * Categorize vulnerabilities by severity
   */
  private categorizeVulnerabilities(vulnerabilities: VulnerabilityReport[]) {
    const summary = {
      critical: 0,
      high: 0,
      moderate: 0,
      low: 0
    };

    for (const vuln of vulnerabilities) {
      summary[vuln.severity]++;
    }

    return summary;
  }

  /**
   * Generate recommendations based on vulnerabilities
   */
  private generateRecommendations(vulnerabilities: VulnerabilityReport[]): string[] {
    const recommendations: string[] = [];

    const criticalCount = vulnerabilities.filter(v => v.severity === 'critical').length;
    const highCount = vulnerabilities.filter(v => v.severity === 'high').length;

    if (criticalCount > 0) {
      recommendations.push(`URGENT: Fix ${criticalCount} critical vulnerabilities immediately`);
    }

    if (highCount > 0) {
      recommendations.push(`HIGH PRIORITY: Address ${highCount} high-severity vulnerabilities`);
    }

    recommendations.push('Run "npm audit fix" to automatically fix compatible issues');
    recommendations.push('Review and manually update packages that cannot be automatically fixed');
    recommendations.push('Consider using npm-check-updates for managing package updates');
    recommendations.push('Implement automated dependency scanning in CI/CD pipeline');

    return recommendations;
  }

  /**
   * Generate audit report
   */
  async generateReport(): Promise<string> {
    const audit = await this.runFullAudit();
    
    let report = `# Dependency Security Audit Report\n\n`;
    report += `**Generated:** ${audit.timestamp.toISOString()}\n`;
    report += `**Total Dependencies:** ${audit.totalDependencies}\n\n`;

    report += `## Summary\n\n`;
    report += `- Critical: ${audit.summary.critical}\n`;
    report += `- High: ${audit.summary.high}\n`;
    report += `- Moderate: ${audit.summary.moderate}\n`;
    report += `- Low: ${audit.summary.low}\n\n`;

    if (audit.vulnerabilities.length > 0) {
      report += `## Vulnerabilities\n\n`;
      
      for (const vuln of audit.vulnerabilities) {
        report += `### ${vuln.package} (${vuln.severity.toUpperCase()})\n\n`;
        report += `**Version:** ${vuln.version}\n`;
        report += `**Issue:** ${vuln.title}\n`;
        report += `**Description:** ${vuln.overview}\n`;
        report += `**Recommendation:** ${vuln.recommendation}\n\n`;
      }
    }

    report += `## Recommendations\n\n`;
    for (const rec of audit.recommendations) {
      report += `- ${rec}\n`;
    }

    return report;
  }
}

export const dependencyAuditor = new DependencyAuditor();