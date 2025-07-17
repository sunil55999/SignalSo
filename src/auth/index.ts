import { User, InsertUser } from '@shared/schema';

export interface AuthResult {
  success: boolean;
  user?: User;
  token?: string;
  error?: string;
}

export interface LicenseStatus {
  isValid: boolean;
  expiresAt?: Date;
  features: string[];
  maxChannels: number;
  machineId?: string;
}

export class AuthManager {
  private currentUser: User | null = null;
  private sessionToken: string | null = null;

  async login(username: string, password: string): Promise<AuthResult> {
    try {
      // Simulate authentication
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Mock user data
      const user: User = {
        id: `user_${Date.now()}`,
        username,
        email: `${username}@example.com`,
        passwordHash: 'hashed_password',
        telegramId: null,
        role: 'user',
        createdAt: new Date(),
        updatedAt: new Date()
      };

      this.currentUser = user;
      this.sessionToken = this.generateToken();

      return {
        success: true,
        user,
        token: this.sessionToken
      };
    } catch (error) {
      return {
        success: false,
        error: `Login failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      };
    }
  }

  async logout(): Promise<void> {
    this.currentUser = null;
    this.sessionToken = null;
  }

  async register(userData: InsertUser): Promise<AuthResult> {
    try {
      // Simulate registration
      await new Promise(resolve => setTimeout(resolve, 800));
      
      const user: User = {
        id: `user_${Date.now()}`,
        ...userData,
        createdAt: new Date(),
        updatedAt: new Date()
      };

      return {
        success: true,
        user,
        token: this.generateToken()
      };
    } catch (error) {
      return {
        success: false,
        error: `Registration failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      };
    }
  }

  async validateToken(token: string): Promise<boolean> {
    return token === this.sessionToken;
  }

  async checkLicense(): Promise<LicenseStatus> {
    // Simulate license check
    await new Promise(resolve => setTimeout(resolve, 200));
    
    return {
      isValid: true,
      expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days
      features: ['signal_parsing', 'trade_execution', 'telegram_integration', 'multi_channel'],
      maxChannels: 5,
      machineId: this.generateMachineId()
    };
  }

  getCurrentUser(): User | null {
    return this.currentUser;
  }

  getSessionToken(): string | null {
    return this.sessionToken;
  }

  isAuthenticated(): boolean {
    return this.currentUser !== null && this.sessionToken !== null;
  }

  private generateToken(): string {
    return `jwt_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
  }

  private generateMachineId(): string {
    // Generate a mock machine ID
    return `machine_${Math.random().toString(36).substring(2, 15)}`;
  }
}

// Export default instance
export const authManager = new AuthManager();